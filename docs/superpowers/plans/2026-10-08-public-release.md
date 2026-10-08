# Public release implementation plan

Spec: `docs/spec-v0.5.md`. Base: `1ae64b9`. Execution: inline, one final independent
review. The user's repeated instruction authorizes proceeding without spec/plan
checkpoints. Work stays in the existing dedicated feature checkout.

## Global constraints

Preserve original sources and private evidence. Zero model calls for the new
onboarding/export features and CI. Use existing measured trials with accurate
scope. Public artifacts must exclude private history and receipts. Do not claim
SOTA. Do not invent acceptance criteria from an old implementation.

### Task 1: First-use experience and stopped comparison rows

Files: `src/secondlook/cli.py`, `diagnostics.py`, `runner.py`, `tests/test_release_cli.py`.
Produces: real browser diagnostic; explicit owner-authored text criteria and
independent brief in a valid capsule; no JSON required for simple text behavior.
Consumes: existing capsule validation, browser harness, provider preflight.

1. Write tests for CLI criteria that exercise a real failing baseline, draft and
   confirmed intent, independent brief, invalid/no-overwrite behavior, doctor
   success/missing browser, and skipped budget rows. Run targeted tests.
   Expected: new flags/command and missing rows fail against the existing code.
2. Implement the smallest compatible extension. Run targeted tests.
   Expected: passing checks and failures describe real behavior, not a mock CLI.
3. Commit with evidence in the ledger. Defer the full suite to the final gate;
   repeat broad tests only after substantive fixes.

### Task 2: Portable sharing without private source

Files: `src/secondlook/sharing.py`, `cli.py`, `tests/test_sharing.py`.
Produces: standalone HTML and a JSON summary; metrics-only default, explicit
intent/screenshot opt-ins. Consumes: result format and existing report renderer.

1. Tests put private markers into every free-form source/result surface, assert
   their absence from default exports, test uncertainty, HTML escaping, screenshot
   confinement, malformed numbers and no-overwrite. Expected: missing command.
2. Whitelist public fields, normalize check identities, validate optional PNGs,
   render from sanitized data, write to a fresh destination. Run targeted tests.
   Expected: no marker leak, no external image read, meaningful evidence retained.
3. Commit; record renderer/export interface decisions in ledger.

### Task 3: Public documentation and demonstration

Files: README EN/KO, docs guides/release evidence, community templates, `site/`,
CI, package metadata. Consumes: tasks 1/2 command contracts and prior live trials.

1. Rewrite onboarding around no-key demo, own-app capture, measured comparison,
   and share. Move advanced CLI details to a reference. Supply runnable examples.
2. Build a responsive static public site and generate the synthetic demo with the
   actual offline engine and share exporter. Expected: zero model calls; 3/8 to 8/8.
3. Verify mobile/desktop, keyboard interactions, links and console with Chromium;
   visually inspect screenshots. Human prose/config gets review, not mirror tests.
4. Commit. Include research overlap and explicit unsupported capabilities.

### Task 4: Verify, review, package and publish

Consumes: tasks 1–3, public snapshot. Produces: public repo/release/Pages URLs.

1. Run the full pytest suite; build wheel/sdist, install in a new venv outside the
   checkout and exercise documented doctor/demo/init/probe/share flow.
2. One fresh independent final review (including publication/privacy boundary).
   Fix Important/Critical findings in one RED→GREEN pass; record minor deferrals.
3. Scan the exact tracked release files; publish a clean public history using a
   GitHub noreply identity, preserving the local development history. Create the
   public repository, push a tagged release, upload distributions and checksums,
   enable GitHub Pages, and verify actual CI and HTTP results.
4. Record exact verification, public URLs and limitations. Archive private ledger
   and remove only this plan's scratch. No social/email outreach.

## Review Focus

- Default export must not carry arbitrary nested strings, raw checks or local
  paths; tests inject markers into all known result surfaces.
- PNG export must not follow paths outside the result directory or oversized
  files; tests cover escaped paths and missing screenshots.
- Unknown usage and skipped/harness outcomes must not become zero/success;
  targeted tests cover each state.
- New init flags must validate before leaving a usable capsule and never replace
  an existing file; end-to-end tests exercise the produced capsule.
- Distribution and public git history must exclude private receipts/identities;
  audit the actual published tree and remote history, not only ignore rules.
