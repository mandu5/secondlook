# Second Look v0.3: a library of problems worth revisiting

The product preserves original problems and decides which deserve another attempt when model capabilities change. Artifact evaluation is one execution adapter. A wardrobe catalog was a private validation case, never the product domain.

## User outcome

Save tasks from several projects, including tasks that cannot yet run automatically. Observe a public model catalog without an LLM. Choose an explicitly configured candidate and get a budgeted, explained queue. Execute the saved queue once. See improvements, regressions, unresolved work, actual usage, and links to artifact comparisons together.

## Binding requirements

- Store original intent and its source, constraints, observed failures, and legacy assumptions separately. Do not manufacture historical model authorship. Preserve immutable revisions; identical harvests are idempotent.
- Preserve allowlisted original artifact bytes in compressed content-addressed objects. Restore into a new directory after validating content identity. Live-source staleness checks remain in place.
- Generic problem records are supported. Only confirmed static-HTML capsules have an execution adapter in this version. Missing evaluators are visible blocked work, not a successful upgrade.
- A first model-catalog sync establishes an inventory. Later additions/changes/removals are observations, not proof of capability improvement. Preserve source, time, and content identity. Reject malformed/oversized catalogs atomically.
- Candidate profiles explicitly record a Claude CLI model ID, a revision, capability claims, and their evidence. No automatic provider-name mapping or inference that a new release is better. Record actual model IDs from execution separately.
- Queue selection uses declared impact/cost and capability overlap, not predicted uplift. Every exclusion has a reason. Per-task stop allocations sum to at most the campaign budget.
- Reuse attempt history only for identical task/source/checks/candidate revision/workflow/harness/environment/trial. History avoids a duplicate dispatch; it never becomes new evaluation evidence. A deliberate extra trial has a different key.
- SQLite transactions serialize campaign claims. An interrupted/unknown campaign prevents further dispatch until its terminal receipts can be reconciled. No lease expiry or automatic replay. Provider limits remain best-effort, and unknown/over-budget cost stops subsequent tasks.
- Plan changes, changed source, and changed candidate profiles invalidate execution before paid dispatch. Execute from the frozen task definition and verify the source snapshot again inside the runner.
- A portable local board shows the whole library, queue explanations, measured before/after outcomes, costs/tokens with unknowns, and report links. No private data is published.

## Non-goals and limits

No claim of unique invention, broad demand, generalized superiority, or a historical old-versus-new-model benchmark. No autonomous background service installed. `watch` performs one catalog observation and can prepare queues for explicitly mapped changed candidates; execution is a separate command. No arbitrary backend/repository execution, full clean-slate rebuild, LLM judge, embeddings, or provider routing in v0.3. The intent-first arm still makes bounded source edits after an independent brief.

## Acceptance

A reproducible multi-project demo includes runnable and parked problems, a clearly labeled simulated catalog change, budget exclusions, a real browser artifact comparison, and a second identical queue that avoids completed work. Separately verify the live public catalog and at least one bounded real-provider campaign. Verify stale source, duplicate workers, unknown spend, malformed catalogs, and report escaping with focused tests.
