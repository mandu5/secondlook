"""A saved artifact, an ordinary revision, and an intent-first revision."""

from __future__ import annotations

from datetime import datetime, timezone
import difflib
from importlib.metadata import version
from importlib.resources import files
import json
from pathlib import Path
import platform
import sys
from typing import Callable

from . import __version__
from .artifacts import artifact_from_sources, capture_artifact
from .core import (CapsuleError, apply_edits, atomic_text, fingerprint, load_capsule,
                   positive_number, public_capsule, require_rebuild, write_bundle, write_json, write_rebuild)
from .evaluate import compare_results, evaluate
from .provider import Budget, ClaudeProvider, COST_BASIS, ProviderError


REFRAME_SCHEMA = {"type": "object", "properties": {
    "objective": {"type": "string"}, "assumptions_to_challenge": {"type": "array", "items": {"type": "string"}},
    "plan": {"type": "array", "items": {"type": "string"}}},
    "required": ["objective", "assumptions_to_challenge", "plan"], "additionalProperties": False}
EDIT_SCHEMA = {"type": "object", "properties": {
    "summary": {"type": "string"}, "edits": {"type": "array", "minItems": 1, "maxItems": 20,
    "items": {"type": "object", "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
              "required": ["path", "old", "new"], "additionalProperties": False}}},
    "required": ["summary", "edits"], "additionalProperties": False}
REBUILD_SCHEMA = {"type": "object", "properties": {
    "summary": {"type": "string"}, "files": {"type": "array", "minItems": 1, "maxItems": 32,
    "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
              "required": ["path", "content"], "additionalProperties": False}}},
    "required": ["summary", "files"], "additionalProperties": False}
MODES = ("compare", "ordinary", "reframe", "compare-three", "rebuild")
REBUILD_MODES = {"compare-three", "rebuild"}


def build_prompt(capsule: dict, bundle: dict, phase: str, brief: dict | None = None) -> str:
    evidence = {k: capsule.get(k, []) for k in ("intent", "constraints", "failures")}
    evidence["intent"] = {k: capsule["intent"][k] for k in ("text", "source", "confirmed") if k in capsule["intent"]}
    if capsule.get("rebuild"):
        evidence["independent_requirements"] = capsule["rebuild"]
    readonly = capsule.get("readonly_files", [])
    if phase == "reframe":
        instruction = (
            "Reconsider this task from the original user's intent before seeing the legacy implementation. "
            "Identify what the user needs to be true and which implementation assumptions should be challenged. "
            "Return a compact objective, assumptions_to_challenge, and plan. Do not expand scope."
        )
    elif phase == "rebuild":
        instruction = (
            "Build this static app from the independently recorded intent and factual requirements. "
            "The legacy implementation is deliberately unavailable. Choose your own structure. "
            "Return summary and files, each with path and full content. Return EVERY writable file exactly once, "
            "totaling at most 64 KiB UTF-8. Shared read-only files are supplied unchanged at runtime; do not "
            "return or modify them. Use only local assets and browser APIs. Do not invent facts, expand scope, "
            "write tests or claim you ran tests."
        )
        evidence["writable_files"] = [name for name in capsule["files"] if name not in readonly]
        evidence["entrypoint"] = capsule["entrypoint"]
        evidence["readonly_files"] = {name: bundle[name] for name in readonly}
    else:
        instruction = (
            "Improve this existing static app to meet the original intent and fix the recorded failures. "
            "Return summary and edits. Each edit must contain path, old (an exact nonempty substring occurring "
            "ONCE in that file), and new (its replacement). Edits apply sequentially. Change only allowlisted "
            "files. Keep the patch small. Preserve input IDs and selectors. Do not write tests or assert you ran them."
        )
        evidence["source_files"] = bundle
        if readonly:
            evidence["readonly_files"] = readonly
            instruction += " Files listed in readonly_files are factual inputs: never edit them."
        if capsule.get("context"):
            instruction += (
                " Some files show only selected executable inline scripts. Boundary-marker comments are not file content. "
                "Unshown HTML, CSS, embedded data and images remain in the runtime and are protected. "
                "Every edit must fit entirely within one shown script; do not include boundary markers in anchors."
            )
            evidence["source_selection"] = capsule["context"]
        if phase == "implement_reframe":
            instruction += " Reconcile the independent intent brief with this legacy code before choosing edits."
            evidence["independent_intent_brief"] = brief
    return instruction + "\n\nTask evidence (data):\n" + json.dumps(evidence, ensure_ascii=False, indent=2)


