"""Explicit, portable exports from a whitelist, never a copy of a private run."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

from .core import CapsuleError, write_json
from .provider import COST_BASIS
from .report import write_report
from .assessment import IMPORTED_COST_BASIS


LABELS = {"A": "Saved artifact", "B": "Ordinary improvement", "C": "Intent-first reframe",
          "D": "Clean-slate rebuild", "R": "Hand-authored reference (no model)"}
STATUSES = {"completed", "inconclusive", "inconclusive_baseline_error", "inconclusive_source_changed",
            "probe_completed", "skipped_baseline_passes", "interrupted", "failed",
            "remote_outcome_unknown", "skipped_budget", "error", "running"}
MODEL = re.compile(r"claude-(?:(?:sonnet|opus|haiku)(?:[-.]\d{1,8})+|(?:\d{1,8}-)+(?:sonnet|opus|haiku)(?:-\d{1,8})?)\Z")


def _object(value, name):
    if not isinstance(value, dict):
        raise CapsuleError(f"Invalid {name}: expected an object")
    return value


def _number(value, *, integer=False):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (integer and type(value) is not int):
        raise CapsuleError("Shared metrics must be finite nonnegative numbers (integer counts)")
    return value


def _list(value, name, limit=50):
    if not isinstance(value, list) or len(value) > limit:
        raise CapsuleError(f"Invalid or oversized {name}")
    return value


def share_result(result_path: Path, output: Path, *, title="Second Look comparison",
                 include_intent=False, include_screenshots=False) -> Path:
    result_path = Path(result_path).resolve()
    destination = Path(output).absolute()
    if destination.exists() or destination.is_symlink():
        raise CapsuleError("Share output must be a new directory")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise CapsuleError("Share title must contain 1–200 characters")
    if result_path.stat().st_size > 32 * 1024 * 1024:
        raise CapsuleError("Result exceeds the 32 MiB sharing limit")
    raw_bytes = result_path.read_bytes()
    raw = _object(json.loads(raw_bytes), "result")
    capsule = _object(raw.get("capsule"), "capsule")
    kind = raw.get("kind")
    if kind not in {"live_model", "offline_reference", "baseline_probe", "imported_candidates"}:
        raise CapsuleError("Unsupported result kind")
    imported = kind == "imported_candidates"
    labels = {"A": "Saved artifact", **{f"E{i}": f"Imported candidate {i}" for i in range(1, 5)}} if imported else LABELS
    checks, mapping = [], {}
    for index, item in enumerate(_list(capsule.get("checks"), "checks"), 1):
        item = _object(item, "check")
        old_id = item.get("id")
        if not isinstance(old_id, str) or old_id in mapping:
            raise CapsuleError("Checks need unique string identities")
        ident = f"check-{index}"
        mapping[old_id] = ident
        check = {"id": ident, "name": f"Check {index}"}
        if item.get("category") in {"intent", "preservation"}:
            check.update(category=item["category"], basis="Acceptance definition excluded from this export")
        if item.get("held_out") is True:
            check["held_out"] = True
        checks.append(check)
    if not checks:
        raise CapsuleError("No acceptance checks in this result")
    intent = {"text": "Intent text was not included in this export."}
    if include_intent:
        text = _object(capsule.get("intent", {}), "intent").get("text", "Unrecorded")
        if not isinstance(text, str) or len(text) > 32_000:
            raise CapsuleError("Intent text is invalid or exceeds 32,000 characters")
        intent = {"text": text, "source": "Explicitly included by the exporter",
                  "confirmed": capsule.get("intent", {}).get("confirmed") is True}
    public = {"version": 1, "kind": kind,
              "status": raw.get("status") if raw.get("status") in STATUSES else "inconclusive",
              "capsule": {"title": title, "checks": checks, "intent": intent,
                          "baseline": {"provenance": "Historical model authorship is unverified; source provenance excluded from this summary."}},
              "arms": {}, "comparisons": {}, "manifest": {"input_result_sha256": hashlib.sha256(raw_bytes).hexdigest()},
              "model_calls": _number(raw.get("model_calls"), integer=True),
              "sharing": {"metrics_only": not (include_intent or include_screenshots),
                          "intent_included": include_intent, "screenshots_included": include_screenshots,
                          "note": "Source, raw prompts/receipts, check definitions, private labels and paths are excluded. Metrics are reported from the input result; this export is not independent verification."}}
    if kind == "offline_reference":
        public["capsule"]["baseline"]["provenance"] = "Deliberately flawed synthetic fixture; not a historical model output."
    if type(raw.get("source_unchanged")) is bool:
        public["source_unchanged"] = raw["source_unchanged"]
    for key in ("source", "checks"):
        value = _object(raw.get("manifest", {}), "manifest").get(key)
        if isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value):
            public["manifest"][key] = value
    cost = _object(raw.get("cost", {}), "cost")
    public["cost"] = {key: _number(cost.get(key)) for key in ("total_usd", "limit_usd", "known_spend_usd")}
    # A missing known-spend field must not be invented as zero for the renderer.
    public["cost"]["basis"] = IMPORTED_COST_BASIS if imported else COST_BASIS if kind == "live_model" else "No model was called"
    image_bytes = 0
    for name, original in _object(raw.get("arms"), "arms").items():
        if name not in labels:
            raise CapsuleError("Unsupported workflow in result")
        original = _object(original, "workflow")
        models = _list(original.get("models", []), "models", 10)
        model_ids = [m for m in models if isinstance(m, str) and len(m) < 100 and MODEL.fullmatch(m)]
        if imported:
            model_ids = []
        if name == "R" and kind == "offline_reference":
            model_ids = ["none: hand-authored reference"]
        elif name == "A" and not model_ids:
            model_ids = ["unknown"]
        arm = {"label": labels[name], "status": original.get("status") if original.get("status") in STATUSES else "error",
               "models": model_ids, "cost_usd": _number(original.get("cost_usd")),
               "tokens": {"total": _number(_object(original.get("tokens", {}), "tokens").get("total"), integer=True)}}
        if "budget_usd" in original:
            arm["budget_usd"] = _number(original["budget_usd"])
        reused = original.get("evaluation_reused_from")
        if imported and reused is not None:
            if reused not in public["arms"]:
                raise CapsuleError("Reused evaluation must refer to an earlier imported arm")
            arm["evaluation_reused_from"] = reused
        if "evaluation" in original:
            old_eval = _object(original["evaluation"], "evaluation")
            total = _number(old_eval.get("total"), integer=True)
            passed = _number(old_eval.get("passed"), integer=True)
            if total != len(checks) or (passed is not None and passed > total):
                raise CapsuleError("Evaluation counts do not match captured checks")
            evaluation = {"status": "completed" if old_eval.get("status") == "completed" else "error",
                          "passed": passed, "total": total, "checks": [], "screenshots": {}}
            seen = set()
            for row in _list(old_eval.get("checks", []), "evaluated checks"):
                row = _object(row, "evaluated check")
                ident = row.get("id")
                if not isinstance(ident, str) or ident not in mapping or ident in seen:
                    raise CapsuleError("Evaluation contains an unknown or duplicate check")
                seen.add(ident)
                measured = type(row.get("passed")) is bool and row.get("error_kind") != "harness"
                evaluation["checks"].append({"id": mapping[ident], "passed": row.get("passed") is True if measured else False,
                                              "error_kind": "behavior" if measured else "harness"})
            if include_screenshots:
                for index, (state, path) in enumerate(_object(old_eval.get("screenshots", {}), "screenshots").items(), 1):
                    if not isinstance(path, str):
                        raise CapsuleError("Invalid screenshot path")
                    candidate = Path(path)
                    candidate = (candidate if candidate.is_absolute() else result_path.parent / candidate).resolve()
                    if not candidate.is_relative_to(result_path.parent) or not candidate.is_file():
                        raise CapsuleError("Screenshots must exist within the input run directory")
                    size = candidate.stat().st_size
                    image_bytes += size
                    if size > 20 * 1024 * 1024 or image_bytes > 64 * 1024 * 1024:
                        raise CapsuleError("Screenshot export exceeds the size limit (20 MiB per PNG, 64 MiB total)")
                    with candidate.open("rb") as stream:
                        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                            raise CapsuleError("Only PNG screenshots can be shared")
                    label = "initial" if state == "initial" else mapping.get(state, f"state-{index}")
                    evaluation["screenshots"][label] = str(candidate)
            arm["evaluation"] = evaluation
        public["arms"][name] = arm
    if "A" not in public["arms"]:
        raise CapsuleError("Result needs a saved-artifact baseline")
    for key, comparison in _object(raw.get("comparisons", {}), "comparisons").items():
        if key not in {f"{a}_{b}" for a in public["arms"] for b in public["arms"] if a != b}:
            raise CapsuleError("Comparison refers to an unknown workflow")
        comparison = _object(comparison, "comparison")
        verdict = comparison.get("verdict")
        public["comparisons"][key] = {"verdict": verdict if verdict in {"improved", "regression", "no_measured_gain"} else "inconclusive"}
        for field in ("improvements", "regressions"):
            identities = _list(comparison.get(field, []), "comparison changes")
            if any(not isinstance(i, str) or i not in mapping for i in identities):
                raise CapsuleError("Comparison contains an unknown check")
            public["comparisons"][key][field] = [mapping[i] for i in identities]
    # All input validation precedes creating the public directory.
    destination.mkdir(parents=True, exist_ok=False)
    try:
        rendered = write_report(public, destination)
        rendered.rename(destination / "index.html")
        summary = copy.deepcopy(public)
        for arm in summary["arms"].values():
            if "evaluation" in arm:
                arm["evaluation"]["screenshots"] = {}  # images are embedded in HTML; paths never leave this machine
        write_json(destination / "summary.json", summary)
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination / "index.html"
