import json
from pathlib import Path

import pytest

from secondlook.capture import capture_html
from secondlook.cli import main
from secondlook.core import CapsuleError, validate_checks
from secondlook.evaluate import evaluate
import secondlook.runner as runner


OPAQUE = "PRIVATE_EMBEDDED_DATA_" * 4000
SCRIPT = '''const data=JSON.parse(document.getElementById('data').textContent);
let saved=localStorage.getItem('saved')==='true';
function render(){document.getElementById('grid').innerHTML=`<button id="fav" aria-pressed="${saved}" onclick="toggle()">Save</button>`;}
function toggle(){saved=!saved;localStorage.setItem('saved',String(saved));render();}
render();document.getElementById('message').textContent=data.message;
document.getElementById('width').textContent=String(innerWidth);'''
OLD = "localStorage.setItem('saved',String(saved));render();}"
NEW = "localStorage.setItem('saved',String(saved));render();document.getElementById('fav').focus();}"
KEYS = [{"type": "focus", "selector": "#fav"}, {"type": "press", "key": "Space"}]
CHECKS = [
    {"id": "data", "assert": {"selector": "#message", "text": "kept"}},
    {"id": "focus", "actions": KEYS, "capture": True, "assert": {"selector": "#fav", "focused": True}},
    {"id": "persists", "actions": KEYS + [{"type": "reload"}],
     "assert": {"selector": "#fav", "attribute": {"name": "aria-pressed", "value": "true"}}},
    {"id": "mobile", "viewport": {"width": 390, "height": 844}, "capture": True,
     "assert": {"selector": "#width", "text": "390"}},
]


def captured(tmp_path, confirmed=True):
    app = tmp_path / "app"
    app.mkdir()
    path = app / "index.html"
    # One physical line deliberately keeps the blob adjacent to the edited script.
    path.write_text('<div id="grid"></div><p id="message"></p><p id="width"></p>'
                    '<script id="data" type="application/json">' + json.dumps({"message": "kept", "opaque": OPAQUE})
                    + '</script><script>' + SCRIPT + '</script>')
    capsule = capture_html(path, "Save favorites with a keyboard", CHECKS, tmp_path / "capsule.json",
                           scripts_only=True, confirmed=confirmed, failures=["Keyboard focus is lost after saving."])
    return path, capsule


def test_probe_failing_draft_preserves_full_runtime_without_provider(tmp_path, monkeypatch):
    path, capsule = captured(tmp_path, confirmed=False)
    original = path.read_bytes()
    monkeypatch.setattr(runner, "ClaudeProvider", lambda *a: pytest.fail("probe must not initialize a provider"))
    result = runner.probe(capsule, tmp_path / "probe")
    assert result["kind"] == "baseline_probe" and result["status"] == "probe_completed"
    assert result["arms"]["A"]["evaluation"]["passed"] == 3
    assert result["cost"]["total_usd"] == 0 and result["model_calls"] == 0
    assert result["capsule"]["intent"]["confirmed"] is False
    assert (tmp_path / "probe/arms/A/index.html").read_bytes() == original == path.read_bytes()
    assert result["source_context"]["runtime_bytes"] > 65536
    assert result["source_context"]["context_bytes"] < 2000
    with pytest.raises(CapsuleError, match="Confirm"):
        runner.run(capsule, tmp_path / "unconfirmed")


