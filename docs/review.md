# Independent review and implementation decisions

One fresh reviewer checked `b81377a..5eb2f84` read-only against the spec, code, tests and live receipts. The reviewer made no paid calls or changes. It confirmed the recorded demo totals and returned four Important findings, no Critical findings and one whitespace-only Minor finding.

## Important findings addressed in one fix pass

1. Invalid UTF-8 provider stdout bypassed accounting. The adapter now captures raw bytes, writes a durable unknown-outcome receipt, raises a normalized error, and stops subsequent calls. Verified at the subprocess boundary and through the full workflow.
2. Malformed `modelUsage` or missing `usage` could crash after spending. Metadata is validated before completion; already-known spend survives adapter failures. Missing usage remains explicitly unavailable, and report totals do not turn it into zero.
3. Invalid acceptance definitions could pass or be treated as app failures. Types, CSV/download prerequisites and selectors are checked. Harness failures make evaluation inconclusive; genuine unmet expectations remain behavioral failures.
4. An overshooting B call could reduce C's effective allowance without changing the equal-budget verdict. Effective caps are recorded and unequal caps make B/C inconclusive. A single matching actual model identity is also required; equal sets containing several fallback models do not establish a matched experiment.

Each issue was reproduced with a failing test before its fix. The review regression run initially showed 18 failures; an additional model-identity test failed before its implementation. The full post-fix suite is recorded in `validation.md`. No second reviewer was dispatched; the original author applied and verified the fixes.

## Decisions retained

- A new dedicated repository on a feature branch supplies isolation without a second worktree. No existing repository was altered. Cost if wrong: no impact on existing repositories; integration remains local.
- Ship the static-app scope and a synthetic public fixture first. A personal wardrobe artifact encountered during exploration contained roughly 120 MB of private image data and was not a suitable small public example. Cost if wrong: usefulness on general repositories and real legacy tasks remains unvalidated.
- Continue implementation under the user's existing approval to proceed; do not ask for a second design approval. Cost if wrong: the local changes are reversible. No public publishing action was taken.
- Arbitrary hostile-code OS isolation remains outside scope, consistent with the binding spec. The evaluator's origin restrictions and copy boundary were reviewed. Cost if wrong: hostile browser code can exceed these protections; use trusted static apps only.
- Automatic detection of secret content inside an explicitly selected source file remains outside scope. The allowlist, filename and path controls were reviewed. Cost if wrong: an improperly selected file can disclose its contents to the chosen model provider; inspect the allowlist before a live run.

## Deferred minor

The original commits have an extra blank line at EOF in `src/secondlook/__init__.py` and `tests/conftest.py`. `git diff b81377a HEAD --check` flags these. They have no runtime effect and were left out of the behavioral fix pass.

The work remains on the local `feat/first-revisit` branch. There is no existing base branch or remote to merge into; public release is a separate action.
