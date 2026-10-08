# v0.4 review and decisions

One fresh `gpt-6-astra` reviewer inspected `e1cdd40..c4662b7` read-only.
The review audited all 12 provider receipts, checked source/data hashes and
looked for private paths in the built wheel/sdist. No new provider calls were
made. There were no Critical findings, three Important findings and one Minor.

## Important findings addressed in one fix pass

1. An explicit `context: null`, accepted by earlier capsules, crashed after a
   generation response. Normalize it before filtering patch policies.
2. Read-only JSON test inputs fulfilled unsupported HTTP methods as successful
   responses. Keep GET/HEAD semantics, omit HEAD response bodies and preserve
   the static server's rejection of POST/PUT/DELETE.
3. Harness errors counted as unmeasured in category totals but appeared as FAIL
   in the table and red bars. Render them consistently as UNKNOWN; actual
   behavioral failures retain FAIL.

Six targeted regression cases failed before these fixes, then all six passed
in 8.08 seconds. The HEAD case exposed the body-semantics issue in addition to
the reviewer's POST reproduction. Final suite and package results are recorded
in [verification-v0.4.json](verification-v0.4.json). There was one reviewer and
one fix pass; no second review was dispatched.

The live experiments used the harness at `c4662b7` before these boundary fixes.
Their capsules omit `context`, their apps use GET for JSON, and no harness-error
rows occurred. Their original frozen results and provider receipts remain
unchanged. Final installation smoke rechecks the real input-isolated baseline
using the packaged corrected harness without making model calls.

## Deferred Minor

When a budget/unknown-cost stop skips a later candidate, its A-to-candidate row
is absent. Candidate-to-candidate comparisons remain inconclusive, and the
overall run remains inconclusive. An explicit skipped baseline-comparison row
would make the report more complete. This does not affect the fully executed
live cases or the zero-call baseline control.

## Rulings made

- Reuse the immediately preceding test output rather than make the plan helper
  rerun it. This follows the higher-priority instruction against redundant
  verification. Risk: manual ledger transcription can be wrong; raw logs remain.
- Add isolated read-only JSON inputs and a new job-only trial after finding the
  DOM-containment confound. This fulfills the independent-evaluation goal.
  Risk: finite assertions can still miss behavior; retain the first trial and
  explicitly separate post-hoc diagnosis from new frozen evidence.
- Keep general superiority, adoption, aesthetic quality and market demand
  outside this finite one-sample trial. Risk: unmeasured value may differ.
- Require human provenance review for arbitrary future briefs/shared files.
  Syntax cannot prove semantic independence. Risk: old assumptions can survive.
- Leave historical authorship and remote UGV availability unknown. Evidence
  was unavailable. Risk: neither can support an adoption decision.
- Audit preserved terminal provider receipts without more paid review calls.
  Re-execution cannot change those receipts. Risk: current provider behavior
  could differ from the dated experiment.
- Complete post-fix tests, installation and packaging in the executor without
  a second reviewer. Risk: the final artifact gate is not another independent
  review; fresh review plus reproduced regressions and logs is the evidence.

## Product evidence boundary

The three projects are private local cases, with agent-curated scopes grounded
in their documentation. The raw score correction is disclosed in
[real-cases-v0.4.md](real-cases-v0.4.md). No original project was replaced, no
candidate was adopted, and no repository/package/site was publicly published.
