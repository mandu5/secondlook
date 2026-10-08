# Clean-slate revisit implementation

Spec: `docs/spec-v0.4.md`
Base: `e1cdd40`; branch: `feat/clean-slate-revisit`.
Execute inline with superpowers:executing-plans. One fresh final reviewer.

## Global constraints

Preserve original files and all receipts. Never retry unknown remote outcomes.
No publishing, outreach or automatic adoption. Static adapter only. Maintain
compatibility with existing v0.3 capsules/modes and reconciliation guards.

## Task 1: Independent contract and source-blind execution

Files: core.py, runner.py, tests/test_rebuild.py.
Interfaces: validated rebuild/readonly contract -> prompt projection, complete
file replacement, mode dispatch. Existing execution identity hashes both files.

1. Write tests for no legacy/hidden-check leakage, all-or-nothing output
   validation, preserved read-only data, category provenance and missing contract.
2. Run `.venv/bin/python -m pytest tests/test_rebuild.py -q`; expect new-feature
   failures. Implement the narrow schema, prompt and D path.
3. Run that file plus test_core.py and test_workflow.py; expect all pass, including
   real-browser three-arm comparisons and unchanged source hashes.
4. Commit code/tests and record actual RED/GREEN evidence.

## Task 2: Portfolio and complete comparison report

Files: portfolio.py, cli.py, portfolio_cli.py, evaluate.py, report.py, tests.
Interfaces: modes and contract from Task 1 -> queue gating/execution; check
categories -> per-arm report; all pairwise outcomes -> neutral report summary.

1. Write failing tests for new-mode queue/skip, baseline zero spend, preservation
   losses beside intent gains, and D-only/three-way report rendering.
2. Implement mode choices, explanatory missing-contract exclusion and category
   evidence. Report every A/candidate and candidate/candidate comparison; never
   present the best arm's result as the whole experiment.
3. Run targeted tests; expect previous receipt/reconcile tests unchanged and new
   cases green. Commit and ledger.

## Task 3: Real cases, verification and distributable v0.4

Files: private `.secondlook/v04-real`, docs, README files, version, dist artifacts.
Interfaces: frozen capsules -> library -> same-model equal-cap campaign -> report.

1. Copy originals, record scoped documentary evidence and full original hashes.
   Freeze criteria before generation, run free probes, preserve their failures.
2. Execute one campaign with three declared $1 allocations and explicit runtime
   model `claude-sonnet-5-5`. Respect every budget/unknown-outcome stop.
3. Verify receipts, source blindness, original hashes, all report UI, mobile
   layout, zero-call negative control and duplicate suppression.
4. Document measured results and limits, update v0.4 wheel/source bundles and run
   appropriate full suite and clean-install smoke. Commit evidence and docs.

## Review Focus

Inspect source/criteria leakage through metadata and shared files; strict
read-only enforcement; partial/duplicate/path-traversing generated outputs;
projected context incompatibility; source-change and interrupted receipt handling
under new modes; misleading aggregate verdicts when an arm regresses or fails;
new-mode library recovery bindings; private-case information in public bundles;
whether real-case claims distinguish proposed requirements, synthetic inputs,
negative control, unknown authorship and one-sample workflow comparisons.

## Completion

One fresh whole-branch review, one justified Critical/Important fix pass with
RED/GREEN evidence, full suite green, browser-visible reports and clean package.
Archive ledger and logs in `.secondlook/verification-v04`, remove only this plan's
scratch workspace, leave the feature branch local with reviewable commits.
