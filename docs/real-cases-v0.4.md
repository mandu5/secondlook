# Three existing projects, with an evaluation mistake retained

v0.4 was exercised on private copies of three existing personal projects.
The scope was selected by the agent from project documentation under the user's
authorization to develop and test Second Look. These are not three independent
customer interviews or verified historical model failures. Generating models for
the old artifacts are unknown. No original project files were changed.

All candidate calls resolved to `claude-sonnet-5-5`. B is an ordinary patch,
C writes an independent intent brief and then patches, and D rebuilds without
old writable source. Each workflow had the same effective $1/3 API-equivalent
cap within its task; actual calls, tokens and spend differed.

## Interpretable frozen comparisons

| Existing project / scoped requirement | A saved artifact | B ordinary | C reframe + patch | D clean slate |
|---|---:|---:|---:|---:|
| Job Radar: honest missing/invalid dates and expired opportunity exclusion | 6/9 | 9/9 | 9/9 | 9/9 |
| UGV-MON: mock-data disclosure, passive monitoring and documented local fallback | 3/7 | 7/7 | 7/7 | 7/7 |
| TSAD research: statistical context, reproduction and manuscript status | 5/5 | Skipped | Skipped | Skipped |

Job tests use explicit **synthetic inputs**, not a claimed production incident.
The HTML baseline is the existing artifact. The corrected protocol gives each
check one opportunity so labels can be evaluated independently of the old DOM.
The UGV trial is about documented presentation and commands; it does not verify
the remote demo's uptime or run packet capture. Research is an already-satisfied
negative control and consumed zero model calls.

| Cost and usage in the two interpretable trials | B | C | D |
|---|---:|---:|---:|
| Job Radar API-equivalent USD | 0.0414374 | 0.0751372 | 0.0348640 |
| Job Radar reported tokens | 8,642 | 14,298 | 5,274 |
| UGV-MON API-equivalent USD | 0.0191834 | 0.0506852 | 0.0331760 |
| UGV-MON reported tokens | 4,214 | 9,526 | 4,858 |
| Combined API-equivalent USD | **0.0606208** | 0.1258224 | 0.0680400 |
| Combined reported tokens | 12,856 | 23,824 | **10,132** |

There was no additional measured functional gain from C or D in these trials.
D cost least for Job Radar; B cost least for UGV and across both cases together.
Tokens and dollars have different rankings. These observations are specific to
the recorded calls, not a general efficiency ranking or causal model upgrade.
Provider tokens include cache reads and writes; API-equivalent cost is not the
subscription invoice.

## Why the first Job Radar score was discarded

The first frozen Job Radar checks searched for date labels **inside** each job
link. D rendered the correct date labels beside the link in the same card.
The automatic score was A4/7, B7/7, C7/7, D3/7. Source and browser review showed
that four failures reflected the evaluator's inherited DOM assumption. Calling
this a functional regression would be incorrect.

The original checkset, generated candidates, receipts and raw result were
preserved. A new protocol was frozen, using check-local read-only JSON inputs
and separate visible-label/link checks. Re-evaluating the **existing** B/C/D
candidates gave 9/9 for all three, with no new model calls. That is explicitly
post-hoc diagnostic evidence. A separate fresh B/C/D model trial then also
reached 9/9; only this newly frozen trial is included in the table above.

The harness now supports bounded check-local input overrides without mutating
the source files or exposing those inputs in prompts. It cannot automatically
prove an evaluator is unbiased: the error was found through review, and these
corrected checks still have finite coverage. Link and keyword checks do not
establish general usability, aesthetic quality or all preserved behavior.

## Total verification bill and scope

- Interpretable frozen cases: **8 calls, 46,812 tokens, $0.2544832**.
- Including the criteria-confounded first job trial: **12 calls, 77,088 tokens,
  $0.4133206**. Zero extra calls were used for post-hoc rechecking or the research
  control. Chat and reviewer inference are outside provider-receipt accounting.
- All 12 provider receipts were terminal and cost-accounted. D prompt structures
  contained no old writable source or check definitions. Read-only file bytes
  and original project hashes remained unchanged.
- Identical repeat plans in each trial's library selected no additional tasks.
- Candidate code remains in experiment folders. Nothing was adopted, published
  or deployed. User adoption, multi-user demand and statistical significance
  remain unmeasured.

The machine-readable [verification record](verification-v0.4.json) contains the
per-arm categories and measured comparisons. Private raw projects, prompts,
screenshots and receipts are excluded from public source bundles.
