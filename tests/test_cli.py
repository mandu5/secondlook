import json
import os
from pathlib import Path
import subprocess
import sys

from secondlook.report import write_report


def cli(*args):
    return subprocess.run([sys.executable, "-m", "secondlook", *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}, timeout=90)


def test_cli_offline_report_is_explicit_and_self_contained(tmp_path):
    output = tmp_path / "demo"
    proc = cli("demo", "--offline", "--output", output)
    assert proc.returncode == 0, proc.stderr
    result = json.loads((output / "result.json").read_text())
    assert result["kind"] == "offline_reference"
    html = (output / "report.html").read_text()
    assert "Hand-authored reference" in html and "No model was called" in html
    assert "data:image/png;base64," in html
    assert result["arms"]["R"]["evaluation"]["passed"] == 8
    assert (output.parent / "demo-input" / "capsule.json").exists()


def test_report_escapes_arbitrary_model_and_user_text(tmp_path):
    payload = '<script>window.EVIL=1</script><img src=x onerror=alert(1)>'
    evidence = {"status": "inconclusive", "kind": "live_model", "created_at": "now",
                "capsule": {"title": payload, "checks": [], "intent": {"text": payload}},
                "arms": {"C": {"label": payload, "status": "failed", "error": payload, "summary": payload, "diff": payload}},
                "comparisons": {}, "cost": {"total_usd": None, "known_spend_usd": 0, "limit_usd": 1},
                "manifest": {}, "fingerprint": "abc"}
    path = write_report(evidence, tmp_path)
    html = path.read_text()
    assert payload not in html
    assert "&lt;script&gt;" in html
    assert "Unknown" in html


def test_live_report_discloses_synthetic_baseline_provenance(tmp_path):
    evidence = {"status": "completed", "kind": "live_model", "capsule": {
        "title": "Live example", "checks": [], "intent": {"text": "Try a repair"},
        "baseline": {"provenance": "Deliberately flawed synthetic fixture; not produced by a historical model"}},
        "arms": {}, "comparisons": {}, "cost": {}, "manifest": {}}
    html = write_report(evidence, tmp_path).read_text()
    assert "Deliberately flawed synthetic fixture; not produced by a historical model" in html


def test_unknown_tokens_do_not_render_as_zero(tmp_path):
    evidence = {"status": "inconclusive", "kind": "live_model", "capsule": {"checks": []},
                "arms": {"B": {"status": "failed", "tokens": {"total": None, "known_total": 0}}},
                "comparisons": {}, "cost": {}, "manifest": {}}
    html = write_report(evidence, tmp_path).read_text()
    assert "unreported" in html
    assert "<strong>Unknown</strong>" in html


def test_invalid_budget_and_replay_are_nonzero_without_model_calls(tmp_path):
    proc = cli("demo", "--offline", "--budget-usd", "nan", "--output", tmp_path / "nan")
    assert proc.returncode == 2
    assert "finite positive" in proc.stderr
    output = tmp_path / "exists"
    output.mkdir()
    (output / "keep.txt").write_text("keep")
    proc = cli("demo", "--offline", "--output", output)
    assert proc.returncode == 2
    assert (output / "keep.txt").read_text() == "keep"


def test_init_records_intent_as_draft_until_reviewed(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text("<h1>Hello</h1>")
    capsule = tmp_path / "capsule.json"
    proc = cli("init", app, "--intent", "Show a greeting", "--files", "index.html", "--output", capsule)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(capsule.read_text())
    assert data["intent"]["text"] == "Show a greeting"
    assert data["intent"]["confirmed"] is False
    assert data["baseline"]["model"] == "unknown"
    proc = cli("plan", capsule, "--capability", "coding", "--budget-usd", "2")
    assert proc.returncode == 0 and "selected" in proc.stdout


def test_report_shows_context_bytes_without_claiming_token_savings(tmp_path):
    result = {"status": "completed", "kind": "live_model", "capsule": {"checks": [],
              "intent": {"text": "Preserve selection", "source": "Original user request", "confirmed": True,
                         "provenance": {"line": 23, "text_sha256": "abc"}}},
              "arms": {"B": {"status": "completed", "diff": "+ focus()", "diff_kind": "selected_context",
                              "diff_note": "Selected-code display diff, not a patch for the full artifact."}},
              "comparisons": {}, "cost": {}, "manifest": {},
              "source_context": {"runtime_bytes": 120410551, "context_bytes": 18000,
                                 "excluded_bytes": 120392551, "files": {}}}
    html = write_report(result, tmp_path).read_text()
    assert "120,410,551" in html and "18,000" in html
    assert "not measured token savings" in html
    assert "Original user request" in html and "text_sha256" in html
    assert "not a patch for the full artifact" in html


def test_probe_report_is_not_labeled_live_or_inconclusive_for_behavior_failure(tmp_path):
    result = {"status": "probe_completed", "kind": "baseline_probe", "capsule": {"checks": []},
              "arms": {"A": {"status": "completed", "evaluation": {"passed": 0, "total": 1},
                             "cost_usd": 0, "tokens": {"total": 0}}}, "comparisons": {}, "cost": {"total_usd": 0}, "manifest": {}}
    html = write_report(result, tmp_path).read_text()
    assert "BASELINE PROBE" in html and "No model was called" in html
    assert "Inconclusive run" not in html and "LIVE MODEL EXPERIMENT" not in html
    assert "Baseline checked" in html
    assert "Same viewport for each corresponding check" in html
