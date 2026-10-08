# CLI and capsule reference

For the first run, start with the [quickstart](quickstart.md). This reference covers advanced capture, replay and evidence boundaries.

## Import results from your existing AI tool

```bash
secondlook prepare capsule.json --mode ordinary --output request
secondlook assess request --response response-a.json --label 'Model A' \
  --response response-b.json --label 'Model B' --output comparison
```

`prepare` defaults to `--mode rebuild`, which requires a confirmed independent
brief and both intent/preservation checks. Give only `request.md` to the external
tool. `assess` accepts 1–4 response/label pairs and optional `--usage FILE` with
an array of owner-reported costs/token counts in the same order. Both commands
make zero model calls. Imported metadata is unverified; absent cost is unknown.
See [formats, exit codes, privacy and a reproducible example](external-models.md).

## Use your own problem library

```bash
# Existing confirmed capsule, or a general record with --problem.
secondlook harvest my-capsule.json --library .secondlook/library
secondlook harvest examples/problem.json --problem --library .secondlook/library

# Restore a preserved original into a new directory, even if its source was deleted.
secondlook restore TASK_ID --output ./restored-original --library .secondlook/library

# Edit the example profile to use a model ID actually available to your CLI.
secondlook candidate my-candidate.json --library .secondlook/library

# First observation inventories the catalog. Later runs record changes.
# Optional --queue prepares plans only for explicitly mapped candidate profiles.
secondlook watch --library .secondlook/library
secondlook queue my-candidate --budget-usd 2 --library .secondlook/library

# Use the plan ID returned above. This is the step that can call the model.
secondlook revisit PLAN_ID --library .secondlook/library
secondlook board --library .secondlook/library
```

`watch` is one observation, not an installed background service. It can be invoked by your scheduler; it never dispatches a model. New catalog availability is not measured improvement. Candidate capability tags and impact/cost estimates are explicit user claims, not predictions.

The saved queue uses declared impact divided by declared cost, with capability overlap. It allocates complete per-task stops within the campaign budget. Free baseline checks still skip tasks whose captured requirements already pass. Exact attempt history avoids redispatch for the same task/source/checks/model profile/workflow/harness/environment/trial; use a different `--trial` for a deliberate new sample. Changed source requires re-harvesting. Alias-only IDs such as `sonnet` are refused for portfolio profiles; update the declared revision when provider behavior changes.

Interrupted or unknown-cost campaigns block further execution. `secondlook reconcile PLAN_ID` reads completed matching evidence without replaying requests. If receipts remain uncertain, the block remains. Cost limits are best-effort provider stops, and reported dollars are API-equivalent rather than subscription invoices.

For the single-artifact offline walkthrough, use `secondlook demo --offline --output .secondlook/offline`.

## Compare revision workflows

