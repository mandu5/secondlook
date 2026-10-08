import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from secondlook.core import CapsuleError
from secondlook.fixtures import create_demo
from secondlook.library import Library
from secondlook.portfolio import make_plan, claim_plan, execute_plan, reconcile_plan, get_plan
from secondlook.runner import run
from test_library import problem, profile


def setup_library(tmp_path, count=1, passing=False):
    lib = Library(tmp_path / "library")
    for i in range(count):
        path = create_demo(tmp_path / f"task-{i}")
        data = json.loads(path.read_text())
        data.update(id=f"task-{i}", title=f"Task {i}")
        data["revisit"] = {"capabilities": ["coding"], "impact": 5-i, "estimated_usd": 0.5}
        if passing:
            data["checks"] = [{"id": "visible", "assert": {"selector": "body", "visible": True}}]
        path.write_text(json.dumps(data))
        lib.harvest_capsule(path)
    lib.register_candidate(profile())
    return lib


def test_queue_explains_budget_adapter_and_capability_exclusions(tmp_path):
    lib = setup_library(tmp_path, 2)
    lib.harvest_problem(problem())
    plan = make_plan(lib, "candidate", 0.5)
    decisions = {r["task_id"]: r["reason"] for r in plan["decisions"]}
    assert decisions == {"task-0": "selected", "task-1": "budget", "research": "no_execution_adapter"}
    assert plan["allocated_usd"] == 0.5
    data = profile("unmatched")
    data["capabilities"] = ["vision"]
    lib.register_candidate(data)
    assert not make_plan(lib, "unmatched", 1)["selected"]


def test_changed_source_cannot_execute_a_saved_plan(tmp_path):
    lib = setup_library(tmp_path)
    plan = make_plan(lib, "candidate", 1)
    record = lib.records()[0]
    source = Path(record["capsule"]["root"]) / "index.html"
    source.write_text(source.read_text() + "<!-- changed -->")
    with pytest.raises(CapsuleError, match="changed|stale|harvest"):
        execute_plan(lib, plan["id"])
    assert get_plan(lib, plan["id"])["status"] == "planned"
    assert make_plan(lib, "candidate", 1)["decisions"][0]["reason"] == "needs_reharvest"


def test_concurrent_claims_cannot_dispatch_same_campaign_twice(tmp_path):
    lib = setup_library(tmp_path)
    plan = make_plan(lib, "candidate", 1)
    def claim():
        try:
            claim_plan(Library(lib.path), plan["id"])
            return "claimed"
        except CapsuleError:
            return "blocked"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: claim(), range(2))) == ["blocked", "claimed"]
    with pytest.raises(CapsuleError):
        execute_plan(lib, make_plan(lib, "candidate", 1, trial=2)["id"])


def test_source_guard_is_inside_runner_before_output_or_model_dispatch(tmp_path):
    path = create_demo(tmp_path / "demo")
    with pytest.raises(CapsuleError, match="source"):
        run(path, tmp_path / "out", expected_source="incorrect")
    assert not (tmp_path / "out").exists()


def test_actual_browser_baseline_pass_costs_zero_and_suppresses_identical_retry(tmp_path):
    lib = setup_library(tmp_path, passing=True)
    plan = make_plan(lib, "candidate", 1)
    result = execute_plan(lib, plan["id"])
    assert result["status"] == "completed"
    assert result["known_spend_usd"] == 0 and result["model_calls"] == 0
    assert result["tasks"][0]["status"] == "skipped_baseline_passes"
    repeat = make_plan(lib, "candidate", 1)
    assert repeat["selected"] == []
    assert repeat["decisions"][0]["reason"] == "already_attempted"
    assert len(make_plan(lib, "candidate", 1, trial=2)["selected"]) == 1


@pytest.mark.parametrize("change", ["candidate", "checks"])
def test_stale_configuration_is_rejected_before_claim(tmp_path, change):
    lib = setup_library(tmp_path)
    plan = make_plan(lib, "candidate", 1)
    if change == "candidate":
        data = profile()
        data["revision"] = "changed"
        lib.register_candidate(data)
    else:
        path = Path(lib.records()[0]["capsule_path"])
        data = json.loads(path.read_text())
        data["checks"][0]["name"] = "changed"
        path.write_text(json.dumps(data))
    with pytest.raises(CapsuleError):
        execute_plan(lib, plan["id"])


def test_unknown_provider_spend_stops_other_projects_and_stays_blocked(tmp_path, monkeypatch):
    from secondlook.provider import ClaudeProvider, ProviderError
    lib = setup_library(tmp_path, 2)
    monkeypatch.setattr(ClaudeProvider, "preflight", lambda self: "test-cli")
    def unknown(self, prompt, schema, cap, receipt):
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"status": "dispatched", "cost_usd": None}))
        raise ProviderError("Unknown remote outcome", None)
    monkeypatch.setattr(ClaudeProvider, "call", unknown)
    result = execute_plan(lib, make_plan(lib, "candidate", 1, mode="ordinary")["id"])
    assert result["status"] == "needs_reconciliation"
    assert result["total_usd"] is None and result["model_calls"] == 1
    assert len(result["tasks"]) == 1
    with pytest.raises(CapsuleError):
        execute_plan(lib, make_plan(lib, "candidate", 1, trial=2)["id"])
    assert reconcile_plan(lib, result["plan_id"])["status"] == "needs_reconciliation"


