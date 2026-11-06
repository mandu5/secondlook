"""Refresh homepage check data from the bundled capsule and recorded offline report.

The public site itself is static and is deployed directly from site/.
This command never evaluates an app or calls a model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check that the committed snapshot is current")
    args = parser.parse_args()
    source = "src/secondlook/demo/capsule.json"
    results = "site/demo/summary.json"
    capsule = json.loads((ROOT / source).read_text())
    report = json.loads((ROOT / results).read_text())
    checks = []
    original = report["arms"]["A"]["evaluation"]["checks"]
    reference = report["arms"]["R"]["evaluation"]["checks"]
    if not len(capsule["checks"]) == len(original) == len(reference) == 8:
        raise ValueError("The homepage is an eight-check composition; review its markup before changing the fixture.")
    for index, (check, before, after) in enumerate(zip(capsule["checks"], original, reference)):
        if before["id"] != after["id"] or before["id"] != f"check-{index + 1}":
            raise ValueError("The saved report no longer matches the capsule's exported check order.")
        checks.append({**check, "originalPassed": before["passed"], "referencePassed": after["passed"], "reportId": before["id"]})
    output = json.dumps({"source": source, "results": results, "kind": "offline_reference", "checks": checks}, indent=2) + "\n"
    target = ROOT / "site/assets/demo-checks.json"
    if args.check:
        if target.read_text() != output:
            raise SystemExit("Homepage check data is stale. Run python3 scripts/build_site.py.")
        print("Homepage check data matches the bundled capsule and recorded report.")
    else:
        target.write_text(output)
        print(f"Updated {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
