# Validation record — 2026-10-07

The v0.2 [real-project case](real-case.md) adds a 120.4 MB existing app: a free probe reproduced three keyboard failures, and real model revisions both reached 10/10 checks. The experiment used 23,390 reported tokens and $0.1033936 API-equivalent. Full images stayed local; selected source was 14,829 bytes. The v0.1 record below remains historical evidence, separate from the new case.

## v0.2 verification

- Full suite: **107 passed**, zero failures, 41.43 seconds after the [independent review fixes](review-v0.2.md). The pre-review suite had 86 tests. New browser tests cover draft probes, source projection, focus, keyboard actions, reload persistence and per-check viewports. No test calls a paid model.
- Built v0.2 wheel and installed into a new environment; verified the import came from its site-packages. The installed CLI completed the offline demo with A=3/8, R=8/8 and zero model calls.
- The real-case HTML report passed desktop (1440px) and mobile (390px) checks: no page errors or document overflow; filters, image enlargement and state selection worked. Both screenshots were visually inspected.
- All three real model receipts reconciled to $0.1033936. Full original bytes and all protected regions matched. A separate, explicitly post hoc browser probe found two removal cases that C passed and A/B failed, with no extra model calls. These were not folded into the original ten checks.
- Saved real-case edit recipes were re-applied under the fixed region validator and yielded byte-identical candidates. Original request eligibility was revalidated from its exact captured record. No additional paid calls were needed after review.

## v0.1 live model experiment

Command: `secondlook demo --model sonnet --budget-usd 2 --output .secondlook/live`.

The input was the project's deliberately flawed synthetic feedback app. No historical model generated the baseline. The repair candidates came from real authenticated Claude Code calls, without shell/file/browser tools. This is a workflow demonstration, not evidence that a new model outperforms a particular older model.

Provider: Claude Code **2.1.289**. Requested alias: `sonnet`. All three provider receipts report actual model ID **`claude-sonnet-5-5`**. Date: 2026-10-07. Raw receipts, prompts, frozen capsule, app copies and browser results are stored locally in the ignored `.secondlook/live/` directory.

| Arm | Checks passed | Regressions vs A | Reported tokens | API-equivalent USD |
| --- | ---: | ---: | ---: | ---: |
| A: saved synthetic fixture | 3/8 | — | 0 new model tokens | $0 new model spend |
| B: ordinary improvement | 8/8 | 0 | 4,373 | $0.0198400 |
| C: intent-first reframe | 8/8 | 0 | 7,705 | $0.0366376 |
| Experiment total | — | — | 12,078 | **$0.0564776** |

Reported tokens sum new input, output, cache-read input and cache-creation input. Reframing and implementation both count toward C. Dollar values use the CLI's API-equivalent estimate, not a subscription invoice. A's original creation cost is unknown; its zero here means no model call was made to evaluate the saved artifact.

Five prior failures passed after each repair: lowercase search, visible-only export, CSV quote/newline preservation, mixed-case whitespace search, and empty-result export. Initial rendering, priority filtering and reset continued to pass. Two check inputs were held out of model prompts. The original source fingerprint was unchanged after the experiment.

**Finding:** B and C achieved the same checked behavior. C used more tokens and cost more. There is no measured functional advantage from the reframe phase in this trial. Do not extrapolate from this single simple task to more ambiguous projects.

## Verification performed

- `python -m pytest -q`: **55 tests passed after independent review fixes** (30.23 seconds). This includes real browser integration and executable provider fixtures. Paid calls are not part of the test suite. The pre-review suite had 36 tests; the added cases reproduce malformed responses, missing usage, invalid checks and mismatched experiment caps.
- `python -m compileall -q src`: passed.
- Built a wheel and installed it into a separate environment. The installed executable ran the offline demo with A=3/8 and reference R=8/8, zero model calls and an HTML report.
- Inspected the generated report in Chromium at 1440px and 390px widths. No page errors or body overflow. Changed filter showed five cases, holdout filter showed two; image enlargement and screen-state switching worked.
- Visually inspected desktop and mobile screenshots. The report displays synthetic provenance, real model identity, costs, no measured B/C gain, and matching-state screenshots.
- Re-evaluated the three saved live artifacts with the final evaluator and Chromium 153.0.8010.12. A=3/8, B=C=8/8 again; source fingerprint unchanged; zero additional model calls. The original live evaluation used Playwright 1.59.0 / Chromium 147.0.7727.15, and all three arms shared that environment.
- Rebuilt the final wheel, reinstalled it into the separate environment, and repeated the offline CLI verification. An 18-second browser walkthrough is included in `docs/assets/demo.webm`.

[Independent review findings and decisions](review.md) document the four Important findings and their regression tests, the one deferred whitespace-only minor, and the retained scope boundaries.

## What remains unverified

No real-user pilot, cross-provider comparison, genuine old/new-model comparison, repeated trial or performance benchmark has been completed. CI is configured but has not run on a public GitHub repository. Linux/Windows runtime behavior has not been checked locally. General repositories and hostile JavaScript are outside this prototype's isolation boundary.

The screenshot in the README comes from this measured live run. Full local receipts are not committed because receipts can contain source and environment paths; future users should apply the same sharing boundary to their projects.
