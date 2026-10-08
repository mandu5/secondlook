# Contributing

Start with a [minimal reproduction](https://github.com/mandu5/secondlook/issues/new/choose)
or a small pull request. The first execution adapter is intentionally limited to
trusted static apps. Read [the protocol](docs/clean-slate.md) before changing evaluation.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m playwright install chromium
python -m pytest -q
```

The suite makes zero paid model calls. Tests that touch Chromium need its local
installation. Add meaningful regression coverage for behavior changes, especially
cost uncertainty, duplicate attempts, immutable inputs and evaluation errors.
Keep requirements independent of candidate generation. Never replace missing
cost with zero or retry an unknown dispatch automatically.

Useful contributions: independently authored small failing apps, better onboarding,
adapter proposals with real isolation/evaluation, and evidence of adoption or
rejection. Include failures and unchanged outcomes. Do not submit personal data,
private prompts or paid-model receipts. Default `share` exports are a starting
point for public issue reports; inspect any opted-in text or screenshots.

Open a design issue before adding another provider or general code execution.
Describe the data boundary, receipt/accounting semantics and independent success
criteria. A new framework, dashboard or dependency needs a concrete benefit.
Human prose and trivial refactors do not need implementation-mirroring tests.

Be respectful, focus feedback on the work, and avoid harassment or personal attacks.
All contributions are distributed under the repository's MIT license.
