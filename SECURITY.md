# Security and data boundaries

Use trusted static apps. Chromium request blocking is not an OS sandbox for
hostile JavaScript. The runner does not execute package scripts, shell commands
from projects, backends or arbitrary repositories. The model receives explicitly
selected text and has no tools. An allowlist does not detect secrets in that text.

Source snapshots, prompts and full reports can contain private information.
`.secondlook/` is ignored by git. `share` exports a whitelist of metrics by default;
intent text and screenshots require explicit options and may reveal private data.
No telemetry is collected and no report is automatically uploaded. `watch`
contacts the public model catalog; explicit live runs contact Claude through its CLI.

`prepare` and `assess` never contact a model. Share only the generated `request.md`
with your external AI tool; other request files contain private source/checks.
External tool context, model identity and generation usage cannot be verified.
Snapshots and hashes detect inconsistent input, not deliberate forgery. Imported
code is evaluated with the same trusted-static-app boundary described above.

Cost stops are best effort. An in-flight response can overshoot its stop budget.
Unknown outcomes remain blocked; preserve receipts before manual reconciliation.

Report sensitive vulnerabilities privately through
[GitHub security advisories](https://github.com/mandu5/secondlook/security/advisories/new).
Do not include secrets in public issues. If private reporting is unavailable,
open an issue requesting a private channel without exploit details.
This community project has no guaranteed response SLA.