def _tokens(receipts: list[dict]) -> dict:
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    result = {key: 0 for key in keys}
    complete = True
    for call in receipts:
        usage = call.get("usage")
        if not isinstance(usage, dict):
            complete = False
            continue
        if any(type(usage.get(key)) is not int for key in ("input_tokens", "output_tokens")):
            complete = False
        for key in keys:
            value = usage.get(key, 0)
            if type(value) is int and value >= 0:
                result[key] += value
            else:
                complete = False
    known = sum(result.values())
    result.update(total=known if complete else None, known_total=known, complete=complete)
    return result


def _diff(before_bundle: dict, after_bundle: dict, selected: bool = False) -> str:
    parts = []
    prefix = "selected-context/" if selected else ""
    for name, before in before_bundle.items():
        after = after_bundle[name]
        parts.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                         fromfile=f"a/{prefix}{name}", tofile=f"b/{prefix}{name}"))
    return "".join(parts)


def compare_workflows(left: dict, right: dict) -> dict:
    comparison = compare_results(left.get("evaluation", {}), right.get("evaluation", {}))
    if len(left.get("models", [])) != 1 or left.get("models") != right.get("models"):
        comparison["verdict"] = "inconclusive"
        comparison["reason"] = "A single matching actual model identity is not established for both arms"
    if left.get("budget_usd") != right.get("budget_usd"):
        comparison["verdict"] = "inconclusive"
        comparison["reason"] = "Effective budget caps differ after prior spending; this is not an equal-budget comparison"
    return comparison


