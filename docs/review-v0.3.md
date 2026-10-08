# v0.3 final review and decisions

The implementation uses a dedicated local branch, `feat/model-aware-revisit`, from `bffbd6c`. One fresh-context reviewer inspected `bffbd6c..f4479bf` read-only. No reviewer called a model API. The corrected implementation is `c2b4db9`.

## Findings and verification

All three findings were accepted as Important. No Critical or deferred Minor findings were reported.

1. **Incomplete/mismatched evidence could release the uncertainty barrier.** Bind each run to the frozen attempt key, capsule, source, checks, requested model, workflow, harness and environment. Require a unique receipt set matching every dispatched call, terminal accounting, consistent finite costs and truthful usage completeness. Preserve interruption independently of source-change detection. Regression includes an actual local fake CLI subprocess interrupted after response parsing while the source changes; it cannot become a zero-cost success.
2. **A hash did not preserve the original artifact.** Harvest now stores compressed source objects by content hash, deduplicates unchanged contents and records them in immutable revisions. Restore validates all object hashes and the complete artifact identity before writing a new directory. Tests delete the original and recover identical bytes; corrupt blobs cannot be restored.
3. **Report errors duplicated accounting during reconciliation.** Append each attempt summary once and handle report rendering separately. A report path occupied by a directory no longer doubles task rows or keeps financially settled evidence blocked.

Eleven regression cases failed before the fix pass. The complete suite after the single fix pass passed: **145 tests, 72.28 seconds**. No second reviewer or review loop was used. Live validation and clean installation are recorded separately in `verification-v0.3.json`.

## Rulings made during execution

- Preserve the existing dedicated repository and create a new feature branch from the clean prior version. No extra worktree was necessary; the previous branch remains available.
- Continue from the user's explicit correction and authorization without another design-approval pause. The original goal is the problem portfolio, not the wardrobe case.
- Keep uncertain/interrupted campaigns blocked until matching terminal evidence can be reconciled. No lease expiry or automatic replay; some cases still require operator investigation.
- Supplement system TLS trust with certifi because this Python installation had no configured CA bundle. Certificate verification remains enabled; the cost is one dependency.
- Preserve pricing-tier time conditions as opaque catalog metadata. Catalog prices never become actual-spend receipts; the live inventory contained 465 models.
- Preserve compressed originals instead of hashes alone. This adds disk and IO, not model tokens, and permits actual recovery after deletion.
- Retain the first live verification as evidence for its own harness revision, then verify the corrected receipt path within the overall $2 API-equivalent development stop budget. Include both verification campaigns in total development usage.
- Keep the branch and release artifacts local. Publishing, pushing and outreach are outside this turn's executed scope; no publication approval was requested as a prerequisite for completing local work.

## Reviewer exclusions resolved

Live model results and clean-install checks were assigned to the implementer and are included in the verification record. General model superiority, representative product demand and historical old-versus-new causality are not claimed. Backend/repository execution remains explicitly unsupported. The OS lock targets the documented macOS/Linux environment; Windows compatibility is not claimed.
