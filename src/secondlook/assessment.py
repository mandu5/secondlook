"""Evaluate owner-imported candidates, without contacting a model provider."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import itertools
import math
from pathlib import Path

from .artifacts import artifact_from_sources
from .core import (CapsuleError, apply_edits, atomic_text, fingerprint,
                   public_capsule, write_bundle, write_json, write_rebuild)
from .evaluate import compare_results, evaluate
from .handoff import MAX_RESPONSE_BYTES, load_request, new_output, read_json
from .runner import _diff, _tokens, execution_identity


IMPORTED_COST_BASIS = "External generation cost and usage are owner-reported, unverified; local assessment makes no model calls"
TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def _usage_records(value: list | None, count: int) -> list[dict]:
    if value is None:
        return [{} for _ in range(count)]
    if not isinstance(value, list) or len(value) != count:
        raise CapsuleError("Usage must be a same-order array with one entry per response")
    records = []
    for row in value:
        if row is None:
            row = {}
        if not isinstance(row, dict) or set(row) - {"cost_usd", *TOKEN_FIELDS}:
            raise CapsuleError("Usage accepts only cost_usd and input/output/cache token counts")
        for key, number in row.items():
            if number is None:
                continue
            try:
                valid = type(number) in (int, float) and math.isfinite(number) and number >= 0
            except OverflowError:
                valid = False
            if not valid or (key != "cost_usd" and (type(number) is not int or number > 2**63 - 1)):
                raise CapsuleError("Usage must contain finite nonnegative costs and integer token counts")
        records.append({key: number for key, number in row.items() if number is not None})
    return records


def assess_responses(request_path: Path, responses: list[Path], labels: list[str], output: Path,
                     usage: list | None = None) -> dict:
    if not isinstance(responses, list) or not 1 <= len(responses) <= 4:
        raise CapsuleError("Provide 1–4 candidate responses")
    if (not isinstance(labels, list) or len(labels) != len(responses)
            or any(not isinstance(s, str) or not s.strip() or len(s) > 100 or any(ord(c) < 32 for c in s) for s in labels)):
        raise CapsuleError("Provide one nonempty label (up to 100 characters) per response")
    if len(set(Path(p).resolve() for p in responses)) != len(responses):
        raise CapsuleError("The same response file was supplied more than once")
    metadata = _usage_records(usage, len(responses))
    request, capsule, original = load_request(request_path)
    mode = request["contract"]["mode"]
    payload_key = "files" if mode == "rebuild" else "edits"
    payloads = []
    for path in responses:
        data = read_json(path, MAX_RESPONSE_BYTES, fenced=True)
        if (not isinstance(data, dict) or set(data) != {"request_id", "summary", payload_key}
                or data.get("request_id") != request["request_id"]):
            raise CapsuleError("Response must match this request_id and contain only summary and " + payload_key)
        if not isinstance(data["summary"], str) or len(data["summary"]) > 2000:
            raise CapsuleError("Response summary must be a string of up to 2000 characters")
        if not isinstance(data[payload_key], list) or not 1 <= len(data[payload_key]) <= (32 if mode == "rebuild" else 20):
            raise CapsuleError("Response must include a bounded nonempty list of " + payload_key)
        payloads.append(data)
    output = new_output(output, Path(request_path))
    output.mkdir(parents=True, exist_ok=False)
    manifest = {**execution_identity(), "source": original.identity,
                "checks": request["contract"]["checks"],
                "checks_frozen_at": request["contract"]["checks_frozen_at"],
                "request_id": request["request_id"], "mode": mode,
                "prepared_with": request["contract"]["prepared_with"],
                "import_harness": fingerprint({name: Path(__file__).with_name(name).read_text()
                                               for name in ("assessment.py", "handoff.py")}),
                "model_identity_basis": "Owner-supplied labels; provider identity and generation context unverified",
                "evaluation_reuse": "Identical artifact bytes within this batch reuse browser evidence; not another sample"}
    costs = [m.get("cost_usd") for m in metadata]
    unknown_cost = any(c is None for c in costs)
    known_cost = round(sum(c for c in costs if c is not None), 8)
    result = {"version": 1, "kind": "imported_candidates", "status": "running",
              "created_at": datetime.now(timezone.utc).isoformat(), "capsule": public_capsule(capsule),
              "manifest": manifest, "model_calls": 0, "external_model_calls": None,
              "arms": {}, "comparisons": {}, "output": str(output),
              "cost": {"total_usd": None if unknown_cost else known_cost, "known_spend_usd": known_cost,
                       "limit_usd": None, "unknown": unknown_cost, "basis": IMPORTED_COST_BASIS},
              "limitations": ["External model identities, usage and context isolation are unverified.",
                              "Local evaluation makes zero model calls; external generation is not thereby free.",
                              "One imported result per arm is not an independent repeated-trial model benchmark.",
                              "Checks cover specified behavior; screenshots are not quality scores.",
                              "Checks were frozen locally; the external generation time cannot be verified."]}

    def save():
        result["fingerprint"] = fingerprint(result["manifest"])
        write_json(output / "result.json", result)

    def assess(name, root):
        return evaluate(root, capsule["checks"], output / "evidence" / name, capsule["entrypoint"],
                        readonly_files=capsule.get("readonly_files"))

    write_json(output / "capsule.frozen.json", public_capsule(capsule))
    save()
    try:
        baseline_root = output / "arms" / "A"
        write_bundle(baseline_root, original.sources)
        baseline = assess("A", baseline_root)
        result["arms"]["A"] = {"label": "Saved artifact", "status": baseline["status"], "evaluation": baseline,
                                "cost_usd": 0, "models": ["unknown"], "tokens": _tokens([]), "receipts": []}
        measured = {original.identity: "A"} if baseline["status"] == "completed" else {}
        save()
        readonly = capsule.get("readonly_files", [])
        writable = [name for name in capsule["files"] if name not in readonly]
        for index, (payload, label, meta) in enumerate(zip(payloads, labels, metadata), 1):
            name = f"E{index}"
            root = output / "arms" / name
            arm = {"label": f"Imported candidate {index}", "declared_model": label,
                   "models": [], "model_identity_basis": "owner-reported, unverified", "status": "running",
                   "cost_usd": meta.get("cost_usd"), "tokens": _tokens([{"usage": {k: v for k, v in meta.items() if k in TOKEN_FIELDS}}]),
                   "usage_basis": "owner-reported, unverified", "receipts": [],
                   "response_sha256": fingerprint(payload), "summary": payload["summary"],
                   "input_policy": "independent_brief_and_readonly_files" if mode == "rebuild" else "legacy_source",
                   "input_policy_verified": False}
            result["arms"][name] = arm
            write_json(output / "responses" / f"{name}.json", payload)
            save()
            try:
                write_bundle(root, {n: text for n, text in original.sources.items() if mode != "rebuild" or n in readonly})
                if mode == "rebuild":
                    write_rebuild(root, payload["files"], writable)
                else:
                    apply_edits(root, payload["edits"], writable,
                                context={n: p for n, p in capsule.get("context", {}).items() if n in writable})
                candidate = artifact_from_sources({n: (root / n).read_bytes().decode("utf-8") for n in capsule["files"]}, capsule.get("context"))
                arm["source_sha256"] = candidate.identity
                selected = bool(capsule.get("context"))
                arm["diff"] = _diff(original.context, candidate.context, selected)
                arm["diff_kind"] = "selected_context" if selected else "full_source"
                arm["diff_note"] = "Selected-source display diff; original response is retained separately." if selected else "Unified diff of the full allowlisted source."
                atomic_text(output / f"{name}.diff", arm["diff"])
                previous = measured.get(candidate.identity)
                if previous is not None:
                    arm["evaluation"] = copy.deepcopy(result["arms"][previous]["evaluation"])
                    arm["evaluation_reused_from"] = previous
                else:
                    arm["evaluation"] = assess(name, root)
                    if arm["evaluation"]["status"] == "completed":
                        measured[candidate.identity] = name
                arm["status"] = arm["evaluation"]["status"]
            except (CapsuleError, OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
                arm.update(status="failed", error=str(error))
            save()
        for left, right in itertools.combinations(result["arms"], 2):
            comparison = compare_results(result["arms"][left].get("evaluation", {}), result["arms"][right].get("evaluation", {}))
            comparison["basis"] = "Measured artifact behavior, not verified model uplift or equal-cost generation"
            result["comparisons"][f"{left}_{right}"] = comparison
        result["status"] = "completed" if all(a["status"] == "completed" for a in result["arms"].values()) else "inconclusive"
    except KeyboardInterrupt:
        result.update(status="interrupted", error="Local assessment interrupted; no provider was dispatched")
    except Exception as error:
        result.update(status="inconclusive", error=str(error))
        save()
        raise
    try:
        result["source_unchanged"] = load_request(request_path)[2].identity == original.identity
    except (CapsuleError, OSError, ValueError):
        result["source_unchanged"] = False
    result["manifest"]["source_unchanged_scope"] = "Prepared snapshot; original source is not accessed during assessment"
    if not result["source_unchanged"]:
        result["status"] = "inconclusive_source_changed"
    save()
    return result
