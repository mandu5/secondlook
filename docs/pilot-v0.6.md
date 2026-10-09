# Second Look v0.6 user pilot

Decision rules set on **2026-10-09 (Asia/Seoul)**. Review date:
**2026-10-23, 23:59 KST**. Product version: **0.6.0**.

This is a small product decision, not a statistical benchmark or proof of market
demand. Feature expansion is on hold. The current CLI and its evaluation scope
remain the trial product. There is no paid recruitment, reward, new API purchase,
background model run, or automatic collection of local work in this pilot.

[Participant guide](https://mandu5.github.io/secondlook/pilot/) ·
[Report a result or blocker](https://github.com/mandu5/secondlook/issues/new?template=experience.yml) ·
[Recruitment copy](launch.md)

## The decision

Would developers return to this tool because it helps them decide what to adopt
from an AI revision of old work, despite the effort of preparing a comparison?
The narrower onboarding test comes first. It does **not** validate portfolio
selection, causal old-versus-new model improvement, or a general token-saving rate.

Reconsider a small, focused next iteration only when **all** of these are met:

| Gate | What counts |
| --- | --- |
| Actual use | At least 3 distinct external developers complete a comparison of their own supported task. Record successful comparisons and abandoned attempts separately. |
| Return use | At least 2 of those developers actually use it on a second distinct task. A second candidate for the same task, a rerun, or saying “I would use it” does not count. Record prompted versus spontaneous returns. |
| Consequential outcome | At least 1 owner-confirmed adopted improvement or a specific regression that changed an adoption decision. Passing checks alone does not count. Label self-reported outcomes separately from independently inspectable evidence. |
| Benefit over an alternative | At least 1 completed matched comparison shows lower total active time or reported token use for an equally acceptable outcome, without a known additional regression. Include preparation, reviewing, failed attempts and evaluation calls. Report other costs and all losses too; one success does not establish a general advantage. |

Meeting these gates permits a reassessment. It does not automatically establish
a 5/10 or 7/10 score, justify a broad platform, or establish SOTA.

## Who and what is eligible

- A developer with a real, trusted static HTML/CSS/JS artifact and an unfinished
  requirement or a candidate change to assess. Python execution, backends and
  arbitrary repositories are outside v0.6's execution scope.
- Python 3.11+, macOS or Linux, and an AI tool they already use if generation is
  needed. Do not buy a plan or API credits for this pilot. Stop if quota or cost
  would exceed what you intended to use. Local assessment itself makes no model
  calls; external generation can consume quota or money.
- Maintainer/contributor trials, AI-generated testimonials and bundled demos
  are excluded from external-user counts. A friend's real attempt may count,
  but disclose that recruitment relationship and any assistance in the ledger.

One participant is identified by their first issue and GitHub author. Follow-up
comments stay on that issue. Reconcile duplicates manually; do not count issue
count, release downloads, page visits or GitHub stars as users.

## First attempt

1. Optionally inspect the [hand-authored import report](https://mandu5.github.io/secondlook/import-demo/).
   Viewing it is not a real-task attempt.
2. Choose one task you are already considering. Before generating, write the
   original purpose, one desired improvement and one behavior to preserve.
   Freeze the same acceptance criteria for every candidate. Check that the
   criteria describe behavior rather than the old implementation's structure.
3. Start a timer. Follow the [installation and own-project capture](quickstart.md#use-your-own-static-app)
   and [prepare / assess walkthrough](external-models.md). Use `--mode ordinary`
   for a patch unless you already have independently confirmed rebuild
   requirements. Give only `request.md` to the external tool in a fresh context.
4. Use a **20-minute preparation cap**. This is a stopping rule, not a promised
   setup time. If installation or preparing the task takes longer, stop and
   report that barrier. Generation/waiting and review time are recorded
   separately. Do not keep debugging to make the pilot look successful.
5. Inspect changed checks, regressions and screenshots. Decide whether to keep
   the original, adopt a change, or reject the comparison. Record the reason.
6. [Open one feedback issue](https://github.com/mandu5/secondlook/issues/new?template=experience.yml).
   English and Korean are welcome. Stopping early is valid feedback. A GitHub
   account is needed to submit; no account is needed to read the guide or demo.

## Compare with the usual method

This optional extra step supplies the benefit gate; participants may report a
blocker or first use without doing it. Use a small task and respect existing
quota. Nobody is asked to rerun a large project.

- Compare the normal direct request plus manual review with the Second Look
  workflow. Use fresh copies of the same starting artifact, the same purpose,
  frozen acceptance criteria, selected model/settings and spend cap. Do not show
  either candidate to the other generation. Randomize which workflow comes first
  (a coin flip is enough) and record the order and any assistance.
- Measure active time (setup + preparing + interacting + reviewing), waiting
  time, attempts, acceptability and regressions for **both** methods. First-use
  installation time belongs in the first-use total. Report later-use time
  separately so amortization cannot hide the initial burden.
- Use actual usage records if available. Mark estimates and retrospective
  recollections as such; they cannot establish the measured-benefit gate.
  Unknown cost/tokens are `null`, never zero. If either side lacks comparable
  token records, omit token savings and compare measured active time instead.
- With measured comparable values, time savings = `1 - secondlook / usual`.
  If the usual-method value is zero or unknown, the ratio is undefined. Do not
  combine time and token savings into one score. A slower or more costly trial
  remains in the record even when another trial passes the gate.
- Evaluate each output with the same criteria and the owner's decision. Do not
  infer that the new model is better, or that reframing is superior, from one
  successful artifact. Record missed improvements as well as regressions.

## Second-task follow-up

Only return when a **different real task** occurs. Do not manufacture a task to
meet the gate. Add this as a comment on your first issue; do not open a duplicate.

```text
Second task date:
Different original task and requirement (no private details):
Why I returned / did someone remind or help me?
Version and model/tool:
Preparation / other active / waiting minutes (unknown is fine):
What I actually adopted, rejected, or could not finish:
Optional comparable usage records or reviewed public evidence:
```

## Record and decision procedure

The maintainer records each exposure (channel, date, link and known denominator),
first attempt, stage reached, abandonment, assistance, actual return and outcome.
No cold messages, community posts or reminders are sent automatically. The
invitation text is prepared in `launch.md`; posting needs a named channel/account.
The review date is a written checkpoint, not a registered scheduled job.

At the checkpoint, publish only reviewed aggregate counts and consented evidence:

- Qualified people reached, where known; unknown exposure denominators stay unknown.
- Distinct external attempts, completed first comparisons, and setup abandonments.
- Actual second-task users / all completed first users; also show how many had at
  least 7 days to return. Late participants are right-censored, not counted as
  observed failures to return. The full-window denominator must remain visible.
- Adopted/prevented-regression outcomes, with evidence basis and failed outcomes.
- Matched comparisons, wins/ties/losses, measured active/waiting time and
  known/unknown token/cost coverage. Exclude neither inconvenient trials nor
  incomplete preparations from the corresponding attempt totals.

If all gates pass, choose at most one next change tied to an observed barrier.
If reached users try but do not finish or return, hold expansion and record where
the workflow failed. If exposure or follow-up is insufficient, the result is
**inconclusive**, not “no demand.” In all non-passing cases leave v0.6 available
and keep feature expansion on hold. Do not silently extend the pilot or lower
the thresholds after seeing the results.

## Public reporting boundary

Feedback issues and comments are public. Ask for brief descriptions and metrics;
source, prompts, raw responses and personal information are unnecessary. Keep
local reports private by default. `secondlook share` is opt-in and its output
must be reviewed before anyone publishes it; screenshots can expose content.
Owner reports are useful evidence but are not provider-verified usage records.
