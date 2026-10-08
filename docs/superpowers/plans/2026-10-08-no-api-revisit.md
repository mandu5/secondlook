# No-API Revisit Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one fresh whole-branch review.

**Goal:** Freeze one task, import external candidates, and compare measured behavior without a new API purchase.

**Architecture:** A request module owns immutable preparation/validation. An assessment module applies imported edits/rebuilds to copies and calls the existing browser evaluator. Existing report/export are extended with an explicit imported-evidence kind.

**Tech Stack:** Python >=3.11, standard library, existing Playwright, pytest.

**Spec:** docs/superpowers/specs/2026-10-08-no-api-revisit.md

## Global Constraints

- Python >=3.11; no new dependencies; no paid service or model calls.
- Imported model labels/cost/tokens are owner-reported, never provider-verified.
- 1–4 candidates; missing cost/tokens stay unknown; preserve original files.
- Existing v0.5 commands remain compatible; static browser artifacts only.

## Review Focus

- A moved request must work while a modified snapshot must fail (Task 1).
- User-supplied labels or JSON text cannot become executable HTML (Task 3).
- Duplicate content is reused evidence, never an independent repetition (Task 2).
- Missing/partial usage must never become a free-model claim (Tasks 2–3).
- Rebuild input remains source-blind and readonly inputs cannot be overwritten (Tasks 1–2).

### Task 1: Portable frozen request

**Files:** Create `src/secondlook/handoff.py`, `tests/test_handoff.py`.

**Interfaces:** `prepare_request(capsule_path: Path, output: Path, mode: str = "rebuild") -> dict`; `load_request(path: Path) -> tuple[dict, dict, Artifact]`; `read_json(path: Path, limit: int, fenced: bool = False) -> object`.

- [ ] Write tests for confirmed intent, source-blind rebuild, ordinary projections,
  relocation, tampered source/checks/prompt, traversal/symlinks, bounded strict JSON.
  Core example: prepare a confirmed rebuild with a `LEGACY_SECRET` sentinel;
  assert it is absent from `request.md`, move the directory, delete the original,
  and verify `load_request` still returns the saved source.
- [ ] Run `python -m pytest tests/test_handoff.py -q`; expect missing-feature failure.
- [ ] Implement snapshot creation, normalized capsule hash and response schema
  using the existing `capture_artifact`, `build_prompt` and `require_rebuild`.
  Use exclusive new-directory creation and bounded reads; validate hashes before
  loading the source; hard-code the snapshot root to `baseline`.
- [ ] Run the same test command; expect all pass, then commit Task 1.

### Task 2: Local assessment of external candidates

**Files:** Create `src/secondlook/assessment.py`, `tests/test_assessment.py`.

**Interfaces:** Consume `load_request/read_json`. Produce
`assess_responses(request_path: Path, responses: list[Path], labels: list[str], output: Path, usage: list | None = None) -> dict`.

- [ ] Write real-browser tests: baseline 1/2, one candidate 2/2, one candidate
  0/2 -> A_E1 improved, A_E2 regression; original bytes unchanged; all pairs.
  Test wrong request ID rejected before output, readonly edit fails per arm,
  duplicate response path rejection, duplicate content evidence reuse, unknown
  and partial usage, invalid counts/NaN, and bounded fenced responses.
- [ ] Run `python -m pytest tests/test_assessment.py -q`; expect missing-feature failure.
- [ ] Validate all envelopes and owner metadata, persist a running result, build
  candidate copies via `apply_edits/write_rebuild`, evaluate A/E1–E4, and save
  after each arm. Use actual full-source identity for within-batch reuse. Produce
  `imported_candidates` results compatible with the existing renderer.
- [ ] Run the same test command; expect all pass, then commit Task 2.

### Task 3: CLI, honest reports and portable sharing

**Files:** Modify `cli.py`, `report.py`, `sharing.py`; create `tests/test_import_cli.py`.

**Interfaces:** `prepare` calls Task 1, `assess` calls Task 2 then `write_report`;
  sharing allows A/E1–E4 only for imported results, omits user labels and keeps
  cost provenance. Existing commands and formats continue to work.

- [ ] Write CLI roundtrip tests with two frozen candidates and unknown cost;
  assert report says imported/user-reported, escapes malicious labels, and the
  shared report contains no labels/source/path, with unknown costs preserved.
- [ ] Run `python -m pytest tests/test_import_cli.py -q`; expect missing commands.
- [ ] Add parser/dispatch and imported report copy; use explicit kind-aware
  budget/token text and generic shared labels; preserve duplicate-evidence flags.
- [ ] Run `python -m pytest tests/test_import_cli.py tests/test_sharing.py tests/test_cli.py -q`;
  expect all pass, then commit Task 3.

### Task 4: Research, release and external verification

**Files:** Research/usage docs, README EN/KO, roadmap, changelog, site, version metadata.

- [ ] Save dated primary-source research and explain what changed the design.
- [ ] Document an executable prepare/assess/share workflow and the manual external
  generation boundary. Add a clearly hand-authored public import demo.
- [ ] Run full pytest, compileall, build distributions and install the wheel in a
  clean venv; run actual prepare/assess/share commands from outside the repo.
- [ ] Verify desktop/mobile report interactions and sanitization. Commit, request
  one independent review, address material findings with reproducing tests.
- [ ] Publish source/tag/assets and verify anonymous downloads and CI. Reconcile
  free-hosting authorization separately; do not claim a new URL before verification.

## Preflight

Tasks 1→2 share the validated capsule/artifact tuple; Task 2→3 share the existing
result shape plus the new kind and declared metadata. The spec is authoritative.
No new arbitrary-code adapter or autonomous external model dispatch is included.
