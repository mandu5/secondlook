# A real 120 MB app, with 14.8 KB of source context

Date: 2026-10-07. Second Look v0.2. One existing private standalone catalog, one trial per workflow. This was an existing artifact with a reproduced bug, not a deliberately broken fixture. The public demo remains synthetic.

The app embeds images and JSON in a single **120,410,551-byte** HTML file. A free baseline probe found that saving a favorite with Space rebuilt the grid and lost keyboard focus. As a result, pressing Space again could not toggle the same favorite off. The desktop and narrow-viewport focus checks failed; seven preservation checks passed.

## What ran

The original human request was selected from a local coding-agent JSONL log. Its physical line number, request hash and whole-session hash were retained in the private capsule. Recorded session model hints were not promoted into historical artifact attribution: A's authoring model remains **unknown**. The new revisit scope was explicitly limited to keyboard focus, with the existing catalog, data and offline behavior preserved.

An `html_scripts` projection selected **14,829 UTF-8 bytes** of executable source, including boundary labels. The whole HTML ran locally. The model could edit only the selected script; HTML, CSS, JSON and images were protected. The full prompts were 17,903 bytes for B, 2,331 bytes for C's brief, and 20,674 bytes for C's implementation. Neither embedded image payloads nor acceptance-check definitions appeared in those prompts.

This is **source-byte exclusion, not measured token savings**. No counterfactual run sent the complete file to a model. Actual provider token use appears below.

Ten acceptance checks were frozen before model calls. They covered initial cards, saved state, desktop and narrow-view keyboard focus, repeated Space, reload persistence, the favorites view, inventory count, Escape, and focus inside a detail dialog. Each check used a fresh browser context; A/B/C shared the same harness and corresponding viewports. Three cases were marked held out; no check definitions were sent to either workflow.

## Measured outcome

Requested model: `sonnet`. All three receipts resolved to **`claude-sonnet-5-5`**, through Claude Code 2.1.289. Python 3.11.9, Playwright 1.63.0, Chromium 153.0.8010.12, macOS on ARM64. The total stop budget was $2 API-equivalent, with $1 per workflow; C used two calls within its allowance.

| Arm | Passed | New passes | Regressions | Reported tokens | API-equivalent USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| A: existing artifact | 7/10 | — | — | 0 new | $0 new |
| B: ordinary revision | 10/10 | 3 | 0 | 9,634 | $0.0413280 |
| C: intent brief, then revision | 10/10 | 3 | 0 | 13,756 | $0.0620656 |
| Total | — | — | — | **23,390** | **$0.1033936** |

Tokens include new input, output and cache reads/writes. Both C calls count. Dollars reconcile to raw provider receipts and are API-equivalent estimates, not subscription invoice charges. A's original creation cost is unknown.

**Both workflows repaired the three captured failures. The ten frozen checks measured no extra functional gain from reframing, which cost more.** That conclusion is limited to the original checkset.

## A coverage gap found after the experiment

Reviewing the candidates revealed that C also handled the focused card disappearing from the favorites view, while B only restored focus if the same heart still existed. This exposed a gap in the original checks. Two additional behavior checks were written **after seeing the candidates** and run against the saved A/B/C copies, with zero additional model calls.

| Post hoc check | A | B | C |
| --- | --- | --- | --- |
| Remove the only favorite without dropping focus to BODY | Fail | Fail | Pass |
| Remove the first of two favorites and focus the remaining favorite | Fail | Fail | Pass |

No browser page errors occurred. These are real additional behavior differences, but **exploratory, post hoc evidence**: they were not specified before generation and cannot be folded into the original 10-check workflow verdict. No model was rerun or given these new checks. This suggests a hypothesis for a fresh, preregistered trial; it does not establish that reframing generally produces better work or caused the difference in this one sample.

The product lesson is sharper than a tied score: **old acceptance checks can preserve old blind spots too.** Keeping checks fixed makes comparison fair but does not make coverage complete. A future workflow should preserve regression checks and independently propose new intent-based checks before seeing candidate implementations. Check provenance and timing matter as much as source provenance.

## Integrity and limits

The original file's SHA-256 was unchanged. Every protected region outside the selected script matched across A, B and C. Browser evaluations reported no page errors or blocked network requests. Candidate copies and selected-code diffs remain available locally; the original app was not overwritten.

The private capsule, original request, app, screenshots and receipts are not committed. The public [aggregate JSON](real-case.json) records outcomes, environment and context sizes without the user's images or request text. The main HTML report preserves the original ten-check comparison; the exploratory results are a separate local evidence record. Raw evidence is available to the owner in their local run directory.

This is one integration case, not a user study, performance benchmark, old-versus-new-model experiment or general workflow comparison. Passing UI checks says nothing about catalog recommendation quality. Unchecked behavior can still be wrong; candidate adoption requires review. No change was automatically applied to the original artifact.