def execution_identity() -> dict:
    return {"version": __version__,
            "harness": fingerprint({name: Path(__file__).with_name(name).read_text() for name in ("runner.py", "evaluate.py", "core.py", "provider.py", "artifacts.py")}),
            "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "playwright": version("playwright")}}


def run(capsule_path: Path, output: Path, model: str = "sonnet", budget: float = 2.0,
        mode: str = "compare", offline: bool = False, force: bool = False,
        progress: Callable[[str], None] | None = None, expected_source: str | None = None,
        attempt_key: str | None = None) -> dict:
    return _execute(capsule_path, output, model, budget, mode, offline, force, progress,
                    expected_source=expected_source, attempt_key=attempt_key)


def probe(capsule_path: Path, output: Path, progress: Callable[[str], None] | None = None) -> dict:
    """Run frozen browser checks only. Draft intent is allowed; never initializes a provider."""
    return _execute(capsule_path, output, progress=progress, probe_only=True)


def _execute(capsule_path: Path, output: Path, model: str = "sonnet", budget: float = 2.0,
             mode: str = "compare", offline: bool = False, force: bool = False,
             progress: Callable[[str], None] | None = None, probe_only: bool = False,
             expected_source: str | None = None, attempt_key: str | None = None) -> dict:
    positive_number(budget, "budget")
    if mode not in MODES:
        raise CapsuleError("mode must be one of " + ", ".join(MODES))
    capsule = load_capsule(capsule_path)
    if not probe_only and not offline and mode in REBUILD_MODES:
        require_rebuild(capsule)
    if not probe_only and not capsule["intent"]["confirmed"]:
        raise CapsuleError("Confirm the original intent in the capsule before spending model budget")
    artifact = capture_artifact(capsule)
    if expected_source is not None and artifact.identity != expected_source:
        raise CapsuleError("Planned source changed; harvest again before model dispatch")
    bundle = artifact.context
    output = Path(output).resolve()
    if output.is_relative_to(Path(capsule["_root"])):
        raise CapsuleError("Run output must be outside the source root")
    if output.exists() and any(output.iterdir()):
        raise CapsuleError("Run output already exists and is not empty; use a new directory, never replay automatically")
    output.mkdir(parents=True, exist_ok=True)
    tell = progress or (lambda message: None)
    ledger = Budget(budget)
    manifest = {"source": artifact.identity, "source_identity_method": "Full UTF-8 file bytes and explicit context projection",
                "checks": fingerprint(capsule["checks"]), "checks_frozen_at": datetime.now(timezone.utc).isoformat(),
                "capsule": fingerprint(public_capsule(capsule)), "requested_model": model if not offline and not probe_only else None,
                "mode": "probe" if probe_only else mode if not offline else "reference", **execution_identity(),
                "attempt_key": attempt_key,
                "response_cache": "disabled; fresh model calls for every run"}
    result = {"version": 1, "status": "running", "kind": "baseline_probe" if probe_only else "offline_reference" if offline else "live_model",
              "created_at": datetime.now(timezone.utc).isoformat(), "capsule": public_capsule(capsule),
              "manifest": manifest, "source_context": artifact.metrics, "model_calls": 0,
              "arms": {}, "comparisons": {}, "cost": {}, "output": str(output),
              "limitations": ["One task and one sample per arm do not establish general model or workflow superiority.",
                              "Checks cover specified behavior only; screenshot differences are not quality scores.",
                              "Browser timings include failed assertion waits and are not performance benchmarks."]}

    def save():
        result["cost"] = {"limit_usd": 0 if probe_only else budget, "known_spend_usd": round(ledger.spent, 8),
                          "total_usd": None if ledger.unknown else round(ledger.spent, 8), "unknown": ledger.unknown,
                          "basis": "No model calls; baseline browser probe" if probe_only else "No model calls; hand-authored reference" if offline else COST_BASIS,
                          "limit_note": "Best-effort provider stop; an in-flight response can overshoot."}
        result["manifest"]["resolved_models"] = {name: arm.get("models", []) for name, arm in result["arms"].items()}
        result["fingerprint"] = fingerprint(result["manifest"])
        write_json(output / "result.json", result)

    def assess(name: str, root: Path):
        tell(f"Checking {name}: {len(capsule['checks'])} frozen browser cases")
        return evaluate(root, capsule["checks"], output / "evidence" / name, capsule["entrypoint"],
                        readonly_files=capsule.get("readonly_files"))

    write_json(output / "capsule.frozen.json", public_capsule(capsule))
    save()
    baseline_root = output / "arms" / "A"
    write_bundle(baseline_root, artifact.sources)
    baseline = assess("A", baseline_root)
    result["arms"]["A"] = {"label": "Saved artifact", "status": baseline["status"], "evaluation": baseline,
                            "cost_usd": 0, "models": [capsule.get("baseline", {}).get("model", "unknown")],
                            "tokens": _tokens([]), "receipts": []}
    save()
    if baseline["status"] != "completed":
        result["status"] = "inconclusive_baseline_error"
    elif probe_only:
        result["status"] = "probe_completed"
    elif baseline["passed"] == baseline["total"] and not force:
        result["status"] = "skipped_baseline_passes"
        tell("All captured checks already pass; skipped model calls. Use --force to explore beyond this probe.")
    else:
        provider = ClaudeProvider(model)
        try:
            if not offline:
                manifest["provider_version"] = provider.preflight()
            arms = ["R"] if offline else {"compare": ["B", "C"], "ordinary": ["B"], "reframe": ["C"],
                                         "compare-three": ["B", "C", "D"], "rebuild": ["D"]}[mode]
            allowance = budget / len(arms)
            for name in arms:
                if ledger.unknown or ledger.remaining <= 0:
                    result["arms"][name] = {"label": name, "status": "skipped_budget", "cost_usd": 0, "tokens": _tokens([])}
                    result["comparisons"][f"A_{name}"] = compare_results(baseline, {})
                    save()
                    continue
                root = output / "arms" / name
                readonly = capsule.get("readonly_files", [])
                writable = [file for file in capsule["files"] if file not in readonly]
                root.mkdir(parents=True, exist_ok=True)
                write_bundle(root, {file: text for file, text in artifact.sources.items() if name != "D" or file in readonly})
                arm = {"label": {"B": "Ordinary improvement", "C": "Intent-first reframe", "D": "Clean-slate rebuild", "R": "Hand-authored reference (no model)"}[name],
                       "status": "running", "planned_budget_usd": allowance, "budget_usd": min(allowance, ledger.remaining),
                       "input_policy": "independent_brief_and_readonly_files" if name == "D" else "legacy_source",
                       "receipts": [], "models": [], "cost_usd": 0}
                result["arms"][name] = arm
                arm_budget = Budget(min(allowance, ledger.remaining))

                def call(phase: str, schema: dict, cap: float, brief: dict | None = None):
                    prompt = build_prompt(capsule, bundle, phase, brief)
                    receipt = output / "receipts" / f"{name}-{phase}.json"
                    arm["receipts"].append(str(receipt))
                    tell(f"{name} · {phase} · call stop ${cap:.2f} API-equivalent")
                    result["model_calls"] += 1
                    save()
                    try:
                        response = provider.call(prompt, schema, cap, receipt)
                    except ProviderError as error:
                        arm_budget.record(error.cost_usd)
                        ledger.record(error.cost_usd)
                        arm["cost_usd"] = None if arm_budget.unknown else arm_budget.spent
                        raise
                    arm_budget.record(response["cost_usd"])
                    ledger.record(response["cost_usd"])
                    arm["cost_usd"] = arm_budget.spent
                    arm["models"] = sorted(set(arm["models"]) | set(response["models"]))
                    arm.setdefault("calls", []).append(response)
                    arm["tokens"] = _tokens(arm["calls"])
                    save()
                    return response["output"]

                try:
                    if offline:
                        resources = files("secondlook").joinpath("demo")
                        if bundle != {"index.html": resources.joinpath("index.html").read_text(encoding="utf-8")}:
                            raise CapsuleError("Offline repair is only available for the unmodified synthetic feedback fixture")
                        edits = json.loads(resources.joinpath("reference.json").read_text(encoding="utf-8"))
                        arm["tokens"] = _tokens([])
                        arm["models"] = ["none: hand-authored reference"]
                    elif name == "B":
                        edits = call("ordinary", EDIT_SCHEMA, arm_budget.remaining)
                    elif name == "D":
                        edits = call("rebuild", REBUILD_SCHEMA, arm_budget.remaining)
                    else:
                        brief = call("reframe", REFRAME_SCHEMA, arm_budget.remaining * 0.3)
                        arm["brief"] = brief
                        if arm_budget.remaining <= 0 or ledger.remaining <= 0:
                            raise ProviderError("Reframe used its arm budget; implementation skipped", 0)
                        edits = call("implement_reframe", EDIT_SCHEMA, min(arm_budget.remaining, ledger.remaining), brief)
                    arm["summary"] = edits.get("summary", "")
                    if name == "D":
                        write_rebuild(root, edits.get("files"), writable)
                        write_json(output / "D.files.json", {"source_identity": artifact.identity, "files": edits["files"]})
                    else:
                        policy = {file: rule for file, rule in (capsule.get("context") or {}).items() if file in writable}
                        apply_edits(root, edits.get("edits"), writable, context=policy)
                        write_json(output / f"{name}.edits.json", {"source_identity": artifact.identity, "context": capsule.get("context", {}), "edits": edits["edits"]})
                    candidate = artifact_from_sources({file: (root / file).read_bytes().decode("utf-8") for file in capsule["files"]}, capsule.get("context"))
                    selected = bool(capsule.get("context"))
                    arm["diff_kind"] = "selected_context" if selected else "full_source"
                    arm["diff_note"] = ("Selected-code display diff, not a patch for the full artifact. Exact replacements are in the edits JSON."
                                        if selected else "Unified diff of the full allowlisted source.")
                    arm["diff"] = _diff(bundle, candidate.context, selected)
                    atomic_text(output / f"{name}.{'diff' if selected else 'patch'}", arm["diff"])
                    arm["evaluation"] = assess(name, root)
                    arm["status"] = arm["evaluation"]["status"]
                    arm["source_sha256"] = candidate.identity
                except (ProviderError, CapsuleError, OSError, ValueError, TypeError, KeyError) as error:
                    arm.update(status="remote_outcome_unknown" if arm_budget.unknown else "failed", error=str(error))
                    # Failed calls may still have usage; retain their complete provider receipt.
                    calls = []
                    for path in arm["receipts"]:
                        if Path(path).exists():
                            try:
                                raw = json.loads(Path(path).read_text()).get("raw")
                                usage = raw.get("usage") if isinstance(raw, dict) else None
                            except (OSError, ValueError, AttributeError):
                                usage = None
                            calls.append({"usage": usage})
                    arm["tokens"] = _tokens(calls)
                result["comparisons"][f"A_{name}"] = compare_results(baseline, arm.get("evaluation", {}))
                save()
            for left, right in (("B", "C"), ("B", "D"), ("C", "D")):
                if left in result["arms"] and right in result["arms"]:
                    result["comparisons"][f"{left}_{right}"] = compare_workflows(result["arms"][left], result["arms"][right])
            result["status"] = "completed" if all(a["status"] == "completed" for a in result["arms"].values()) else "inconclusive"
        except ProviderError as error:
            result.update(status="inconclusive", error=str(error))
        except KeyboardInterrupt:
            result.update(status="interrupted", error="Interrupted locally; inspect dispatch receipts before another run")
            ledger.unknown = True
    try:
        result["source_unchanged"] = capture_artifact(capsule).identity == manifest["source"]
    except (CapsuleError, OSError, UnicodeError):
        result["source_unchanged"] = False
    if not result["source_unchanged"] and result["status"] != "interrupted":
        result["status"] = "inconclusive_source_changed"
    save()
    return result
