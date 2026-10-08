"""Hand-authored import demonstration. Never calls a model."""

import argparse
from importlib.resources import files
import json
from pathlib import Path

from secondlook.assessment import assess_responses
from secondlook.core import write_json
from secondlook.fixtures import create_demo
from secondlook.handoff import prepare_request
from secondlook.report import write_report
from secondlook.sharing import share_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    root = parser.parse_args().output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    capsule = create_demo(root / "source")
    manifest = prepare_request(capsule, root / "request", mode="ordinary")
    reference = json.loads(files("secondlook").joinpath("demo/reference.json").read_text())
    good = {"request_id": manifest["request_id"], **reference}
    bad = {"request_id": manifest["request_id"],
           "summary": "Hand-authored regression: change a feedback priority; no model generated this.",
           "edits": [{"path": "index.html",
                      "old": "id: 'F-106', title: 'CSV export includes hidden items', priority: 'P1'",
                      "new": "id: 'F-106', title: 'CSV export includes hidden items', priority: 'P3'"}]}
    write_json(root / "reference.json", good)
    write_json(root / "regression.json", bad)
    result = assess_responses(root / "request", [root / "reference.json", root / "regression.json"],
                              ["Hand-authored reference (no model)", "Hand-authored regression (no model)"], root / "comparison",
                              usage=[{"cost_usd": 0, "input_tokens": 0, "output_tokens": 0}] * 2)
    write_report(result, root / "comparison")
    assert [a["evaluation"]["passed"] for a in result["arms"].values()] == [3, 8, 2]
    assert result["model_calls"] == 0 and result["comparisons"]["A_E2"]["verdict"] == "regression"
    shared = share_result(root / "comparison" / "result.json", root / "shared",
                          title="Hand-authored import demo · no model performance claim",
                          include_intent=True, include_screenshots=True)
    print(json.dumps({"report": str(shared), "scores": {k: a.get("evaluation", {}).get("passed") for k, a in result["arms"].items()},
                      "comparisons": result["comparisons"], "model_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
