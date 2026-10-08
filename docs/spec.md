# Second Look v0.1

Revisit old AI work when a model changes. Start with original intent, select a bounded task, and show what actually changed.

This release supports small static web apps. A capsule contains user intent, provenance, known failures, assumptions, capability triggers, an explicit source allowlist, and independent browser checks. The tool never infers an unknown historical model identity. The included feedback app is deliberately flawed synthetic data, not evidence about an older model.

`init` creates an editable capsule. `plan` ranks capsules by declared failure impact and capability overlap and selects within a budget, without model calls. `run` freezes source and checks and evaluates A (saved artifact), B (ordinary improvement) and C (intent-first reframe then improvement). B and C receive equal maximum budgets and the same model, intent and failure evidence. C's first call cannot see legacy source. A-to-C measures artifact change; B-to-C measures this workflow on these checks, not pure model uplift. `demo --offline` uses an explicitly labeled reference repair. Live demo uses the authenticated Claude CLI.

Python >=3.11; core uses the standard library; browser evaluation uses Playwright Chromium. Model tools, project instructions, plugins, hooks and MCP are disabled. The model returns exact text edits; only the host writes copies of allowlisted source. Source symlinks, path escapes and secrets are refused. No original source modification, automatic adoption, deployment or public publication. Browser checks are host-owned, outside candidate source; candidate browser requests are restricted to the local static origin. This is not an OS sandbox for arbitrary repositories. Only inspect apps you trust to execute in a browser.

Cost is provider-reported API-equivalent USD, not a subscription invoice. Native per-call budget limits are best effort and may overshoot by an in-flight response. Never report missing cost as zero. Journal before dispatch; unknown remote outcomes stop the run without retry. Include failed calls in totals. Each run is fresh: do not reuse model outputs across models. Fingerprint source, acceptance, harness, provider version, requested and resolved model, prompts and environment in evidence. Cap source context, use exact patches, preflight probes, and skip model calls when all existing checks pass (unless explicitly forced).

Report functional improvements/regressions, actual token usage, dollar-equivalent cost, individual browser timings (not a benchmark), identical-view screenshots, and a unified source diff. Verdict never depends on a model grading its own work. Missing or failed evaluation means inconclusive, never improvement. Green tests are evidence of checked behavior, not complete correctness. Reframing may cost more without improving results, and the report must say so.

Completion: installable CLI, offline demo, real authenticated A/B/C run with receipts, immutable tests, source unchanged, readable desktop/mobile report, passing automated tests, independent review and documented limits. Public repository creation remains a separate publishing action.

