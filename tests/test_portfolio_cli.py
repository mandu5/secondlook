import json

from secondlook.board import write_board
from secondlook.cli import main
from secondlook.library import Library
from secondlook.portfolio import make_plan
from secondlook.portfolio_cli import watch_catalog
from secondlook.portfolio_demo import portfolio_demo
from test_library import catalog, problem, profile
from test_portfolio import setup_library


def test_cli_harvest_candidate_queue_and_board_preserve_problem_definition(tmp_path, capsys):
    lib_path = tmp_path / "library"
    record = tmp_path / "problem.json"
    record.write_text(json.dumps(problem()))
    assert main(["harvest", str(record), "--problem", "--library", str(lib_path)]) == 0
    assert json.loads(capsys.readouterr().out)["model_calls"] == 0
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(profile()))
    assert main(["candidate", str(candidate), "--library", str(lib_path)]) == 0
    capsys.readouterr()
    assert main(["queue", "candidate", "--library", str(lib_path), "--budget-usd", "1"]) == 0
    queued = json.loads(capsys.readouterr().out)
    assert queued["decisions"][0]["reason"] == "no_execution_adapter"
    assert main(["board", "--library", str(lib_path)]) == 0
    assert (lib_path / "board.html").is_file()


def test_catalog_changes_queue_only_explicitly_mapped_candidates(tmp_path):
    lib = setup_library(tmp_path)
    data = profile("mapped")
    data.update(catalog_id="vendor/new", catalog_source="fixture:feed")
    lib.register_candidate(data)
    first = watch_catalog(lib, catalog("vendor/old"), "fixture:feed", budget=1, queue=True)
    assert first["plans"] == []
    observed = watch_catalog(lib, catalog("vendor/old", "vendor/new"), "fixture:feed", budget=1, queue=True)
    assert len(observed["plans"]) == 1
    assert observed["plans"][0]["candidate"]["id"] == "mapped"
    assert observed["plans"][0]["trigger"]["quality_improvement"] == "not established"
    assert watch_catalog(lib, catalog("vendor/new"), "fixture:feed", budget=1, queue=True)["plans"] == []


def test_board_escapes_intent_and_has_no_remote_assets_or_fabricated_metrics(tmp_path):
    lib = Library(tmp_path / "library")
    record = problem()
    record["title"] = '<img src=x onerror="alert(1)">'
    lib.harvest_problem(record)
    page = write_board(lib).read_text()
    assert '<img src=x' not in page
    assert '&lt;img src=x' in page
    assert "No measured revisits yet" in page
    assert '<script src=' not in page and '<link href="http' not in page
    assert "Old assistant hypothesis" in page


def test_portfolio_demo_compares_real_browser_artifacts_without_model_calls(tmp_path):
    result = portfolio_demo(tmp_path / "demo")
    assert result["simulation"] is True
    assert result["campaign"]["model_calls"] == 0
    assert result["campaign"]["total_usd"] == 0
    task = result["campaign"]["tasks"][0]
    assert task["arms"]["A"]["passed"] == 3 and task["arms"]["R"]["passed"] == 8
    assert result["repeat"]["selected"] == []
    reasons = {d["task_id"]: d["reason"] for d in result["repeat"]["decisions"]}
    assert reasons["feedback-board"] == "already_attempted"
    assert reasons["focus-timer"] == "budget"
    assert reasons["research-note"] == "no_execution_adapter"
    assert Library(tmp_path / "demo" / "library").records()[0]["id"] == "feedback-board"
