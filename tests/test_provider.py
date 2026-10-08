import json
from pathlib import Path

import pytest

from secondlook.provider import Budget, ClaudeProvider, ProviderError


def executable(tmp_path, body):
    script = tmp_path / "fake-claude"
    script.write_text("#!/usr/bin/env python3\nimport json,sys,time\n" + body)
    script.chmod(0o755)
    return str(script)


def success(cost=0.03):
    return {"type": "result", "subtype": "success", "is_error": False,
            "structured_output": {"answer": "ok"}, "total_cost_usd": cost,
            "usage": {"input_tokens": 12, "output_tokens": 8, "cache_read_input_tokens": 20},
            "modelUsage": {"claude-test-exact": {"inputTokens": 12, "outputTokens": 8}}}


def test_provider_is_tool_free_and_records_real_identity(tmp_path):
    body = "\n".join([
        "args=sys.argv[1:]",
        "assert args[args.index('--tools')+1] == ''",
        "assert '--safe-mode' in args and '--restricted' in args",
        "assert '--strict-mcp-config' in args and '--no-session-persistence' in args",
        "assert '--max-budget-usd' in args",
        "assert sys.stdin.read() == 'original intent'",
        "print(" + repr(json.dumps(success())) + ")",
    ])
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, body))
    receipt = tmp_path / "receipt.json"
    result = provider.call("original intent", {"type": "object"}, 0.2, receipt)
    assert result["models"] == ["claude-test-exact"]
    assert result["cost_usd"] == 0.03
    assert result["output"] == {"answer": "ok"}
    stored = json.loads(receipt.read_text())
    assert stored["state"] == "completed"
    assert stored["raw"]["total_cost_usd"] == 0.03
    assert stored["prompt_sha256"] and stored["requested_model"] == "sonnet"
    assert (tmp_path / "receipt.prompt.txt").read_text() == "original intent"


def test_failed_call_still_accounts_for_known_spend(tmp_path):
    response = success(0.07)
    response.update(subtype="error_max_budget_usd", is_error=True)
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, f"print({json.dumps(response)!r})\nsys.exit(1)"))
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 0.05, tmp_path / "r.json")
    assert caught.value.cost_usd == 0.07
    budget = Budget(0.1)
    budget.record(caught.value.cost_usd)
    assert budget.remaining == pytest.approx(0.03)


@pytest.mark.parametrize("output", ["not json", json.dumps({"subtype": "success", "structured_output": {}}), json.dumps(success(float("nan")))])
def test_missing_or_invalid_cost_is_unknown_and_stops_budget(tmp_path, output):
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, f"print({output!r})"))
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 0.2, tmp_path / "r.json")
    assert caught.value.cost_usd is None
    budget = Budget(1.0)
    budget.record(None)
    assert budget.remaining == 0
    assert budget.unknown
    assert json.loads((tmp_path / "r.json").read_text())["state"] == "remote_outcome_unknown"


def test_timeout_records_unknown_and_never_retries(tmp_path):
    marker = tmp_path / "count"
    body = f"from pathlib import Path\nwith Path({str(marker)!r}).open('a') as f: f.write('once')\ntime.sleep(10)"
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, body), timeout=1)
    receipt = tmp_path / "r.json"
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 0.2, receipt)
    assert caught.value.cost_usd is None
    assert marker.read_text() == "once"
    assert json.loads(receipt.read_text())["state"] == "remote_outcome_unknown"
    with pytest.raises(ProviderError, match="already exists"):
        provider.call("p", {}, 0.2, receipt)


def test_missing_executable_is_known_zero_cost(tmp_path):
    provider = ClaudeProvider("sonnet", executable=str(tmp_path / "missing"))
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 0.2, tmp_path / "r.json")
    assert caught.value.cost_usd == 0


def test_budget_refuses_nan_and_never_has_negative_remaining():
    with pytest.raises(ValueError):
        Budget(float("nan"))
    budget = Budget(0.1)
    budget.record(0.15)
    assert budget.spent == 0.15 and budget.remaining == 0


def test_non_utf8_output_becomes_durable_unknown_cost(tmp_path):
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, "sys.stdout.buffer.write(b'\\xff')"))
    receipt = tmp_path / "r.json"
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 0.2, receipt)
    assert caught.value.cost_usd is None
    assert json.loads(receipt.read_text())["state"] == "remote_outcome_unknown"
    assert receipt.with_suffix(".stdout.bin").read_bytes() == b"\xff"


def test_bad_model_metadata_preserves_known_spend(tmp_path):
    response = success(0.7)
    response["modelUsage"] = None
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, f"print({json.dumps(response)!r})"))
    receipt = tmp_path / "r.json"
    with pytest.raises(ProviderError) as caught:
        provider.call("p", {}, 1.0, receipt)
    assert caught.value.cost_usd == 0.7
    assert json.loads(receipt.read_text())["cost_usd"] == 0.7


def test_absent_usage_is_explicitly_unavailable(tmp_path):
    response = success()
    response.pop("usage")
    provider = ClaudeProvider("sonnet", executable=executable(tmp_path, f"print({json.dumps(response)!r})"))
    result = provider.call("p", {}, 1.0, tmp_path / "r.json")
    assert result["usage"] is None
