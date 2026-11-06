# Public site: selected A implementation

The homepage is the native static site in `site/index.html`, `site/home.css`, and
`site/app.js`. The existing Pages workflow still uploads `site/` directly. This
change does not deploy the site or change that workflow.

The branching composition follows the approved 6 November 2026 Second Look A
study. It is ordinary HTML, CSS, SVG, and JavaScript; the study's chooser,
feedback panel, and iframe shell are not included. The existing `site/style.css`
is retained for the pilot page, so its content and presentation remain intact.

## Source of the eight checks

`site/assets/demo-checks.json` joins the check definitions in
`src/secondlook/demo/capsule.json` with the exported results in
`site/demo/summary.json`. The export anonymizes IDs as `check-1` through
`check-8`; the join follows that existing order and records the exported ID.

The original passes **initial, priority, reset** (3/8). The hand-authored
reference passes all eight. These are synthetic offline artifacts; no model
performance or additional participant result is implied.

Refresh or check this committed snapshot without running an evaluation:

```sh
python3 scripts/build_site.py
python3 scripts/build_site.py --check
python3 -m http.server 19303 --bind 127.0.0.1 --directory site
```

## Preserved navigation and actions

| Before | Now | Destination / behavior |
| --- | --- | --- |
| Explore the no-key demo | Inspect the comparison; original label also in “How a Second Look works” | `demo/` |
| Try it locally | Get started in navigation; original label also in the workflow section | `#start` |
| Logo with circle mark | Second Look wordmark | `./` |
| Job Radar / UGV-MON select | Two case buttons | Same recorded costs, tokens, calls, report links |
| B / C / D workflow buttons | B / C / D workflow buttons | Same recorded values and selected-workflow explanation |
| Copy commands | Copy commands | Same installation commands, clipboard fallback |
| Import example | Inspect the import example | `import-demo/` |
| Exported trial metrics | Inspect the exported trial metrics | `evidence/job/`, `evidence/ugv/` |
| User pilot | Pilot in navigation and existing closing action | `pilot/` |

All existing main-page sections, CLI commands, documentation, research,
license, language, and feedback links remain available. The former hero's
workflow explanation remains under “How a Second Look works”. The saved demo,
import report, trial exports, and pilot files are unchanged.

The design inventory compares names rather than destinations. Its
`lost-in-redesign` warning is allowed only for the wordmark and moved/renamed
hero links above. Its field warning maps the old `#case` select to the two case
buttons. The new title is the user's selected A title. Short display headings
retain their approved tight line spacing; paragraphs keep normal reading
spacing.

## Provenance and licenses

The selected study was composed using Design Studio's approved reference
materials, including KLOD (focus/depth), meetee (time/flow), and comparison
typography references. The user confirmed personal GitHub reuse authorization
on 5 November 2026. That provenance is retained; the reference collection is not
relicensed as original MIT material here. This implementation imports no
reference application runtime or third-party animation library.

Local fonts are Pretendard 1.3.9 and Archivo Variable (Fontsource 5.3.0). Their
unaltered SIL Open Font License notices are in `site/assets/fonts/`. Project
code and original demo artifacts retain the repository's existing license.

To revert the design, revert its implementation commit. The package, CLI,
recorded reports, and pilot do not require migration.
