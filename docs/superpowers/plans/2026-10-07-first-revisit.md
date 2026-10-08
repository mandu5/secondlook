# First Revisit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver an executable, evidence-based A/B/C revisit for a small web app.

**Architecture:** A local Python CLI freezes allowlisted source and declarative browser checks. A tool-free Claude adapter returns anchored edits to isolated copies; a host evaluator produces a standalone HTML report.

**Tech Stack:** Python 3.11+, argparse, pytest, Playwright, Claude Code CLI.

**Spec:** `docs/spec.md`

## Global Constraints

- No original source modification, automatic adoption, deployment or public publication.
- Cost is provider-reported API-equivalent USD, not a subscription invoice.
- Never report missing cost as zero.
- Each run is fresh: do not reuse model outputs across models.
- Missing or failed evaluation means inconclusive, never improvement.
- The included feedback app is deliberately flawed synthetic data, not evidence about an older model.

## Review Focus

- Path traversal, symlinks and private configuration must not enter prompts or candidate writes (Task 1).
- Malformed, interrupted or failed provider responses must preserve receipts and stop on unknown cost (Task 2).
- Host-owned checks must not be editable by the candidate; evaluation failure must not become improvement (Task 3).
- Model aliases, mode, acceptance and source changes must change evidence identity (Tasks 1, 2, 3).
- Untrusted text and screenshots in reports must be inert; offline results must not look like real model results (Task 4).

### Task 1: Capsule and bounded planner

**Files:** `pyproject.toml`, `src/secondlook/core.py`, `tests/test_core.py`.

**Interfaces:** `load_capsule(path: Path) -> dict`; `source_bundle(capsule: dict) -> dict[str,str]`; `fingerprint(value: object) -> str`; `apply_edits(root: Path, edits: list, allowed: list[str]) -> None`; `plan_capsules(paths: list[Path], capabilities: set[str], budget: float) -> list[dict]`.

- [x] Write behavioral tests for traversal/symlink rejection, atomic anchored edits, content-sensitive identity and budget selection.
- [x] Run `python3 -m pytest tests/test_core.py -q`. Expected: import failure before implementation.
- [x] Implement validation and copies using resolved relative paths, SHA256 canonical JSON, exact single-anchor patches and a deterministic score.
- [x] Run `python3 -m pytest tests/test_core.py -q`. Expected: all pass.
- [x] Commit `feat: add revisit capsules and bounded selection`.

### Task 2: Tool-free provider and journal

**Files:** `src/secondlook/provider.py`, `tests/test_provider.py`.

**Interfaces:** consumes Task 1 fingerprints. `ClaudeProvider.call(prompt: str, schema: dict, budget: float, receipt: Path) -> dict` returns normalized output, actual model IDs, usage, API-equivalent cost and receipt path. `ProviderError` carries known/unknown cost. `Budget` reserves per-arm allowances and accounts for failed calls.

- [x] Write tests using an executable fixture at the process boundary: success, malformed receipt, nonzero exit with known cost, timeout, disallowed tool flags, unknown-cost fail-closed budget.
- [x] Run `python3 -m pytest tests/test_provider.py -q`. Expected: import failure before implementation.
- [x] Implement subprocess argv, stdin prompts, timeout termination, dispatch-before-call journal and atomic receipts; disable automatic retries.
- [x] Run `python3 -m pytest tests/test_provider.py -q`. Expected: all pass.
- [x] Commit `feat: add bounded Claude calls with durable receipts`.

### Task 3: Immutable browser evaluation and workflow

**Files:** `src/secondlook/evaluate.py`, `src/secondlook/runner.py`, `tests/test_workflow.py`, `examples/feedback/`.

**Interfaces:** consumes capsule, source, provider. `evaluate(root: Path, checks: list, output: Path) -> dict`; `run(capsule_path: Path, output: Path, model: str, budget: float, mode: str, offline: bool, force: bool) -> dict`. Result JSON records A/B/C evidence, verdict, receipts and unchanged-source hash.

- [x] Write integration tests against a tiny static app: baseline failure, repair pass, regression verdict, untouched source, frozen checks, budget preflight and passing-baseline skip.
- [x] Run `python3 -m pytest tests/test_workflow.py -q`. Expected: import failure before implementation.
- [x] Implement local-only static browser evaluation, hidden checks, two-phase reframe, equal arm caps and evidence journaling. Add synthetic demo app, independent checks and offline reference patch.
- [x] Run `python3 -m pytest tests/test_workflow.py -q`. Expected: all pass.
- [x] Commit `feat: compare saved ordinary and reframed artifacts`.

### Task 4: CLI, report and real verification

**Files:** `src/secondlook/cli.py`, `src/secondlook/report.py`, `tests/test_cli.py`, `README.md`, `README.ko.md`, `LICENSE`, `.github/workflows/tests.yml`, `docs/validation.md`.

**Interfaces:** CLI invokes Tasks 1-3 and writes report via `write_report(result: dict, output: Path) -> Path`. `secondlook demo --offline --output PATH` requires no model access; live demo invokes installed authenticated Claude Code.

- [x] Write subprocess CLI tests for offline report and invalid options, plus inert report content and explicit reference labeling.
- [x] Run `python3 -m pytest tests/test_cli.py -q`. Expected: failure before CLI implementation.
- [x] Implement CLI and responsive standalone report. Document install, capture, selection, run, interpretation and limits.
- [x] Run full pytest suite, build wheel, install into clean environment and execute offline demo. Expected: all pass and eight checks measured, without original changes.
- [x] Run live `secondlook demo --model sonnet --budget-usd 2 --output .secondlook/live`; inspect actual A/B/C costs, screenshots, verdict and raw receipts. Expected: honest completed or inconclusive result; no predetermined winner.
- [x] Render report at desktop/mobile widths and verify errors/overflow. Commit `feat: ship CLI and verifiable comparison report`.
- [x] Fresh independent whole-branch review, fix important findings with regression tests, record final evidence.

## Execution decisions

The user approved the researched direction and explicitly said to continue. Work proceeds inline without a second plan approval. The new dedicated repository on `feat/first-revisit` is already isolated; a second worktree adds no separation. The test snippets live in the task's test files to avoid maintaining duplicate executable specifications in this document.
