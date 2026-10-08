import json

from secondlook.cli import parser
from secondlook.core import write_json
from secondlook.evaluate import evaluate
from secondlook.fixtures import create_demo
from secondlook.library import Library
from secondlook.portfolio import execute_plan, make_plan, reconcile_plan
from secondlook.report import write_report
from test_library import profile
from test_rebuild import rebuild_capsule


def test_new_modes_are_available_for_direct_and_portfolio_cli():
    assert parser().parse_args(["run", "capsule.json", "--mode", "rebuild"]).mode == "rebuild"
    assert parser().parse_args(["queue", "candidate", "--mode", "compare-three"]).mode == "compare-three"


def test_rebuild_queue_explains_missing_contract_without_reserving_budget(rebuild_capsule, tmp_path):
    lib = Library(tmp_path / "library")
    lib.harvest_capsule(rebuild_capsule)
    other = create_demo(tmp_path / "ordinary-only")
    lib.harvest_capsule(other)
    lib.register_candidate(profile())
    plan = make_plan(lib, "candidate", 2, mode="compare-three")
    rows = {row["task_id"]: row for row in plan["decisions"]}
    assert rows["hello"]["reason"] == "selected"
    assert rows[json.loads(other.read_text())["id"]]["reason"] == "needs_rebuild_contract"
    assert plan["allocated_usd"] == .5


def test_three_way_negative_control_spends_zero_and_reconciles_without_replay(rebuild_capsule, tmp_path):
    data = json.loads(rebuild_capsule.read_text())
    source = rebuild_capsule.parent / "app" / "index.html"
    source.write_text(source.read_text().replace("Wrong", "Hello"))
    lib = Library(tmp_path / "library")
    lib.harvest_capsule(rebuild_capsule)
    lib.register_candidate(profile())
    plan = make_plan(lib, "candidate", 1, mode="compare-three")
    result = execute_plan(lib, plan["id"])
    assert result["status"] == "completed"
    assert result["total_usd"] == result["model_calls"] == 0
    assert result["tasks"][0]["status"] == "skipped_baseline_passes"
    assert result["tasks"][0]["arms"]["A"]["categories"]["preservation"]["passed"] == 1
    assert reconcile_plan(lib, plan["id"])["total_usd"] == 0
    repeat = make_plan(lib, "candidate", 1, mode="compare-three")
    assert not repeat["selected"] and repeat["decisions"][0]["reason"] == "already_attempted"
    assert data["intent"]["confirmed"] is True


def test_category_scores_use_expected_checks_and_preserve_basis(rebuild_capsule, tmp_path):
    data = json.loads(rebuild_capsule.read_text())
    result = evaluate(rebuild_capsule.parent / "app", data["checks"], tmp_path / "evaluation")
    assert result["categories"]["intent"] == {"passed": 0, "failed": 1, "unmeasured": 0, "total": 1}
    assert result["categories"]["preservation"] == {"passed": 1, "failed": 0, "unmeasured": 0, "total": 1}
    assert result["checks"][1]["basis"] == data["checks"][1]["basis"]


def test_report_does_not_hide_rebuild_regression_behind_good_patch(tmp_path):
    checks = [{"id": "intent", "category": "intent", "basis": "Documented purpose"},
              {"id": "keep", "category": "preservation", "basis": "Documented existing feature"}]
    def arm(outcomes):
        return {"label": "candidate", "evaluation": {"status": "completed", "passed": sum(outcomes), "total": 2,
                "checks": [{"id": c["id"], "passed": value} for c, value in zip(checks, outcomes)]},
                "tokens": {"total": 0}, "cost_usd": 0}
    result = {"status": "completed", "capsule": {"checks": checks},
              "arms": {"A": arm([False, True]), "B": arm([True, True]), "C": arm([True, True]), "D": arm([True, False])},
              "comparisons": {"A_C": {"verdict": "improved", "improvements": ["intent"], "regressions": []},
                              "A_D": {"verdict": "regression", "improvements": ["intent"], "regressions": ["keep"]},
                              "C_D": {"verdict": "regression", "improvements": [], "regressions": ["keep"]}}}
    html = write_report(result, tmp_path).read_text()
    assert "Regression detected in at least one workflow" in html
    assert 'aria-label="Pairwise comparisons"' in html
    assert "A → D" in html and "C → D" in html
    assert "Preservation: 0/1" in html
    assert "Documented existing feature" in html


def test_rebuild_only_report_identifies_its_measured_candidate(tmp_path):
    result = {"status": "completed", "capsule": {"checks": []}, "arms": {"A": {}, "D": {}},
              "comparisons": {"A_D": {"verdict": "improved", "improvements": ["x"], "regressions": []}}}
    html = write_report(result, tmp_path).read_text()
    assert "Measured improvement" in html
    assert "No candidate measured" not in html
