# Second Look v0.2 — bring a real old artifact

The v0.1 workflow works on a synthetic fixture but cannot accept a real self-contained app with embedded photos: it treats the whole file as model context. A read-only browser probe of an existing local wardrobe app (120,410,551 bytes) also reproduced a real keyboard bug: pressing Space on a favorite button recreates the grid, leaving focus on BODY. This release must demonstrate a real task without uploading the embedded images or changing the original artifact.

## Required behavior

1. Separate runtime snapshot from selected model context. Retain the complete allowlisted artifact for local execution. An explicit `html_scripts` projection supplies only executable inline JavaScript; JSON data scripts, HTML and CSS are read-only in this mode. Unprojected files retain the 64 KiB total context cap. Total runtime source is capped at 256 MiB. No general asset-directory traversal or arbitrary repository execution.
2. Exact edits can only target the selected regions. Validate all edits before writing any candidate file. Original bytes, protected regions and source hashes remain intact. Diff output must not include opaque image/data payload as context. Record runtime bytes, selected UTF-8 context bytes, hashes and the projection policy; byte reduction is not measured token savings.
3. Capture a runnable draft capsule from an HTML file and a checkset, with either supplied intent or an explicitly selected human request from a local session. Extract Claude/Codex user text only, preserve line/source/hash provenance, skip tools and environment/agent-instruction wrappers, never execute logs. No scanning all private histories by default, no model calls for capture. Imported intent remains unconfirmed until the caller explicitly confirms it. A recorded model hint never proves who produced the final artifact.
4. Add keyboard actions (`focus`, `press`) and focus/attribute assertions to frozen browser checks. Support viewport per check and `reload` for persistence checks. Add a free `probe` command that evaluates A only; no model dispatch even when baseline fails. Capsule, artifact and harness errors stay distinct from functional failures.
5. Run the real focus failure through A/B/C with a total $2 API-equivalent stop budget. Record exact cost, tokens, real model IDs, preserved source, context reduction, outcomes and uncertainty. The full private app and its images stay in ignored local output; public documentation uses aggregate observations only.

## Non-goals and limits

No historical-model attribution without evidence, no automatic adoption, no clothing/fit conclusions from UI checks, no public upload of the private case, no arbitrary hostile-code OS sandbox. Existing v0.1 capsules and demo remain supported. A real legacy-app case validates an integration; it is not a user study or proof of market demand.

## Success

Capture/inspect/probe/run/report can handle the real 120 MB HTML file using less than 64 KiB of selected source. The baseline failure is reproduced before model calls; a candidate's independent checks and source preservation are verified. Automated tests cover region escapes, non-executable script classification, malformed sessions, provenance, large payload omission and keyboard behavior. Build/install verification and one fresh independent review finish the release.