def test_provider_overshoot_stops_next_task_even_if_its_reservation_exists(tmp_path, monkeypatch):
    from secondlook.provider import ClaudeProvider, ProviderError
    lib = setup_library(tmp_path, 2)
    monkeypatch.setattr(ClaudeProvider, "preflight", lambda self: "test-cli")
    def expensive(self, prompt, schema, cap, receipt):
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"state": "failed", "requested_model": self.model, "cost_usd": 1.1,
                                      "raw": {"total_cost_usd": 1.1, "usage": {"input_tokens": 10, "output_tokens": 1}}}))
        raise ProviderError("Provider overshot the cap", 1.1)
    monkeypatch.setattr(ClaudeProvider, "call", expensive)
    result = execute_plan(lib, make_plan(lib, "candidate", 1, mode="ordinary")["id"])
    assert result["status"] == "stopped_budget"
    assert result["known_spend_usd"] == 1.1 and len(result["tasks"]) == 1
    decisions = {r["task_id"]: r["reason"] for r in make_plan(lib, "candidate", 1)["decisions"]}
    assert decisions["task-1"] == "selected"


def test_reconciliation_never_replays_a_claimed_but_unfinished_attempt(tmp_path):
    lib = setup_library(tmp_path)
    plan = make_plan(lib, "candidate", 1)
    claim_plan(lib, plan["id"])
    # Reserved but not started is safe to release; running without final evidence is not.
    with lib.transaction() as db:
        db.execute("UPDATE attempts SET status='running' WHERE plan_id=?", (plan["id"],))
    result = reconcile_plan(lib, plan["id"])
    assert result["status"] == "needs_reconciliation"
    assert result["total_usd"] is None
    assert not Path(plan["selected"][0]["output"]).exists()


@pytest.mark.parametrize("field,value", [
    ("mode", "ordinary"), ("harness", "wrong"), ("capsule", "wrong"),
    ("attempt_key", "wrong"), ("environment", {}),
    ("bad_total", -100), ("missing_receipts", 2),
])
def test_reconciliation_rejects_partial_or_wrong_attempt_evidence(tmp_path, field, value):
    lib = setup_library(tmp_path, passing=True)
    plan = make_plan(lib, "candidate", 1)
    result = execute_plan(lib, plan["id"])
    path = Path(result["tasks"][0]["result"])
    evidence = json.loads(path.read_text())
    if field == "bad_total":
        evidence["cost"]["total_usd"] = value
    elif field == "missing_receipts":
        evidence["model_calls"] = value
    else:
        evidence["manifest"][field] = value
    path.write_text(json.dumps(evidence))
    with lib.transaction() as db:
        db.execute("UPDATE plans SET status='needs_reconciliation' WHERE id=?", (plan["id"],))
    reconciled = reconcile_plan(lib, plan["id"])
    assert reconciled["status"] == "needs_reconciliation"
    assert reconciled["total_usd"] is None


def test_sigint_after_real_subprocess_cannot_be_hidden_by_source_change(tmp_path, monkeypatch):
    import secondlook.provider as provider_module
    import secondlook.runner as runner_module
    from secondlook.provider import ClaudeProvider
    from test_provider import executable, success
    lib = setup_library(tmp_path)
    source = Path(lib.records()[0]["capsule"]["root"]) / "index.html"
    fake_cli = executable(tmp_path, "sys.stdin.read()\nprint(" + repr(json.dumps(success(0.2))) + ")")
    monkeypatch.setattr(runner_module, "ClaudeProvider", lambda model: ClaudeProvider(model, executable=fake_cli))
    monkeypatch.setattr(ClaudeProvider, "preflight", lambda self: "test-cli")
    original_write = provider_module.write_json
    def interrupt_after_parse(path, journal):
        if "raw" in journal:
            source.write_text(source.read_text() + "<!-- external change -->")
            raise KeyboardInterrupt()
        original_write(path, journal)
    monkeypatch.setattr(provider_module, "write_json", interrupt_after_parse)
    result = execute_plan(lib, make_plan(lib, "candidate", 1, mode="ordinary")["id"])
    assert result["status"] == "needs_reconciliation"
    assert result["total_usd"] is None and result["unknown"] is True
    assert result["tokens"] is None


def test_report_write_error_never_adds_a_second_summary(tmp_path):
    lib = setup_library(tmp_path, passing=True)
    plan = make_plan(lib, "candidate", 1)
    result = execute_plan(lib, plan["id"])
    report = Path(result["tasks"][0]["report"])
    report.unlink()
    report.mkdir()
    with lib.transaction() as db:
        db.execute("UPDATE plans SET status='needs_reconciliation' WHERE id=?", (plan["id"],))
    reconciled = reconcile_plan(lib, plan["id"])
    assert len(reconciled["tasks"]) == 1
    assert reconciled["status"] == "reconciled"
    assert reconciled["tasks"][0]["report_error"]
