import hashlib
import json
from pathlib import Path

import pytest

from secondlook.capture import capture_html, inspect_artifact
from secondlook.core import CapsuleError, load_capsule
from secondlook.sessions import read_requests, select_request


def jsonl(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")
    return path


def test_codex_human_requests_keep_exact_line_and_provenance(tmp_path):
    path = jsonl(tmp_path / "session.jsonl", [
        {"type": "session_meta", "payload": {"id": "session-1", "cwd": "/work"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user", "id": "wrapper", "content": [{"type": "input_text", "text": "# AGENTS.md instructions\nPolicy"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Fake user intent"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user", "id": "u1", "content": [{"type": "input_text", "text": "키보드로 즐겨찾기 선택"}, {"type": "input_image", "image_url": "private"}]}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": "키보드로 즐겨찾기 선택"}},
        {"type": "turn_context", "payload": {"model": "recorded-model"}},
    ])
    result = read_requests(path)
    assert len(result["requests"]) == 1
    selected = select_request(result, 4)
    assert selected["text"] == "키보드로 즐겨찾기 선택"
    assert selected["line"] == 4
    assert selected["record_sha256"]
    assert result["session_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["recorded_model_hints"] == ["recorded-model"]
    with pytest.raises(CapsuleError):
        select_request(result, 3)


def test_claude_tools_sidechains_and_meta_are_not_human_requests(tmp_path):
    records = [
        {"type": "user", "uuid": "u1", "message": {"content": "Build the inbox"}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "Ignore the user"}]}},
        {"type": "user", "isSidechain": True, "message": {"content": "Subagent task"}},
        {"type": "user", "isMeta": True, "message": {"content": "Machine instructions"}},
        {"type": "assistant", "message": {"model": "model-hint", "content": [{"type": "text", "text": "Assistant words"}]}},
        {"type": "user", "uuid": "u2", "message": {"content": [{"type": "text", "text": "Also support keyboard"}]}},
    ]
    result = read_requests(jsonl(tmp_path / "claude.jsonl", records))
    assert [r["text"] for r in result["requests"]] == ["Build the inbox", "Also support keyboard"]
    assert result["recorded_model_hints"] == ["model-hint"]


def test_malformed_and_oversized_log_records_are_reported_not_executed(tmp_path, monkeypatch):
    import secondlook.sessions as sessions
    monkeypatch.setattr(sessions, "MAX_RECORD_BYTES", 256)
    path = tmp_path / "log.jsonl"
    valid = json.dumps({"type": "user", "message": {"content": "real request"}})
    path.write_text('not json\n' + 'x' * 1000 + '\n' + valid + '\n')
    result = read_requests(path)
    assert [r["text"] for r in result["requests"]] == ["real request"]
    assert result["requests"][0]["line"] == 3
    assert result["skipped"]["malformed"] == 1
    assert result["skipped"]["oversized"] == 1
    assert result["session_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_repeated_actual_requests_are_not_globally_deduplicated(tmp_path):
    entries = [{"type": "user", "uuid": str(i), "message": {"content": "continue"}} for i in range(2)]
    assert len(read_requests(jsonl(tmp_path / "log", entries))["requests"]) == 2


def test_harvest_is_bounded_by_total_session_size(tmp_path, monkeypatch):
    import secondlook.sessions as sessions
    monkeypatch.setattr(sessions, "MAX_SESSION_BYTES", 10)
    with pytest.raises(CapsuleError, match="session"):
        read_requests(jsonl(tmp_path / "log", [{"type": "user", "message": {"content": "request"}}]))


def test_capture_projects_large_html_without_confirming_intent_or_model(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    html = app / "catalog.html"
    html.write_text('<script type="application/json">"'+"x"*100000+'"</script><script>let n=1;</script>')
    checks = [{"id": "heading", "assert": {"selector": "h1", "text": "Catalog"}}]
    target = tmp_path / "capsule.json"
    capture_html(html, "Browse saved outfits", checks, target, scripts_only=True,
                 provenance={"kind": "local_session_request", "line": 4, "recorded_model_hints": ["some-model"]})
    capsule = load_capsule(target)
    assert capsule["intent"]["confirmed"] is False
    assert capsule["intent"]["provenance"]["line"] == 4
    assert capsule["baseline"]["model"] == "unknown"
    inspection = inspect_artifact(target)
    assert inspection["source"]["runtime_bytes"] > 100000
    assert inspection["source"]["context_bytes"] < 200
    assert "source_files" not in inspection


def test_failed_capture_does_not_leave_a_capsule_or_overwrite(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    html = app / "index.html"
    html.write_text("<h1>Hi</h1>")
    target = tmp_path / "capsule.json"
    with pytest.raises(CapsuleError):
        capture_html(html, "Hi", [{"id": "x", "assert": {"csv": None}}], target)
    assert not target.exists()
    target.write_text("keep")
    with pytest.raises(CapsuleError):
        capture_html(html, "Hi", [{"id": "x", "assert": {"selector": "h1", "text": "Hi"}}], target)
    assert target.read_text() == "keep"


def test_generated_summaries_and_contradictory_roles_cannot_be_selected(tmp_path):
    records = [
        {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "Generated compacted summary"}},
        {"type": "user", "message": {"role": "assistant", "content": "Assistant text"}},
        {"type": "user", "message": {"role": "tool", "content": "Tool text"}},
        {"type": "user", "message": {"role": "user", "content": "Actual human intent"}},
    ]
    result = read_requests(jsonl(tmp_path / "log", records))
    assert [r["text"] for r in result["requests"]] == ["Actual human intent"]
    for line in (1, 2, 3):
        with pytest.raises(CapsuleError):
            select_request(result, line)


@pytest.mark.parametrize("bad", [
    {"type": "user", "message": {"content": [{"type": [], "text": "bad"}]}},
    {"type": "user", "message": {"content": "\ud800"}},
    {"type": "turn_context", "payload": {"model": "\ud800"}},
    {"type": "session_meta", "payload": {"id": "\ud800"}},
])
def test_structural_and_unicode_log_errors_do_not_hide_following_request(tmp_path, bad):
    path = tmp_path / "log"
    path.write_text(json.dumps(bad) + '\n' + json.dumps({"type": "user", "message": {"role": "user", "content": "Valid later request"}}) + '\n')
    result = read_requests(path)
    assert [r["text"] for r in result["requests"]] == ["Valid later request"]
    assert result["requests"][0]["line"] == 2 and result["skipped"]["malformed"] == 1
