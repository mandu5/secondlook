# Real Project Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Revisit a real large HTML artifact using selected code context and independent keyboard checks.

**Architecture:** Preserve runtime source separately from a bounded context projection; integrate both into the existing runner. Deterministic session parsing and capture create capsules without model calls. Browser checks and reports expose the measured real outcome.

**Tech Stack:** Python 3.11+, standard-library HTML/JSON parsing, existing Claude CLI adapter, Playwright.

**Spec:** `docs/spec-v0.2.md`

## Global Constraints

- Original artifacts are never overwritten; all private case evidence stays ignored and local.
- Selected context is capped at 64 KiB; total allowlisted runtime source is capped at 256 MiB.
- Model edits cannot target protected source regions.
- Byte reduction is not measured token savings.
- Capture/probe make no model calls. Imported intent needs explicit caller confirmation.
- Preserve v0.1 behavior, cost accounting and independent acceptance checks.

## Review Focus

- Executable script classification, Unicode and delimiter changes cannot allow writes into protected data (Task 1).
- Source identity includes the full artifact; large opaque payloads never enter prompts or diff context (Tasks 1 and 3).
- Log wrappers, tool text, duplicates, oversized records and malformed lines cannot become false original intent (Task 2).
- Keyboard/reload assertions must measure actual focus and persistent app state, with schema errors inconclusive (Task 3).
- Reports distinguish byte exclusion from tokens saved and private case data is excluded from release artifacts (Task 4).

### Task 1: Runtime snapshots and bounded context

**Files:** `src/secondlook/artifacts.py`, `src/secondlook/core.py`, `tests/test_artifacts.py`.

**Interfaces:** `capture_artifact(capsule: dict) -> Artifact` exposing `sources`, `context`, `identity`, `metrics`; `context_spans(text: str, policy: dict | None) -> list[tuple[int,int]]`; `apply_edits(..., context: dict | None=None)` enforces source-region scope. Core `source_bundle` returns model-visible context for compatibility.

- [ ] Write tests for large embedded JSON omission, script MIME types, Unicode indexing, protected patch refusal, source hash changes and context/runtime size caps.
- [ ] Run `python -m pytest tests/test_artifacts.py -q`; expect missing implementation failures.
- [ ] Implement explicit HTML script projection and full-source identity, with exact scoped patches.
- [ ] Run artifact/core tests; expect all pass. Commit `feat: separate runtime artifacts from bounded model context`.

### Task 2: Local intent harvesting and capsule capture

**Files:** `src/secondlook/capture.py`, `src/secondlook/sessions.py`, `tests/test_capture.py`.

**Interfaces:** `read_requests(path: Path) -> dict` returns typed human-request records with line and digest; `capture_html(path, intent, checks, output, scripts_only, confirmed, provenance) -> Path` writes a validated capsule outside source. `inspect_artifact(capsule_path) -> dict` reports local sizes and selected regions without model calls.

- [ ] Write fixtures for real observed log shapes, tools/wrappers, malformed/oversized records, exact request provenance and draft-confirmation behavior.
- [ ] Run `python -m pytest tests/test_capture.py -q`; expect missing implementation failures.
- [ ] Implement deterministic bounded parsing and explicit HTML/checkset capture; do not infer historical artifact model from session metadata.
- [ ] Run capture tests; expect all pass. Commit `feat: capture intent and checks without model calls`.

### Task 3: Keyboard checks, probe and projected runs

**Files:** `src/secondlook/evaluate.py`, `src/secondlook/runner.py`, `src/secondlook/cli.py`, `tests/test_capture_workflow.py`.

**Interfaces:** consumes Artifact and capture/session helpers; `probe(capsule_path, output)` returns A-only evidence; existing run uses full source for execution and projected source for prompts and scoped edits. New CLI: `capture`, `requests`, `inspect`, `probe`.

- [ ] Write real-browser tests for lost/restored focus, press/reload, per-check viewport, immutable large data, no-call probe, and CLI capture→probe→run.
- [ ] Run `python -m pytest tests/test_capture_workflow.py -q`; expect new behavior failures.
- [ ] Implement and integrate with existing costs/identity/comparisons. Preserve compact full-source diffs without opaque payload context.
- [ ] Run the whole suite; expect old and new tests pass. Commit `feat: run projected artifacts with keyboard acceptance checks`.

### Task 4: Real case, report and release evidence

**Files:** `src/secondlook/report.py`, documentation, version metadata, public aggregate validation record.

**Interfaces:** report renders source/context byte metrics and original-intent provenance; local real-case capsule is outside the committed tree.

- [ ] Add report behavior tests for projection metrics and explicit byte-versus-token wording; run red before implementation.
- [ ] Implement report metrics and document capture, provenance, probe and adoption limits.
- [ ] Capture the actual local wardrobe app and host-owned keyboard checks. Probe before dispatch. Run A/B/C within a $2 total stop budget; do not predetermine which workflow wins.
- [ ] Verify raw receipts, exact original hash, protected embedded data and both viewport outcomes. Keep images/session text private.
- [ ] Run full tests, build/install, offline demo, desktop/mobile report checks and public-archive privacy scan. Commit release evidence.
- [ ] One fresh independent review; reproduce/fix Important findings and retain minor/scope decisions in the review record.

## Authorized execution

The user explicitly asked to keep progressing after the v0.1 prototype. This is the next implementation slice of that same goal, not a new approval request. Work remains in the dedicated repository on `feat/real-project-capture`; the v0.1 branch is retained. Code/test snippets live in executable tests rather than duplicate code in this plan.
