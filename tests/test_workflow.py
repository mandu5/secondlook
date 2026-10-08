import json
from pathlib import Path

import pytest

from secondlook.core import CapsuleError, fingerprint, load_capsule, source_bundle
from secondlook.evaluate import compare_results, evaluate
from secondlook.fixtures import create_demo
from secondlook.runner import build_prompt, run


def test_real_browser_reports_failure_then_pass_and_blocks_external_requests(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    source = '<h1>Hello</h1><script>fetch("https://example.com/leak").catch(()=>{});</script>'
    (app / "index.html").write_text(source)
    checks = [{"id": "title", "assert": {"selector": "h1", "text": "Better"}}]
    before = evaluate(app, checks, tmp_path / "a")
    assert before["status"] == "completed" and before["passed"] == 0
    assert "https://example.com/leak" in before["blocked_requests"]
    (app / "index.html").write_text(source.replace("Hello", "Better"))
    after = evaluate(app, checks, tmp_path / "b")
    assert after["passed"] == 1
    assert Path(after["screenshots"]["initial"]).is_file()
    assert compare_results(before, after)["verdict"] == "improved"


def result(passes, status="completed"):
    return {"status": status, "checks": [{"id": str(i), "passed": p} for i, p in enumerate(passes)]}


def test_regressions_override_new_passes_and_missing_evaluation_is_inconclusive():
    assert compare_results(result([True, False]), result([False, True]))["verdict"] == "regression"
    assert compare_results(result([False]), result([True]))["verdict"] == "improved"
    assert compare_results(result([True]), result([True]))["verdict"] == "no_measured_gain"
    assert compare_results(result([False]), result([True], "error"))["verdict"] == "inconclusive"
    assert compare_results(result([False, False]), result([True]))["verdict"] == "inconclusive"


def test_reframe_has_no_legacy_source_or_hidden_checks(capsule_file):
    capsule = load_capsule(capsule_file)
    bundle = {"index.html": "PRIVATE_LEGACY_IMPLEMENTATION"}
    prompt = build_prompt(capsule, bundle, "reframe")
    assert "PRIVATE_LEGACY_IMPLEMENTATION" not in prompt
    assert '"assert"' not in prompt
    assert capsule["intent"]["text"] in prompt
    assert "PRIVATE_LEGACY_IMPLEMENTATION" in build_prompt(capsule, bundle, "ordinary")


def test_offline_demo_preserves_source_and_frozen_checks(tmp_path):
    capsule_path = create_demo(tmp_path / "demo")
    original = capsule_path.read_bytes()
    bundle = source_bundle(load_capsule(capsule_path))
    output = tmp_path / "run"
    evidence = run(capsule_path, output, offline=True)
    assert evidence["kind"] == "offline_reference"
    assert evidence["arms"]["A"]["evaluation"]["passed"] < len(evidence["capsule"]["checks"])
    assert evidence["arms"]["R"]["evaluation"]["passed"] == len(evidence["capsule"]["checks"])
    assert evidence["comparisons"]["A_R"]["verdict"] == "improved"
    assert evidence["cost"]["total_usd"] == 0
    assert evidence["source_unchanged"] is True
    assert capsule_path.read_bytes() == original
    assert fingerprint(source_bundle(load_capsule(capsule_path))) == fingerprint(bundle)
    assert not (output / "arms" / "R" / "capsule.json").exists()
    assert json.loads((output / "capsule.frozen.json").read_text())["checks"] == evidence["capsule"]["checks"]


def test_passing_baseline_skips_model_calls(capsule_file, tmp_path):
    evidence = run(capsule_file, tmp_path / "run", model="does-not-exist")
    assert evidence["status"] == "skipped_baseline_passes"
    assert list(evidence["arms"]) == ["A"]
    assert evidence["cost"]["total_usd"] == 0


def test_output_must_be_new_and_outside_source(capsule_file):
    with pytest.raises(CapsuleError, match="source"):
        run(capsule_file, capsule_file.parent / "app" / "run")
    with pytest.raises(CapsuleError, match="empty|exists"):
        run(capsule_file, capsule_file.parent)


def test_invalid_selector_is_an_evaluation_error(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text("<h1>Hello</h1>")
    measured = evaluate(app, [{"id": "invalid", "assert": {"selector": "[", "text": "Hello"}}], tmp_path / "out")
    assert measured["status"] == "error"
    assert measured["checks"][0]["error_kind"] == "harness"


def test_unknown_decode_stops_further_dispatches(capsule_file, tmp_path, monkeypatch):
    import secondlook.runner as runner
    from secondlook.provider import ClaudeProvider
    source = capsule_file.parent / "app" / "index.html"
    source.write_text('<h1 id="title">Wrong</h1>')
    executable = tmp_path / "invalid-output"
    executable.write_text("#!/usr/bin/env python3\nimport sys\nsys.stdout.buffer.write(b'\\xff')\n")
    executable.chmod(0o755)
    provider = ClaudeProvider("test", executable=str(executable))
    monkeypatch.setattr(provider, "preflight", lambda: "test")
    monkeypatch.setattr(runner, "ClaudeProvider", lambda model: provider)
    evidence = run(capsule_file, tmp_path / "out")
    assert evidence["cost"]["unknown"] is True
    assert evidence["cost"]["total_usd"] is None
    assert len(list((tmp_path / "out" / "receipts").glob("*.json"))) == 1
    assert evidence["arms"]["C"]["status"] == "skipped_budget"


def test_overshoot_records_unequal_effective_caps_and_inconclusive_workflow(capsule_file, tmp_path, monkeypatch):
    import secondlook.runner as runner
    source = capsule_file.parent / "app" / "index.html"
    source.write_text('<h1 id="title">Wrong</h1>')
    calls = []

    class OvershootProvider:
        def preflight(self):
            return "fake-process-boundary-reviewed-separately"

        def call(self, prompt, schema, budget, receipt):
            calls.append(budget)
            payload = {"objective": "Hello", "assumptions_to_challenge": [], "plan": []} if "objective" in schema.get("properties", {}) else {
                "summary": "Fix title", "edits": [{"path": "index.html", "old": "Wrong", "new": "Hello"}]}
            return {"output": payload, "cost_usd": 1.2 if len(calls) == 1 else 0.1,
                    "usage": None, "models": ["exact-model"], "receipt": str(receipt)}

    monkeypatch.setattr(runner, "ClaudeProvider", lambda model: OvershootProvider())
    evidence = run(capsule_file, tmp_path / "out", budget=2.0)
    assert calls == pytest.approx([1.0, 0.24, 0.7])
    assert evidence["arms"]["C"]["budget_usd"] == pytest.approx(0.8)
    assert evidence["arms"]["B"]["tokens"]["total"] is None
    assert evidence["cost"]["total_usd"] == pytest.approx(1.4)
    assert evidence["comparisons"]["B_C"]["verdict"] == "inconclusive"
    assert "budget" in evidence["comparisons"]["B_C"]["reason"].lower()


def test_multiple_resolved_models_do_not_prove_same_model_comparison():
    from secondlook.runner import compare_workflows
    arm = {"models": ["model-one", "model-two"], "budget_usd": 1.0, "evaluation": result([True])}
    comparison = compare_workflows(arm, arm)
    assert comparison["verdict"] == "inconclusive"
    assert "model" in comparison["reason"].lower()
