# Model-neutral revisit without a new API purchase

The owner wants a free project address and continued development of the original
preserve-intent/revisit/measure workflow. They have authorized implementation and
publication, with no new paid services. The v0.5 baseline has 202 passing tests.

## Decision

Extend the existing static-app evaluator with a portable request and response
boundary. A local `prepare` command freezes source, intent and acceptance checks,
then writes one model-facing Markdown request. The user can use an existing chat,
coding assistant or local model. `assess` imports 1–4 responses and evaluates the
baseline and candidates locally. No provider call occurs in either command.

Alternatives considered: another paid API adapter adds financial/setup friction;
arbitrary Python/repository execution needs a new sandbox contract. Both remain
future work. Importing existing outputs is established evaluation practice, not
our novelty. This increment removes the Claude CLI requirement for evaluation;
it does not automate external chat submission or prove cross-model superiority.

## Contract

- Python >=3.11; no new dependencies; existing Playwright isolation remains.
- `prepare CAPSULE --mode ordinary|rebuild --output NEW_DIRECTORY` defaults to
  rebuild. Rebuild requires independently confirmed requirements and both purpose
  and preservation criteria. Ordinary uses the existing selected-source policy.
- Output contains `request.md`, `response.schema.json`, `request.json`,
  `capsule.frozen.json` and a `baseline/` snapshot. Only `request.md` is supplied
  to the external model. Private acceptance checks stay out of that request.
- Request identity binds the normalized frozen capsule, full source identity,
  mode and preparation harness identity. The response contains that request ID,
  a summary and either anchored edits or complete writable files. Rebuild request
  excludes all legacy writable source; external context isolation is unverified.
- Moving the request directory works. Original source may change or disappear
  after preparation: assessment uses the frozen snapshot, not live files.
- Tampered request/capsule/source, symlinks, path traversal, nonfinite or duplicate
  JSON keys, oversized inputs and an existing output directory fail clearly.
- Response JSON may be wrapped in exactly one Markdown JSON fence. Extraneous
  prose or unexpected fields are rejected, never executed.
- `assess REQUEST_DIR --response FILE --label LABEL [repeat] --output NEW_DIR`
  accepts 1–4 response/label pairs. Optional `--usage FILE` is a same-order JSON
  array of null or owner-reported cost/token records. Model labels and usage are
  explicitly unverified. Missing cost/tokens remain unknown, including exports.
- All response IDs and metadata are validated before creating an output. Invalid
  edits become a failed candidate with evidence; other candidates can complete.
- Each candidate is built in its own directory. Same-content candidates reuse
  within-batch browser evidence with a visible reuse marker, not another sample.
  Repeating the same response file in one batch is rejected as a likely mistake.
- Compare every pair for measured behavior. Any regression overrides new passes.
  There is no model ranking, automatic adoption or statistical success claim.
- Results use `kind=imported_candidates`, arms A/E1–E4, raw response hashes,
  preparation/evaluation identities and 0 locally dispatched model calls. External
  model calls/cost are not inferred from this zero. Durable result is written
  before browser evaluation; incomplete evaluation stays inconclusive.
- Report distinguishes local evaluation from live model experiments and reports
  owner-supplied labels/usage as such. Sharing omits private labels, inputs and
  source; imported metrics retain their unverified origin.
- Existing capture/run/probe/portfolio/share behavior stays compatible.

## Release and evidence

Publish a labeled hand-authored import example, no-model clean-install CLI smoke,
desktop/mobile report verification, unit/integration results and this limitation:
no new two-model performance experiment was run. Retain v0.5 evidence intact.

Free hosting uses an existing authorized Hobby account when access permits. The
Vercel connection currently returns a team authorization error; no project URL is
claimed until production and anonymous access are verified. Domain registration,
paid upgrades, model purchases and unsolicited recruitment are outside this run.
