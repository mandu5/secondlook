import json

import pytest
from playwright.sync_api import sync_playwright

from secondlook.cli import main
from secondlook.core import CapsuleError
from secondlook.sharing import share_result


def test_cli_prepare_assess_and_share_preserves_unknown_cost_and_escapes_labels(capsule_file, tmp_path, capsys):
    request = tmp_path / "request"
    assert main(["prepare", str(capsule_file), "--mode", "ordinary", "--output", str(request)]) == 0
    prepared = json.loads(capsys.readouterr().out)
    assert prepared["model_calls"] == 0 and prepared["request_id"]
    paths = []
    for index, text in enumerate(("Better", "Worse"), 1):
        path = tmp_path / f"response-{index}.json"
        path.write_text(json.dumps({"request_id": prepared["request_id"], "summary": "External <b>output</b>",
                                   "edits": [{"path": "index.html", "old": "Hello", "new": text}]}))
        paths.append(path)
    output = tmp_path / "out"
    malicious = '<script>window.SECONDLOOK_INJECTED=true</script>'
    assert main(["assess", str(request), "--response", str(paths[0]), "--label", malicious,
                 "--response", str(paths[1]), "--label", "PRIVATE_MODEL_LABEL", "--output", str(output)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["model_calls"] == 0 and summary["cost"]["total_usd"] is None
    report = (output / "report.html").read_text()
    assert "IMPORTED CANDIDATES" in report
    assert "owner-reported" in report and "unverified" in report
    assert "stop budget" not in report
    assert malicious not in report
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.goto((output / "report.html").as_uri())
            assert page.evaluate("window.SECONDLOOK_INJECTED === undefined")
            assert page.locator(".arm").count() == 3
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        finally:
            browser.close()
    shared = tmp_path / "shared"
    assert main(["share", str(output / "result.json"), "--output", str(shared)]) == 0
    exported = json.loads((shared / "summary.json").read_text())
    assert exported["cost"]["total_usd"] is None
    assert "owner-reported" in exported["cost"]["basis"]
    assert list(exported["arms"]) == ["A", "E1", "E2"]
    for path in (shared / "index.html", shared / "summary.json"):
        text = path.read_text()
        for secret in ("PRIVATE_MODEL_LABEL", "SECONDLOOK_INJECTED", str(tmp_path), '"old": "Hello"'):
            assert secret not in text


def test_cli_import_usage_file_is_read_as_unverified_metadata(capsule_file, tmp_path, capsys):
    from secondlook.handoff import prepare_request
    folder = tmp_path / "request"
    prepared = prepare_request(capsule_file, folder, mode="ordinary")
    response = tmp_path / "response.json"
    response.write_text(json.dumps({"request_id": prepared["request_id"], "summary": "same",
                                   "edits": [{"path": "index.html", "old": "Hello", "new": "Hello"}]}))
    usage = tmp_path / "usage.json"
    usage.write_text('[{"cost_usd":0,"input_tokens":10,"output_tokens":2}]')
    out = tmp_path / "out"
    assert main(["assess", str(folder), "--response", str(response), "--label", "owner label",
                 "--usage", str(usage), "--output", str(out)]) == 0
    result = json.loads((out / "result.json").read_text())
    assert result["arms"]["E1"]["evaluation_reused_from"] == "A"
    assert result["arms"]["E1"]["tokens"]["total"] == 12
    assert "Reused" in (out / "report.html").read_text()
    shared = tmp_path / "shared"
    share_result(out / "result.json", shared)
    public = json.loads((shared / "summary.json").read_text())
    assert public["arms"]["E1"]["evaluation_reused_from"] == "A"
    assert public["arms"]["E1"]["models"] == []


def test_imported_arms_are_not_accepted_as_verified_live_results(tmp_path):
    result = {"kind": "live_model", "status": "completed", "capsule": {"checks": [{"id": "x"}]},
              "cost": {}, "arms": {"A": {}, "E1": {}}}
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    with pytest.raises(CapsuleError, match="workflow"):
        share_result(path, tmp_path / "out")
