import json
from pathlib import Path

import pytest

from secondlook.core import CapsuleError
from secondlook.handoff import prepare_request


@pytest.fixture
def prepared(capsule_file, tmp_path):
    data = json.loads(capsule_file.read_text())
    data["checks"] = [
        {"id": "title", "category": "intent", "basis": "Owner", "assert": {"selector": "h1", "text": "Hello"}},
        {"id": "keep", "category": "preservation", "basis": "Owner", "assert": {"selector": "footer", "text": "Saved"}},
    ]
    capsule_file.write_text(json.dumps(data))
    (capsule_file.parent / "app" / "index.html").write_text('<h1>Wrong</h1><footer>Saved</footer>')
    folder = tmp_path / "request"
    manifest = prepare_request(capsule_file, folder, mode="ordinary")
    return folder, manifest["request_id"]


def response(folder, request_id, name, edits):
    path = folder.parent / name
    path.write_text(json.dumps({"request_id": request_id, "summary": "Candidate", "edits": edits}))
    return path


def test_import_compares_two_candidates_with_real_browser_and_unknown_cost(prepared, tmp_path):
    from secondlook.assessment import assess_responses
    folder, request_id = prepared
    original = (folder / "baseline" / "index.html").read_bytes()
    better = response(folder, request_id, "better.json", [{"path": "index.html", "old": "Wrong", "new": "Hello"}])
    worse = response(folder, request_id, "worse.json", [{"path": "index.html", "old": "Saved", "new": "Lost"}])
    result = assess_responses(folder, [better, worse], ["Chat A", "Local B"], tmp_path / "assessed")
    assert [a["evaluation"]["passed"] for a in result["arms"].values()] == [1, 2, 0]
    assert result["comparisons"]["A_E1"]["verdict"] == "improved"
    assert result["comparisons"]["A_E2"]["verdict"] == "regression"
    assert result["comparisons"]["E1_E2"]["verdict"] == "regression"
    assert result["kind"] == "imported_candidates" and result["model_calls"] == 0
    assert result["cost"]["total_usd"] is None
    assert result["arms"]["E1"]["tokens"]["total"] is None
    assert result["arms"]["E1"]["models"] == []
    assert result["arms"]["E1"]["declared_model"] == "Chat A"
    assert (folder / "baseline" / "index.html").read_bytes() == original
    assert (tmp_path / "assessed" / "result.json").is_file()


def test_wrong_response_or_metadata_rejected_before_output(prepared, tmp_path):
    from secondlook.assessment import assess_responses
    folder, request_id = prepared
    path = response(folder, "wrong", "response.json", [])
    with pytest.raises(CapsuleError, match="request"):
        assess_responses(folder, [path], ["A"], tmp_path / "out")
    assert not (tmp_path / "out").exists()
    path = response(folder, request_id, "response.json", [{"path": "index.html", "old": "Wrong", "new": "Hello"}])
    for usage in ([{"cost_usd": float("nan")}], [{"input_tokens": True}], [{"output_tokens": -1}], [{"cost_usd": 1, "verified": True}], []):
        with pytest.raises(CapsuleError):
            assess_responses(folder, [path], ["A"], tmp_path / "out", usage=usage)
        assert not (tmp_path / "out").exists()
    with pytest.raises(CapsuleError, match="label"):
        assess_responses(folder, [path], [], tmp_path / "out")
    with pytest.raises(CapsuleError, match="same|duplicate"):
        assess_responses(folder, [path, path], ["A", "B"], tmp_path / "out")


def test_identical_content_reuses_evidence_and_partial_usage_stays_unknown(prepared, tmp_path):
    from secondlook.assessment import assess_responses
    folder, request_id = prepared
    edits = [{"path": "index.html", "old": "Wrong", "new": "Hello"}]
    a = response(folder, request_id, "a.json", edits)
    b = response(folder, request_id, "b.json", edits)
    result = assess_responses(folder, [a, b], ["A", "B"], tmp_path / "out",
                              usage=[{"cost_usd": 0, "input_tokens": 123}, {"input_tokens": 20, "output_tokens": 4}])
    assert result["arms"]["E2"]["evaluation_reused_from"] == "E1"
    assert not (tmp_path / "out" / "evidence" / "E2").exists()
    assert result["arms"]["E1"]["tokens"]["total"] is None
    assert result["arms"]["E2"]["tokens"]["total"] == 24
    assert result["cost"]["total_usd"] is None
    assert result["cost"]["known_spend_usd"] == 0
    assert result["comparisons"]["E1_E2"]["verdict"] == "no_measured_gain"


def test_invalid_edit_keeps_failed_candidate_and_valid_candidate(prepared, tmp_path):
    from secondlook.assessment import assess_responses
    folder, request_id = prepared
    invalid = response(folder, request_id, "bad.json", [{"path": "../secret.txt", "old": "Wrong", "new": "Hello"}])
    valid = response(folder, request_id, "good.json", [{"path": "index.html", "old": "Wrong", "new": "Hello"}])
    result = assess_responses(folder, [invalid, valid], ["Bad", "Good"], tmp_path / "out",
                              usage=[{"cost_usd": .1}, {"cost_usd": .2}])
    assert result["status"] == "inconclusive"
    assert result["arms"]["E1"]["status"] == "failed"
    assert result["comparisons"]["A_E1"]["verdict"] == "inconclusive"
    assert result["comparisons"]["A_E2"]["verdict"] == "improved"
    assert result["cost"]["total_usd"] == pytest.approx(.3)
    assert not (tmp_path / "out" / "arms" / "secret.txt").exists()


def test_rebuild_preserves_readonly_inputs_and_rejects_attempt_to_change_them(capsule_file, tmp_path):
    from secondlook.assessment import assess_responses
    from test_handoff import rebuild_capsule
    rebuild_capsule(capsule_file)
    data = json.loads(capsule_file.read_text())
    data["files"].append("facts.json")
    data["readonly_files"] = ["facts.json"]
    capsule_file.write_text(json.dumps(data))
    (capsule_file.parent / "app" / "facts.json").write_text('{"fact":42}')
    folder = tmp_path / "request"
    manifest = prepare_request(capsule_file, folder)
    payload = {"request_id": manifest["request_id"], "summary": "Rebuild", "files": [
        {"path": "index.html", "content": '<h1>Hello</h1><footer>Saved</footer>'},
    ]}
    good = tmp_path / "good.json"
    good.write_text('```json\n' + json.dumps(payload) + '\n```')
    payload["files"].append({"path": "facts.json", "content": '{"fact":0}'})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload))
    result = assess_responses(folder, [good, bad], ["Good", "Bad"], tmp_path / "out")
    assert result["arms"]["E1"]["evaluation"]["passed"] == 2
    assert result["arms"]["E2"]["status"] == "failed"
    assert (tmp_path / "out" / "arms" / "E1" / "facts.json").read_text() == '{"fact":42}'


def test_import_refuses_unexpected_response_fields_and_too_many_candidates(prepared, tmp_path):
    from secondlook.assessment import assess_responses
    folder, request_id = prepared
    path = response(folder, request_id, "response.json", [])
    data = json.loads(path.read_text())
    data["checks"] = []
    path.write_text(json.dumps(data))
    with pytest.raises(CapsuleError):
        assess_responses(folder, [path], ["A"], tmp_path / "out")
    with pytest.raises(CapsuleError, match="1|4|four"):
        assess_responses(folder, [path] * 5, ["A"] * 5, tmp_path / "out")
