# v0.2 independent review and fixes

One fresh reviewer inspected `0c1f420..49fc129`, read-only, with targeted Python and Chromium reproductions. No paid model calls or private raw-session/image inspection were made by the reviewer. The reviewer initially marked the branch not ready: three Important findings and one Minor. The executor regraded the malformed-record finding Important because a single corrupt record blocked access to valid later requests, a core import workflow.

## Fixed in one regression-tested pass

1. **Edits could expand their own permissions.** A first edit could change HTML parsing boundaries and allow a second edit into originally protected JSON. `apply_edits` now fixes editable regions from the original snapshot, adjusts only their offsets through replacements, verifies the final partition and compares protected segments before writing any file. The sequential delimiter-injection reproduction and the single boundary-changing edit are both rejected atomically.
2. **HTML classification could expose protected text.** Raw-text/RCDATA elements now keep nested-looking tags as text, `noscript` follows the evaluator's scripting-enabled behavior, and duplicate attributes retain the first value. Ambiguous syntax is rejected. A Chromium comparison confirms the textarea, noscript and duplicate-type reproductions expose only the actual executable script.
3. **Generated or non-user text could appear as original intent.** `isCompactSummary` records and contradictory explicit nested roles are excluded and cannot be selected as human requests. Legacy user records without a nested role remain supported.
4. **Malformed records could abort import.** Invalid content-block shapes and invalid Unicode in content or metadata are counted as malformed and skipped. Later valid requests keep their actual physical line number. The existing bounded reader and whole-source hash remain intact.

Each reproduction failed before its fix. The final full suite passed **107 tests**, zero failures, in **41.43 seconds**. The author verified the fixes; no second reviewer was dispatched, so this is not a separate independent sign-off on the fix commit.

Saved real-case B/C edit recipes were re-applied with the fixed validator. Their resulting full files matched the original live candidates exactly, and the original source identity stayed unchanged. The selected human request was revalidated from an exact record snapshot whose record/text hashes matched the original capture. A direct reread of the still-changing session log was correctly refused; no claim is made that the whole active log remained immutable.

## Decisions and costs

- Continue in the clean dedicated repository on a feature branch, retaining v0.1. Integration remains a later local, reversible decision.
- Limit the real case to keyboard behavior. Its checks cannot assess clothing suitability or recommendation quality.
- Use selected-code display diffs and exact-edit JSON for projected files. The display diffs cannot be applied to the whole artifact with `git apply`; complete candidate copies remain available.
- Keep removal checks discovered after seeing candidates separate from the frozen experiment. They show additional behavior, but a fresh trial is needed for a preregistered comparison.
- Reject unsupported SVG/MathML, template, plaintext, self-closing raw-text and script-escape constructs in script-only projection. Some otherwise valid HTML needs an explicit source allowlist; unsupported input is not silently classified.
- Retain existing behavior classification for scalar assertions that match multiple DOM elements. Duplicate app elements can be a genuine failure; an overly broad authored selector can also appear as a behavior failure. Use the free probe and inspect the check before spending.
- Historical authorship, general workflow superiority, adoption and catalog quality remain outside the evidence. Model hints and passing checks cannot establish those claims.
- Private raw experiment data was verified by the implementing agent, not independently reauthenticated by the reviewer. Public evidence is aggregate-only; this is a limit on independent validation, not a claim of an externally replicated experiment.

No new minor findings remain deferred after regrading and fixing malformed-record handling. The historical v0.1 review is recorded separately in [review.md](review.md).