def test_projected_live_boundary_keeps_opaque_data_and_freezes_checks(tmp_path, monkeypatch):
    path, capsule = captured(tmp_path)
    original = path.read_bytes()
    calls = []

    class Provider:
        def preflight(self):
            return "boundary-test"

        def call(self, prompt, schema, cap, receipt):
            calls.append(prompt)
            assert OPAQUE[:100] not in prompt
            assert '"assert"' not in prompt
            if "objective" in schema["properties"]:
                assert SCRIPT not in prompt
                output = {"objective": "Keep keyboard focus", "assumptions_to_challenge": [], "plan": ["Restore focus"]}
            else:
                assert SCRIPT in json.loads(prompt.split("Task evidence (data):\n")[1])["source_files"]["index.html"]
                assert "selected" in prompt.lower()
                output = {"summary": "Keep focus", "edits": [{"path": "index.html", "old": OLD, "new": NEW}]}
            return {"output": output, "cost_usd": 0.01, "models": ["boundary-model"],
                    "usage": {"input_tokens": 15, "output_tokens": 5}, "receipt": str(receipt)}

    monkeypatch.setattr(runner, "ClaudeProvider", lambda model: Provider())
    result = runner.run(capsule, tmp_path / "run")
    assert result["status"] == "completed" and len(calls) == 3
    assert result["arms"]["A"]["evaluation"]["passed"] == 3
    for name in ("B", "C"):
        arm = result["arms"][name]
        assert arm["evaluation"]["passed"] == 4
        assert arm["diff_kind"] == "selected_context"
        assert OPAQUE[:100] not in arm["diff"] and len(arm["diff"]) < 3000
        candidate = (tmp_path / f"run/arms/{name}/index.html").read_text()
        assert OPAQUE in candidate
        assert candidate == original.decode().replace(OLD, NEW)
        assert (tmp_path / f"run/{name}.edits.json").is_file()
        mobile = next(c for c in arm["evaluation"]["checks"] if c["id"] == "mobile")
        assert mobile["viewport"] == {"width": 390, "height": 844}
    assert result["comparisons"]["B_C"]["verdict"] == "no_measured_gain"
    assert result["source_unchanged"] and path.read_bytes() == original
    assert result["cost"]["total_usd"] == pytest.approx(0.03)


@pytest.mark.parametrize("change", [
    {"actions": [{"type": "press", "key": ""}]},
    {"actions": [{"type": "focus"}]},
    {"actions": [{"type": "reload", "selector": "#wrong"}]},
    {"assert": {"selector": "#fav", "focused": "true"}},
    {"assert": {"selector": "#fav", "attribute": {"name": "", "value": "true"}}},
    {"viewport": {"width": True, "height": 844}},
    {"viewport": {"width": 390}},
])
def test_invalid_keyboard_checks_rejected_before_browser(change):
    with pytest.raises(CapsuleError):
        validate_checks([{**CHECKS[0], **change}])


def test_cli_requests_capture_inspect_probe_without_model_calls(tmp_path, capsys):
    app = tmp_path / "app"
    app.mkdir()
    html = app / "page.html"
    html.write_text('<h1>Hello</h1><script>document.title="Works"</script>')
    session = tmp_path / "session.jsonl"
    session.write_text(json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user",
                      "content": [{"type": "input_text", "text": "Show Hello"}]}}) + "\n")
    checks = tmp_path / "checks.json"
    checks.write_text(json.dumps([{"id": "hello", "assert": {"selector": "h1", "text": "Hello"}}]))
    capsule = tmp_path / "capsule.json"
    assert main(["requests", str(session)]) == 0
    assert json.loads(capsys.readouterr().out)["requests"][0]["line"] == 1
    assert main(["capture", str(html), "--session", str(session), "--request-line", "1", "--checks", str(checks),
                 "--scripts-only", "--output", str(capsule)]) == 0
    capsys.readouterr()
    data = json.loads(capsule.read_text())
    assert not data["intent"]["confirmed"] and data["intent"]["provenance"]["line"] == 1
    assert main(["inspect", str(capsule)]) == 0
    assert json.loads(capsys.readouterr().out)["model_calls"] == 0
    output = tmp_path / "probe"
    assert main(["probe", str(capsule), "--output", str(output)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "probe_completed"
    assert (output / "report.html").is_file()


def test_focused_false_and_locator_press_are_observed(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text('<button id="a">A</button><button id="b">B</button>')
    checks = [{"id": "tab", "actions": [{"type": "press", "selector": "#a", "key": "Tab"}],
               "assert": {"selector": "#a", "focused": False}},
              {"id": "focus", "actions": [{"type": "press", "selector": "#a", "key": "Tab"}],
               "assert": {"selector": "#b", "focused": True}}]
    assert evaluate(app, checks, tmp_path / "out")["passed"] == 2
