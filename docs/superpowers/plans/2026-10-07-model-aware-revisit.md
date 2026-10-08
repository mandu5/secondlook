# Model-aware revisit implementation

> Execute inline with superpowers:executing-plans. One fresh whole-branch reviewer at the end.

**Goal:** Restore the original product loop: harvest problems, observe model changes, select valuable revisits within a budget, and compare actual outcomes across projects.

**Architecture:** A local SQLite library stores immutable problem and candidate revisions, catalog observations, frozen plans and durable attempts. A deterministic planner feeds the existing bounded browser runner. Static HTML is one adapter; unsupported problems remain visible. A generated HTML board connects intent, decisions and results.

**Tech Stack:** Python 3.11 standard library / SQLite, existing Playwright and Claude CLI adapter.

**Spec:** `docs/spec-v0.3.md`

## Global Constraints

Preserve originals and private `.secondlook` evidence. No publishing. Never equate model availability with quality. No inferred old-model authorship. No duplicate paid requests after interruption. Unknown cost stays unknown. No model calls while harvesting, syncing, planning, or rendering. CLI provider dollars are API-equivalent and best-effort. Reuse the existing runner rather than recreating its cost and receipt handling.

## Review Focus

Adversarial inputs: malformed/oversized catalogs; source or candidate mutation after planning; simultaneous/repeated execution; interruption with unknown provider outcome; HTML/path injection and falsely complete usage. Review budget accounting and causal claims as well as functionality.

### Task 1: Durable problem library and catalog observations

**Files:** `src/secondlook/library.py`, `src/secondlook/catalog.py`, `tests/test_library.py`.

**Interfaces:** `Library(path)`, `harvest_capsule(path)`, `harvest_problem(record)`, `records()`, `register_candidate(profile)`, `candidate(id)`, `sync_catalog(payload, source)`. Revision IDs are content fingerprints; records retain provenance and source identity. `fetch_catalog()` is bounded and read-only.

1. RED: test duplicate harvests, changed-source revision, generic parked records, first-sync baseline, later event deltas, atomic malformed rejection, candidate validation.
2. GREEN: implement SQLite persistence, bounded validators, normalized catalog observations and explicit candidate profiles.
3. Verify focused tests; commit the library/catalog slice.

### Task 2: Budgeted queues and durable execution

**Files:** `src/secondlook/portfolio.py`, `src/secondlook/runner.py`, `tests/test_portfolio.py`.

**Interfaces:** `make_plan(library, candidate_id, budget, mode='reframe', trial=1)`, `execute_plan(library, plan_id, progress=None)`, `reconcile_plan(library, plan_id)`. Runner receives an optional expected source identity. Plans are stored, claims are atomic, attempted keys persist, unknown results stop the library.

1. RED: test capability/adapter/budget exclusions, stale plans, duplicate claims, exact-repeat suppression, source mutation before dispatch, unknown cost and overshoot stopping later work, terminal-only reconciliation.
2. GREEN: deterministic selection with reasons; frozen identities; transactional attempt reservation; sequential adapter execution; receipt-aware reconciliation with no replay.
3. Verify tests including existing runner compatibility; commit.

### Task 3: CLI, board and reproducible portfolio demo

**Files:** `src/secondlook/portfolio_cli.py`, `src/secondlook/board.py`, `src/secondlook/cli.py`, `src/secondlook/portfolio_demo.py`, `tests/test_portfolio_cli.py`.

**Interfaces:** commands `harvest`, `candidate`, `watch`, `queue`, `revisit`, `reconcile`, `board`, `portfolio-demo`, each with `--library`; existing commands stay compatible. `write_board(library)` renders escaped, local evidence. Demo uses explicit simulation labels, real browser checks and no model call by default.

1. RED: CLI integration across harvest/queue/execute/board; report escaping and unknown usage; watch queues mapped changed candidates only; offline portfolio demonstration preserves source and avoids repeats.
2. GREEN: wire CLI and board to real modules, add runnable and parked demo tasks, expose saved plans and result links.
3. Run demo and browser review; commit.

### Task 4: Live verification, research and release evidence

**Files:** README, `docs/roadmap.md`, `docs/research-v0.3.md`, `docs/verification-v0.3.json`, version metadata, review record.

1. Check current primary sources for competing eval tools and catalog semantics. Separate established features, hypotheses and untested demand.
2. Verify live catalog sync; run a bounded real-provider campaign; verify repeat exclusion and source preservation. Save private receipts and public aggregate facts.
3. Run complete tests and wheel/clean-install CLI demo. Review the branch with one fresh reviewer, fix important findings via RED/GREEN once, document any remaining limits.
4. Archive rulings/review, commit, remove only this plan's scratch workspace, report the usable local artifact and material limits. Do not publish.
