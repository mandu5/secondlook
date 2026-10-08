"""Explainable budget allocation and exactly-once local campaign claims.

Provider completion cannot be guaranteed exactly once: uncertain calls remain
blocked. There is deliberately no lease timeout or implicit remote retry.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import sys
from uuid import uuid4

from . import __version__
from .artifacts import capture_artifact
from .core import CapsuleError, fingerprint, load_capsule, positive_number, public_capsule, require_rebuild, write_json
from .library import Library, dumps, now
from .report import write_report
from .runner import MODES, REBUILD_MODES, _tokens, execution_identity, run


def harness_identity() -> str:
    names = ("runner.py", "evaluate.py", "core.py", "provider.py", "artifacts.py", "portfolio.py")
    return fingerprint({"code": {name: Path(__file__).with_name(name).read_text() for name in names},
                        "version": __version__, "python": sys.version, "platform": platform.platform(),
                        "playwright": version("playwright")})


def current_source(record: dict) -> str:
    capsule = load_capsule(Path(record["capsule_path"]))
    normalized = public_capsule(capsule)
    normalized["root"] = capsule["_root"]
    if normalized != record["capsule"]:
        raise CapsuleError("Capsule changed; harvest the task again")
    identity = capture_artifact(capsule).identity
    if identity != record["source_identity"]:
        raise CapsuleError("Source changed; harvest the task again")
    return identity


def make_plan(library: Library, candidate_id: str, budget: float, mode: str = "reframe", trial: int = 1,
              *, offline: bool = False, trigger: dict | None = None) -> dict:
    budget = positive_number(budget, "campaign budget")
    if mode not in MODES:
        raise CapsuleError("Unknown revisit mode")
    if type(trial) is not int or not 1 <= trial <= 10000:
        raise CapsuleError("trial must be an explicit integer from 1 through 10000")
    candidate = library.candidate(candidate_id)
    records = library.records()
    harness = harness_identity()
    with library.transaction() as db:
        attempted = {row[0] for row in db.execute("SELECT key FROM attempts")}
    plan_id = uuid4().hex
    decisions, selected, allocated = [], [], 0.0
    ordered = sorted(records, key=lambda r: (-r["revisit"]["impact"] / r["revisit"]["estimated_usd"], r["id"]))
    for record in ordered:
        overlap = sorted(set(record["revisit"]["capabilities"]) & set(candidate["capabilities"]))
        key = fingerprint({"task": record["revision"], "candidate": candidate["revision"], "harness": harness,
                           "mode": mode, "trial": trial, "offline": offline})
        decision = {"task_id": record["id"], "title": record["title"], "task_revision": record["revision"],
                    "capability_overlap": overlap, "declared_impact": record["revisit"]["impact"],
                    "allocation_usd": record["revisit"]["estimated_usd"], "attempt_key": key}
        reason = "selected"
        if record["adapter"] is None:
            reason = "no_execution_adapter"
        elif not record["intent"]["confirmed"]:
            reason = "unconfirmed_intent"
        elif not overlap:
            reason = "no_capability_match"
        else:
            if mode in REBUILD_MODES and not offline:
                try:
                    require_rebuild(record["capsule"])
                except CapsuleError as error:
                    reason, decision["detail"] = "needs_rebuild_contract", str(error)
            try:
                current_source(record)
            except (CapsuleError, OSError, ValueError) as error:
                reason, decision["detail"] = "needs_reharvest", str(error)
            if reason == "selected" and key in attempted:
                reason = "already_attempted"
            if reason == "selected" and allocated + decision["allocation_usd"] > budget + 1e-9:
                reason = "budget"
        decision["reason"] = reason
        decisions.append(decision)
        if reason == "selected":
            allocated += decision["allocation_usd"]
            selected.append({**decision, "record": record,
                             "output": str(library.path / "runs" / plan_id / record["id"])})
    plan = {"id": plan_id, "created_at": now(), "candidate": candidate, "budget_usd": budget,
            "allocated_usd": round(allocated, 8), "mode": mode, "trial": trial, "offline": offline,
            "harness": harness, "execution_identity": execution_identity(),
            "selected": selected, "decisions": decisions, "trigger": trigger,
            "method": "Declared impact / declared cost, with capability overlap. Not predicted uplift.",
            "model_calls": 0}
    with library.transaction() as db:
        db.execute("INSERT INTO plans VALUES(?,?,?,NULL)", (plan_id, dumps(plan), "planned"))
    return {**plan, "status": "planned"}


def get_plan(library: Library, plan_id: str) -> dict:
    with library.transaction() as db:
        row = db.execute("SELECT body,status,result FROM plans WHERE id=?", (plan_id,)).fetchone()
    if row is None:
        raise CapsuleError(f"Unknown plan: {plan_id}")
    return {**json.loads(row[0]), "status": row[1], "result": json.loads(row[2]) if row[2] else None}


def claim_plan(library: Library, plan_id: str) -> dict:
    """One durable claim, including all attempt reservations, in one transaction."""
    with library.transaction() as db:
        row = db.execute("SELECT body,status FROM plans WHERE id=?", (plan_id,)).fetchone()
        if row is None or row[1] != "planned":
            raise CapsuleError("Plan is missing or already claimed; inspect/reconcile it, do not replay")
        if db.execute("SELECT 1 FROM plans WHERE status IN ('running','needs_reconciliation')").fetchone():
            raise CapsuleError("A campaign is running or needs reconciliation; no new dispatch")
        plan = json.loads(row[0])
        for kind, key, revision in [("candidate", plan["candidate"]["id"], plan["candidate"]["revision"])] + [
                ("task", item["task_id"], item["task_revision"]) for item in plan["selected"]]:
            head = db.execute("SELECT revision FROM heads WHERE kind=? AND id=?", (kind, key)).fetchone()
            if not head or head[0] != revision:
                raise CapsuleError("Task or candidate changed; make a new plan")
        for item in plan["selected"]:
            if db.execute("SELECT 1 FROM attempts WHERE key=?", (item["attempt_key"],)).fetchone():
                raise CapsuleError("An identical attempt is already reserved or recorded; make a new plan")
            db.execute("INSERT INTO attempts VALUES(?,?,?,?,?,NULL)",
                       (item["attempt_key"], plan_id, item["task_id"], "reserved", item["output"]))
        db.execute("UPDATE plans SET status='running' WHERE id=?", (plan_id,))
    return plan


@contextmanager
def dispatch_lock(library: Library):
    # The kernel releases this on process death. The durable journal does NOT
    # expire with it. Reconciliation cannot race a still-running worker.
    with (library.path / "dispatch.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CapsuleError("A local worker holds the dispatch lock") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def summarize(evidence: dict, item: dict, plan: dict) -> dict:
    manifest = evidence.get("manifest", {})
    if not isinstance(plan.get("execution_identity"), dict):
        raise CapsuleError("Legacy plan lacks a full execution binding; inspect its receipts separately")
    expected = {**plan["execution_identity"], "source": item["record"]["source_identity"],
                "checks": fingerprint(item["record"]["capsule"]["checks"]),
                "capsule": fingerprint(item["record"]["capsule"]), "attempt_key": item["attempt_key"],
                "requested_model": None if plan["offline"] else plan["candidate"]["runtime_model"],
                "mode": "reference" if plan["offline"] else plan["mode"]}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise CapsuleError("Result does not match the frozen attempt identity")
    if (evidence.get("capsule") != item["record"]["capsule"] or
            evidence.get("kind") != ("offline_reference" if plan["offline"] else "live_model") or
            Path(evidence.get("output", "")).resolve() != Path(item["output"]).resolve()):
        raise CapsuleError("Result body does not match its planned attempt")
    cost = evidence.get("cost", {})
    known = cost.get("known_spend_usd")
    total = cost.get("total_usd")
    def amount(value):
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    if (not amount(known) or type(cost.get("unknown")) is not bool or
            (total is not None and (not amount(total) or not math.isclose(total, known, abs_tol=1e-8)))):
        raise CapsuleError("Invalid or inconsistent result accounting")
    terminal = {"completed", "skipped_baseline_passes", "inconclusive", "inconclusive_source_changed", "inconclusive_baseline_error"}
    unknown = cost["unknown"] or total is None or evidence.get("status") not in terminal
    arms = evidence.get("arms", {})
    if not isinstance(arms, dict) or "A" not in arms:
        raise CapsuleError("Incomplete result: baseline evidence missing")
    calls = evidence.get("model_calls")
    if type(calls) is not int or calls < 0:
        raise CapsuleError("Invalid dispatched-call count")
    receipt_names = [name for key, arm in arms.items() if key != "A" for name in arm.get("receipts", [])]
    receipt_paths = [Path(name).resolve() for name in receipt_names]
    receipt_root = Path(item["output"]).resolve() / "receipts"
    disk_paths = {path.resolve() for path in receipt_root.glob("*.json")}
    if (len(receipt_paths) != calls or len(set(receipt_paths)) != calls or set(receipt_paths) != disk_paths or
            any(path.parent != receipt_root or path.suffix != ".json" for path in receipt_paths) or
            (plan["offline"] and calls)):
        raise CapsuleError("Dispatched calls do not have a complete unique receipt set")
    receipt_spend, usage = 0.0, []
    for path in receipt_paths:
        try:
            with path.open("rb") as stream:
                raw_receipt = stream.read(16 * 1024 * 1024 + 1)
            if len(raw_receipt) > 16 * 1024 * 1024:
                raise ValueError("oversized receipt")
            receipt = json.loads(raw_receipt)
            if receipt.get("requested_model") != plan["candidate"]["runtime_model"]:
                raise ValueError("receipt model mismatch")
            state, value = receipt.get("state"), receipt.get("cost_usd")
            raw = receipt.get("raw")
            if state == "not_dispatched":
                if value != 0:
                    raise ValueError("undispatched receipt has spending")
                usage.append({"usage": {"input_tokens": 0, "output_tokens": 0}})
            else:
                usage.append({"usage": raw.get("usage") if isinstance(raw, dict) else None})
                if state not in {"completed", "failed"}:
                    unknown = True
                if (not amount(value) or not isinstance(raw, dict) or
                        not amount(raw.get("total_cost_usd")) or not math.isclose(value, raw["total_cost_usd"], abs_tol=1e-8)):
                    unknown = True
                    continue
            receipt_spend += value
        except (OSError, ValueError, AttributeError, TypeError):
            unknown = True
            usage.append({"usage": None})
    if not math.isclose(known, receipt_spend, abs_tol=1e-8):
        unknown = True
    known = max(known, receipt_spend)
    token_data = _tokens(usage)
    known_tokens = token_data["known_total"]
    return {"task_id": item["task_id"], "title": item["title"], "status": evidence.get("status", "unknown"),
            "kind": evidence.get("kind"), "known_spend_usd": known,
            "total_usd": None if unknown else known, "unknown": unknown,
            "model_calls": calls, "known_tokens": known_tokens,
            "tokens": token_data["total"],
            "comparisons": evidence.get("comparisons", {}),
            "arms": {key: {"passed": arm.get("evaluation", {}).get("passed"),
                            "total": arm.get("evaluation", {}).get("total"), "models": arm.get("models", []),
                            "categories": arm.get("evaluation", {}).get("categories", {})}
                     for key, arm in arms.items()},
            "report": str(Path(item["output"]) / "report.html"), "result": str(Path(item["output"]) / "result.json")}


def _finish(library: Library, plan: dict, status: str, summaries: list[dict], error: str | None = None) -> dict:
    unknown = status == "needs_reconciliation" or any(s["unknown"] for s in summaries)
    known = round(sum(s["known_spend_usd"] for s in summaries), 8)
    with library.transaction() as db:
        unaccounted = db.execute("SELECT COUNT(*) FROM attempts WHERE plan_id=? AND status!='reserved' AND summary IS NULL", (plan["id"],)).fetchone()[0]
    known_calls = sum(s["model_calls"] for s in summaries)
    result = {"plan_id": plan["id"], "status": status, "tasks": summaries,
              "budget_usd": plan["budget_usd"], "known_spend_usd": known,
              "total_usd": None if unknown else known, "unknown": unknown,
              "model_calls": None if unaccounted else known_calls, "known_model_calls": known_calls,
              "tokens": None if any(s["tokens"] is None for s in summaries) or unknown else sum(s["tokens"] for s in summaries),
              "known_tokens": sum(s["known_tokens"] for s in summaries), "error": error,
              "cost_basis": "API-equivalent provider receipts; best-effort stop, not a subscription invoice"}
    with library.transaction() as db:
        db.execute("UPDATE plans SET status=?,result=? WHERE id=?", (status, dumps(result), plan["id"]))
        # Reserved work was never dispatched; it must remain eligible later.
        db.execute("DELETE FROM attempts WHERE plan_id=? AND status='reserved'", (plan["id"],))
    write_json(library.path / "runs" / plan["id"] / "campaign.json", result)
    return result


def _render(evidence: dict, output: Path, summary: dict) -> None:
    try:
        write_report(evidence, output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        summary["report_error"] = str(error)


def execute_plan(library: Library, plan_id: str, progress=None) -> dict:
    with dispatch_lock(library):
        pending = get_plan(library, plan_id)
        if pending["harness"] != harness_identity():
            raise CapsuleError("Harness or environment changed; make a new plan")
        for item in pending["selected"]:
            current_source(item["record"])
            if Path(item["output"]).exists():
                raise CapsuleError("Planned output already exists; inspect existing evidence")
        plan = claim_plan(library, plan_id)
        summaries, spent = [], 0.0
        for item in plan["selected"]:
            cap = item["allocation_usd"]
            if spent + cap > plan["budget_usd"] + 1e-9:
                return _finish(library, plan, "stopped_budget", summaries)
            try:
                current_source(item["record"])
            except (CapsuleError, OSError, ValueError) as error:
                return _finish(library, plan, "stopped_stale_source", summaries, str(error))
            capsule = library.path / "runs" / plan_id / "inputs" / f"{item['task_id']}.json"
            write_json(capsule, item["record"]["capsule"])
            with library.transaction() as db:
                db.execute("UPDATE attempts SET status='running' WHERE key=?", (item["attempt_key"],))
            try:
                evidence = run(capsule, Path(item["output"]), model=plan["candidate"]["runtime_model"],
                               budget=cap, mode=plan["mode"], offline=plan["offline"], progress=progress,
                               expected_source=item["record"]["source_identity"], attempt_key=item["attempt_key"])
                summary = summarize(evidence, item, plan)
                # Record cost before rendering: a report error cannot erase a paid attempt.
                summaries.append(summary)
                spent += summary["known_spend_usd"]
                _render(evidence, Path(item["output"]), summary)
                with library.transaction() as db:
                    db.execute("UPDATE attempts SET status=?,summary=? WHERE key=?",
                               ("unknown" if summary["unknown"] else "finished", dumps(summary), item["attempt_key"]))
                if summary["unknown"]:
                    return _finish(library, plan, "needs_reconciliation", summaries)
                if spent >= plan["budget_usd"] and item is not plan["selected"][-1]:
                    return _finish(library, plan, "stopped_budget", summaries)
            except (Exception, KeyboardInterrupt) as error:
                return _finish(library, plan, "needs_reconciliation", summaries, str(error))
        return _finish(library, plan, "completed", summaries)


def reconcile_plan(library: Library, plan_id: str) -> dict:
    """Read terminal evidence only. Never invokes a provider or replays work."""
    with dispatch_lock(library):
        plan = get_plan(library, plan_id)
        if plan["status"] not in {"running", "needs_reconciliation"}:
            return plan["result"] or {"plan_id": plan_id, "status": plan["status"]}
        summaries, unresolved = [], False
        with library.transaction() as db:
            rows = {row["key"]: dict(row) for row in db.execute("SELECT * FROM attempts WHERE plan_id=?", (plan_id,))}
        for item in plan["selected"]:
            attempt = rows.get(item["attempt_key"])
            if not attempt or attempt["status"] == "reserved":
                continue
            try:
                evidence = json.loads((Path(item["output"]) / "result.json").read_text())
                summary = summarize(evidence, item, plan)
            except (OSError, ValueError, KeyError, TypeError, CapsuleError):
                unresolved = True
                if attempt["summary"]:
                    summaries.append(json.loads(attempt["summary"]))
                continue
            summaries.append(summary)
            unresolved |= summary["unknown"]
            _render(evidence, Path(item["output"]), summary)
            with library.transaction() as db:
                db.execute("UPDATE attempts SET status=?,summary=? WHERE key=?",
                           ("unknown" if summary["unknown"] else "finished", dumps(summary), item["attempt_key"]))
        return _finish(library, plan, "needs_reconciliation" if unresolved else "reconciled", summaries)