Install and authenticate a recent [Claude Code CLI](https://code.claude.com/docs/en/cli-reference) first. This adapter requires `--restricted`, `--safe-mode`, `--json-schema`, and `--max-budget-usd`; it checks support before making model calls.

```bash
secondlook demo --model sonnet --budget-usd 2 --output .secondlook/live
```

| Arm | What runs | Interpretation |
| --- | --- | --- |
| A | Saved artifact, evaluated now | Current behavior in the fixed harness |
| B | Candidate model, ordinary improvement | A practical comparison workflow |
| C | Same candidate model, intent brief before seeing legacy source, then revision | Tests whether reframing adds value |
| D | Same candidate model, independent requirements and read-only data, complete new files | Tests a clean-slate implementation without legacy source |

The standard `demo` and `--mode compare` run B/C. To compare B/C/D, use a capsule
with an independently sourced `rebuild` brief and categorized checks:

```bash
secondlook run examples/clean-slate/capsule.json --mode compare-three \
  --model YOUR_EXACT_MODEL_ID --budget-usd 1 --output .secondlook/three-way
```

`compare-three` splits the total stop budget into three equal caps; `rebuild`
runs only D. The report exposes every pairwise comparison, checked preservation
and intent, actual spend and screenshots. D receives no legacy writable source
or hidden test inputs. It may still inherit assumptions in the supplied brief.
See [the contract and limits](clean-slate.md).

In B/C mode each gets half of the experiment's stop budget. C's first call gets 30% of its effective allowance; implementation can use the remaining allowance. If a provider overshoot leaves a later arm a smaller allowance, the report records that limit and marks the workflow comparison inconclusive. The exact model IDs reported by the provider are saved. Missing, multiple or different actual identities also make comparisons inconclusive. All failed calls with known spend count toward the total. Unavailable token usage is shown as unknown.

**A → C is an artifact difference. B → C is a workflow comparison. Neither alone establishes causal model uplift.** Equal ceilings do not mean equal realized spend or equal token counts. One trial cannot establish general superiority. If both candidates pass the same checks, the report says reframing added no measured functional gain.

Claude's reported dollars are **API-equivalent estimates**, not the charge on a subscription invoice. The native stop limit is best effort and may overshoot by an in-flight response. Missing cost is **unknown**, never zero; the run stops instead of retrying. The default is $2 API-equivalent for the entire experiment.

## Bring an existing HTML app, even with embedded images

`capture`, `requests`, `inspect`, and `probe` make **zero model calls**. For a self-contained HTML app, `--scripts-only` keeps the complete app for local execution but sends only executable inline scripts to the model. HTML, CSS, JSON data scripts and embedded images stay protected.

```bash
# checks.json is an array of product acceptance checks (example below).
secondlook capture ./my-app/index.html \
  --intent 'Keep keyboard focus when saving favorites' \
  --checks checks.json --scripts-only --output capsule.json
secondlook inspect capsule.json
secondlook probe capsule.json --output .secondlook/baseline
```

The capsule starts as a draft. Review the original intent, constraints and failures, then set `intent.confirmed` to `true` before `run`. Use `--confirm-intent` at capture time only after reviewing the request. A free probe is allowed on a draft and does not confirm it. A completed probe can contain failed behavior checks; harness errors return an inconclusive result.

To recover the original request from an explicit local Codex or Claude JSONL log:

```bash
secondlook requests /path/to/session.jsonl
secondlook requests /path/to/session.jsonl --line 23
secondlook capture ./my-app/index.html \
  --session /path/to/session.jsonl --request-line 23 \
  --checks checks.json --scripts-only --output imported-capsule.json
```

Only the selected human request is imported. Physical line numbers and request/session hashes preserve provenance. Tool output, common environment wrappers and oversized records are skipped; the command reports skipped counts. Logs are bounded to 512 MiB, records to 4 MiB, selected requests to 32,000 characters. Nothing scans your entire history or sends the log to a model. A session's model hints **do not prove authorship of the artifact**.

An independent keyboard checkset can look like this:

```json
[
  {
    "id": "favorite-focus",
    "viewport": {"width": 390, "height": 844},
    "actions": [
      {"type": "focus", "selector": "#favorite"},
      {"type": "press", "key": "Space"}
    ],
    "assert": {"selector": "#favorite", "focused": true},
    "capture": true
  }
]
```

The runtime limit is 256 MiB; total selected source context is capped at 64 KiB. A real local 120,410,551-byte app fit into 14,829 bytes of source context using this projection. This is a byte measurement, **not measured token savings**; prompt overhead and actual provider usage are separate. The projection cannot edit markup or styling, and scripts can still contain private text. Review the selected source before a live run.

The script selector is deliberately conservative: it skips data/external/`nomodule` scripts and raw text such as `textarea` or `noscript`, retains the first duplicate attribute as HTML does, and refuses ambiguous markup. Inline SVG/MathML, `template`, `plaintext`, self-closing raw-text tags and script escape syntax are currently unsupported in `--scripts-only` mode. Use a small explicit source allowlist when this projection cannot safely classify a file. Edits are authorized against the original regions; changing script boundaries is rejected before any candidate file is written.

## Capture an allowlisted multi-file static app

```bash
secondlook init ./my-app \
  --intent 'Export exactly the filtered records as valid CSV' \
  --files index.html app.js style.css \
  --output my-capsule.json
```

Edit the generated capsule:

1. Preserve the original request and its source. Set `intent.confirmed` to `true` after review.
2. Record known failures, constraints, and assumptions with their provenance.
3. Replace the generated page-visible smoke check with actual product acceptance checks. Mark unseen edge inputs with `held_out: true`.
4. Declare capability triggers, impact (1–5), and an estimated experiment cost.

For example, an independent CSV check:

```json
{
  "id": "visible-export",
  "name": "Export matches visible rows",
  "actions": [
    {"type": "fill", "selector": "#search", "value": "Keyboard"},
    {"type": "download", "selector": "#export"}
  ],
  "assert": {"csv": [["id", "title"], ["F-104", "Keyboard shortcut"]]}
}
```

Supported actions: `click`, `fill`, `select`, `download`, `focus`, `press`, `reload`. `press` without a selector uses the current keyboard focus. Assertions: exact DOM `text`, `count`, `value`, `visible`, `focused`, `attribute: {"name": "aria-pressed", "value": "true"}`, or parsed `csv` rows. Each case starts with a fresh browser context. `reload` preserves that case's local storage. `viewport` sets a case's width/height (240–3840 pixels); the default is 1200 × 820. `capture: true` records its final state. See the complete [example capsule](../src/secondlook/demo/capsule.json).

```bash
# No model calls. Selection uses your declared estimates, not an uplift prediction.
secondlook plan my-capsule.json another-capsule.json \
  --capability coding --budget-usd 4

# Output must be a new directory outside the source root.
secondlook run my-capsule.json --model sonnet --budget-usd 2 \
  --output ./revisit-output

# Lower-cost single-workflow run when you do not need the B/C comparison.
secondlook run my-capsule.json --mode ordinary --budget-usd 1 \
  --output ./revisit-ordinary

# Rebuild presentation from saved evidence; no model call.
secondlook report ./revisit-output/result.json
```

If every baseline check already passes, model calls are skipped. That is a conservative probe, not proof that no improvement is possible. Add a meaningful failing check, or use `--force` for an explicitly exploratory run. Only selected source is sent; total UTF-8 source context is capped at 64 KiB. The model returns small anchored edits rather than full-file rewrites. Old model responses are never reused to measure a new model.

## Evidence and boundaries

```text
revisit-output/
  report.html                 standalone visual comparison
  result.json                 outcomes, costs, token use, identities
  capsule.frozen.json         original intent + fixed independent checks
  arms/A/ B/ C/               isolated copies, originals untouched
  evidence/A/ B/ C/           browser results and screenshots
  receipts/                   prompts, dispatch journal, raw provider JSON
  B.patch  C.patch            reviewable unified diffs
  B.diff   C.diff             selected-code display diffs when projected
  B.edits.json C.edits.json   exact replacements tied to source identity
```

Projected `.diff` files are for inspection, **not `git apply` against the full HTML**. Read the exact-edit recipe and inspect the runnable candidate copy. Adoption is manual; no command overwrites your original app.

- The model has no filesystem, shell, browser or network tools. It receives selected text and returns structured edits. User/project customizations are disabled; managed organization policy can still apply in Claude Code.
- Tests live outside candidate source. The model does not see check definitions, including holdout inputs. It can still infer requirements from the original brief; this is not a secret benchmark.
- The host writes only allowlisted copies. Path escapes, symlinks, hidden paths and private key/config filenames are refused. An allowlist is not a secret detector: inspect files before sending them to a provider.
- The evaluator serves static files on a temporary localhost origin and blocks other browser requests and WebSockets. **This is not an OS sandbox for hostile code or arbitrary repositories.** Use trusted static apps. Backends, package scripts and build commands are unsupported.
- Evaluation errors are inconclusive. Regressions override new passes. Browser timings include assertion waits and are not performance benchmarks. Screenshot differences have no automatic aesthetic score.
- Each run uses a new output directory. Interrupted or malformed calls keep their receipt and stop. Inspect the receipt before starting another logical request; no automatic retries or remote reconciliation are implemented.
- Prompt/receipt files may contain your source. `.secondlook/` is ignored by Git. Keep private reports private; review artifacts before sharing.

## Development

```bash
python -m pytest -q
python -m compileall -q src
```

Tests cover source boundaries, exact patch behavior, real subprocess receipts, timeout handling, conservative budgets, browser behavior, offline CLI use and HTML escaping. No test invokes a paid model. [Validation record](validation.md) distinguishes live evidence from test fixtures.

This version supports synthetic examples and a real large local artifact. Cross-provider adapters, repository-wide failure harvesting, automatic release triggers, general code execution sandboxes, validated scheduling heuristics, repeated trials and real-user outcome studies remain future work. [Product direction](roadmap.md).

The package name is `secondlook-revisit`; the executable is `secondlook`. Tagged wheels and source releases are available on [GitHub](https://github.com/mandu5/secondlook/releases). The package is not published to PyPI.
