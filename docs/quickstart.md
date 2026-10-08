# From installation to your first comparison

Python 3.11+ on macOS/Linux. Start with the installation commands in the
[README](../README.md#try-it-with-zero-model-calls). Wheels are distributed through
GitHub Releases; this project is not on PyPI. No account is needed for the offline
demo, probe, library operations or export. Browser installation needs internet.

`secondlook doctor` launches Chromium locally. Add `--provider` to check that
Claude Code supports the required flags; it does not verify login or model access.
Install/authenticate Claude Code using its [official instructions](https://code.claude.com/docs/en/quickstart)
before a live run. The adapter checks `--restricted`, `--safe-mode`,
`--json-schema`, and `--max-budget-usd`; older installations may need an update.

## Use your own static app

Choose a trusted static app that can run offline, without a build or backend.
Keep the output capsule outside the source folder. Select files explicitly.

```bash
secondlook init ./my-app --files index.html app.js style.css \
  --intent 'Show a welcoming heading while keeping documentation accessible' \
  --expect-text 'role=heading[level=1]' 'Hello' \
  --preserve-text 'role=link[name="Documentation"]' 'Documentation' \
  --output ./capsule.json
secondlook inspect ./capsule.json
secondlook probe ./capsule.json --output ./baseline
```

Replace the files, selectors and expected text with the actual requirements.
Text checks compare the selected element's exact text. Repeat either flag to add
checks. These simple checks do not measure overall usability, aesthetics or every
behavior. For click/fill/download, holdouts and isolated JSON fixtures, edit the
capsule using the [reference](cli-reference.md) and [clean-slate guide](clean-slate.md).

Open `baseline/report.html`. Correct broken selectors or missing requirements
**before** calling a model. Do not change criteria after seeing candidates and
then treat the new scores as a predeclared experiment.

The capsule starts with `intent.confirmed: false`. Review and set it to `true`.
Alternatively, use `--confirm-intent` when creating a **new** capsule from
requirements you have already reviewed. Existing capsules are never overwritten.

### Compare all three workflows

Create `requirements.txt` from the original request and trusted facts, independent
of the old implementation. Specify what matters and what must remain. Avoid
copying old architecture choices into it unless they are actual constraints.

```bash
secondlook init ./my-app --files index.html app.js style.css \
  --intent 'Show a welcoming heading while keeping documentation accessible' \
  --expect-text 'role=heading[level=1]' 'Hello' \
  --preserve-text 'role=link[name="Documentation"]' 'Documentation' \
  --brief-file ./requirements.txt --confirm-intent \
  --output ./confirmed-capsule.json
secondlook run ./confirmed-capsule.json --mode compare-three \
  --model YOUR_EXACT_CLAUDE_MODEL_ID --budget-usd 1 --output ./comparison
```

Use an exact model ID available to your authenticated CLI. B/C/D get equal stop
caps within the $1 total. B patches; C writes an intent brief then patches; D
rebuilds without old writable source. A passing baseline skips model calls.
Outputs go to new directories; original files are unchanged. Inspect and adopt
changes manually. Reported costs are API-equivalent, not subscription billing.

For a reproducible starting input, clone the repo and substitute
`./examples/welcome` as the source, `index.html` as its only file, and
`./examples/welcome/requirements.txt` as the brief. That small example is synthetic.
Its free baseline is 1/2. We do not publish an invented live score for it.

## Preserve work for the next model

```bash
secondlook harvest ./confirmed-capsule.json --library .secondlook/library
secondlook candidate ./candidate.json --library .secondlook/library
secondlook watch --library .secondlook/library
secondlook queue my-candidate --budget-usd 1 --mode compare-three --library .secondlook/library
secondlook revisit PLAN_ID --library .secondlook/library
secondlook board --library .secondlook/library
```

Use the plan ID printed by `queue`. Build the explicit candidate profile using the
[problem-library guide](problem-record.md). Candidate capabilities are documented
claims, not inferred from a model's name. `watch` is a single catalog observation;
it installs no background service. Repeated identical plans skip prior attempts.
Changed source must be re-harvested. A deliberate new sample uses a new `--trial`.
Unknown-cost or interrupted attempts require `reconcile`; do not replay blindly.

## Export and share

```bash
secondlook share ./comparison/result.json --output ./shareable
secondlook share ./comparison/result.json --output ./visual-share \
  --include-screenshots --include-intent --title 'My revisit experiment'
```

Keep `index.html` and `summary.json` together. Images are embedded in HTML, so the
export works after the original run folder moves. Default exports omit original
intent, screenshots, private check labels/inputs, source, local paths and raw
receipts. Recognized versioned Claude IDs, counts, unknown states and source/check
hashes remain. Detailed failure reasons are only in your private full report.
The summary is derived from the supplied local result; it is not signed or an
independent audit. `share` makes no network request and never uploads anything.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Chromium missing | Run `python -m playwright install chromium` in the same environment. On Linux use `--with-deps` if system libraries are missing. |
| CLI flag unavailable | Update Claude Code; run `secondlook doctor --provider`. |
| All checks pass; no call | The free probe skipped the run. Add a real unmet requirement, or deliberately explore using `--force`. |
| Draft intent / rebuild contract | Review and confirm intent/brief; supply intent + preservation checks. |
| Output already exists | Use a fresh directory. Inspect old receipts before repeating paid work. |
| External resources blocked | Make the static app self-contained. Backends need a different adapter. |
| Cost unknown / interrupted | Preserve receipts. Library users run `reconcile PLAN_ID`; it reads evidence without another call. |
