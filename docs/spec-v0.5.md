# First public release: Second Look 0.5

The outcome is an installable, documented open-source release with a public URL
and a no-key demonstration. A local archive alone does not meet this release.
The owner has requested continuous execution through a shareable finished result.

## User experience

1. Open the public demonstration before installing anything.
2. Install a tagged release, diagnose Chromium and optionally Claude CLI, then
   run the offline example without credentials or model calls.
3. Capture a trusted static app with the original request and explicit text
   acceptance criteria from CLI arguments. No JSON authoring is needed for this
   narrow case. Draft intent remains the default. Advanced actions and fixtures
   continue to use capsules. No criteria are inferred from the old implementation.
4. Probe for free, then explicitly request a bounded comparison. An independent
   brief plus intent and preservation checks unlocks all three workflows.
5. Export a portable comparison with metrics only by default. Source, prompts,
   local paths, private labels, detailed errors and expected inputs do not travel
   with it. Intent text and screenshots require explicit export options.

## Release contract

- `doctor` performs a real Chromium launch and no model request. With
  `--provider`, it checks CLI support but makes no authentication/model claim.
- `init` accepts repeated `--expect-text SELECTOR TEXT` and
  `--preserve-text SELECTOR TEXT`, `--brief-file`, and `--confirm-intent`.
  Invalid inputs leave no capsule; existing files are never overwritten.
- `share RESULT --output DIR` writes `index.html` and `summary.json` from a
  whitelist. Unknown cost/tokens remain unknown. Broken/inconclusive/skipped
  evaluations stay so. User labels are escaped. Optional PNGs must be confined
  to the input run directory, bounded in size, and embedded for portability.
- Stopped arms appear in all relevant comparison rows as inconclusive.
- The public site includes a labeled synthetic reference demonstration and
  measured live-case evidence with its protocol limits. It works on mobile,
  with keyboard navigation, without accounts or external scripts.
- A clean environment installs the wheel, runs doctor and the offline demo,
  and exports/opens the result. CI covers supported Python/Linux combinations
  plus macOS. No CI job requires a model key.
- Publish a reviewed snapshot with a tagged GitHub release, downloadable wheel,
  source and checksums, and a live GitHub Pages demonstration. Exclude private
  run directories, raw provider receipts and private git author email history.

## Position and boundaries

This is a beta release of a narrow, usable product. SOTA, uniqueness, market
demand, token savings and causal model uplift require evidence beyond this
release. Existing evaluation tools already compare outputs and cache requests.
Second Look connects preserved intent, budgeted revisit selection and alternative
implementation workflows. The first execution adapter remains trusted static
HTML/CSS/JS. Claude CLI is the only live provider. General records can be parked.
No source is automatically adopted, no model is called on release detection, and
no outward promotional messages are sent as part of publishing the repository.
