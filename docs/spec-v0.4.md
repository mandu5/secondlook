# v0.4: Revisit the purpose without inheriting the implementation

Second Look preserves old work so that a later model can reconsider the original
problem. v0.4 adds a genuinely source-blind implementation route and evaluates it
against the same frozen behavioral contract as ordinary revision.

## User-visible contract

- Existing `compare` (B/C), `ordinary`, `reframe`, and offline examples retain
  their meaning. `compare-three` runs B ordinary patch, C independent intent brief
  then patch, and D clean-slate rebuild. `rebuild` runs D alone.
- A is the saved artifact, whose generating model can be unknown. B/C/D use the
  same requested model and equal planned total caps. Actual identity, effective
  cap, usage and failures remain visible. One sample and a fixed B/C/D order do
  not establish general workflow or model superiority.
- D receives original intent, constraints, recorded failures, an independently
  sourced rebuild brief, writable filenames, and explicitly shared read-only
  files. It never receives old writable content, source excerpts, screenshots,
  test definitions, or C's brief. It returns complete replacement files in one
  call. B/C receive the same independent brief as well as legacy source.
- A rebuild capsule declares `rebuild: {brief, source, confirmed}` and optional
  `readonly_files`. The brief records requirements and facts, not old source.
  Confirmation means the experiment scope is authorized; documentation-derived
  criteria must identify the curator and are not historical user testimony.
- D requires both `intent` and `preservation` check categories with nonempty
  `basis` provenance. CSS/Playwright role selectors may express visible behavior
  without requiring the old DOM. These are finite checks, not full coverage.
- The complete check list is frozen and hashed before any call. All arms use it.
  Reports show category scores and every pairwise comparison, with regression
  taking precedence. There is no automatic winner or automatic adoption.
- Check-local JSON `inputs` can override only declared read-only `.json` files
  in that check's browser. Overrides never mutate files, leak into another check,
  or reach model prompts. This supports one independent input per behavior,
  avoiding assumptions about where a fresh layout nests labels inside links.
  Limit each check's serialized override data to 64 KiB. Both source and override
  provenance must distinguish synthetic test inputs from production observations.
- D writes only the exact declared writable set; read-only inputs cannot change
  in any arm. Validate complete output before writing. Generated writable text
  is capped at 64 KiB. Script-projected capsules cannot rebuild in v0.4, because
  their unshown implementation cannot be reconstructed from an independent brief.
- Baseline pass still skips calls. Portfolio plans carry the new modes through
  immutable attempts, receipts, source guards, accounting and reconciliation.
  Missing rebuild contracts are explained at selection time.

## Real-case validation

Use private copies of three existing projects with unknown historical model
provenance. Scope is selected by the agent from existing project documentation,
not represented as three interview-confirmed customer failures:

1. Job Radar static page: honest deadline classification and exclusion of expired
   opportunities, from its original design. Existing HTML remains unchanged in
   the baseline; a small declared synthetic edge-case data file is shared by all
   arms. Test data is not described as historical production failures.
2. UGV-MON portfolio page: clarify mock mode, passive monitoring and a documented
   local launch fallback. Do not claim the remote deployment is broken or inspect
   network traffic. Preserve links and project identity.
3. TSAD research page: negative control. Freeze checks for already documented
   statistical context, reproducibility and manuscript status. If they pass, skip
   all candidates; do not invent a defect to spend a third experiment budget.

Budget: at most $3 API-equivalent planned across the three cases, $1 each;
provider in-flight overshoot remains possible. Preserve actual receipts and
original hashes. Human adoption, aesthetic quality, retention, user demand and
old/new-model uplift are not established by this run. No public publication,
outreach, source replacement or arbitrary repository command execution.

Preflight amendment after the first campaign: Job Radar's link-contained label
checks penalized a correct alternative layout. Preserve that trial as criteria-
confounded, re-evaluate existing candidates only as post-hoc analysis, and freeze
input-isolated cases for a separate job-only trial. Do not repeat the unaffected
UGV/control cases. Count both campaigns toward the $3 actual stop ceiling.

## Scope boundaries

The adapter remains static HTML/CSS/JS. General code/research reruns, release
quality prediction, predictive token optimization, multi-provider comparisons,
and community recruitment belong to later milestones. Independent briefs may
still encode human assumptions; source blindness does not guarantee good framing.
