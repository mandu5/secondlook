# An independent brief for the next attempt

Save the original problem separately from its last implementation. The v0.4
rebuild contract adds a small, explicitly sourced brief to a normal capsule:

```json
{
  "readonly_files": ["facts.json"],
  "rebuild": {
    "brief": "State the outcome, verified facts, required interactions and existing value to preserve. Do not paste the old implementation here.",
    "source": "Original request or independent project document, with provenance",
    "confirmed": true
  }
}
```

This is a documentation convention implemented by Second Look, not a claim to
have invented specification-driven development. It must still be curated:
incorrect requirements or mislabeled shared files can carry old assumptions into
the new attempt. A model cannot recover missing original intent from a hash.

Before generation:

1. Record the original request, constraints and facts with their sources. When
   an agent proposes a scope from project documents, say that explicitly.
2. Put old implementation assumptions in `assumptions`, with their provenance.
   Do not promote them to confirmed facts in the rebuild brief.
3. Choose the exact files that are independent shared data/assets in
   `readonly_files`. All other allowlisted files are writable. The entrypoint
   must be writable. No arm can change shared files.
4. Define `intent` checks for the intended outcome and `preservation` checks for
   existing useful behavior. Each categorized check needs a nonempty `basis`.
   Both categories are required for rebuild. Passing a handful of checks still
   leaves untested behavior.
5. Probe for free, correct harness mistakes, then freeze the final contract
   before generating candidates. Changes made after generation are exploratory
   and require a separate trial; never merge them into the original score.

Prefer behavior and accessible names over old element IDs. Second Look accepts
Playwright selector strings, for example `role=link[name="Docs"]`. The public
[locator guidance](https://playwright.dev/docs/locators) explains why visible
roles and names help express what the reader interacts with. A selector is still
a finite operational definition; differing correct wording can require human
review. Check definitions are withheld from every generation prompt. An input
already present in shared data or source is not a holdout.

For data-driven pages, use one test input at a time to avoid requiring the old
layout. A check's optional `inputs` replaces only allowlisted read-only JSON
responses in its isolated browser context, without writing source files:

```json
{
  "id": "missing-deadline",
  "category": "intent",
  "basis": "Missing dates must be labeled unknown; one opportunity avoids layout assumptions",
  "inputs": {"data.json": {"opportunities": [{"title": "Example", "deadline": null}]}},
  "assert": {"selector": ":text-is(\"Date unknown\"):visible >> nth=0", "visible": true}
}
```

The capsule must include `data.json` in both `files` and `readonly_files`.
Object/array overrides total at most 64 KiB per check and are never sent to the
model. A new browser context prevents overrides leaking into the next check.
Overrides preserve GET/HEAD behavior; unsupported write methods still reach the
static server's normal rejection, so fixtures cannot manufacture a working API.
Check link retention separately; the presence of a label alone does not prove
that all surrounding behavior is correct.

## What each workflow receives

| Workflow | Independent requirements | Old writable source | Shared read-only files | Calls |
|---|---|---|---|---|
| B ordinary revision | Yes | Yes | Yes | 1 |
| C intent brief, then revision | Before the brief | Only in implementation call | In implementation call | 2 |
| D clean-slate rebuild | Yes | Never | Yes | 1 |

Each workflow gets the same planned total cap, not the same token count or
actual spend. D returns complete files. They are validated as a whole before
writing and limited to 64 KiB of generated UTF-8 text. The total captured source
context limit also applies. Script-projected capsules cannot use D: their
unshown implementation is not an independent brief.

A is the saved artifact, checked now. The report includes A/B, A/C, A/D, B/C,
B/D and C/D, category scores, screenshots, diffs, actual usage and receipts.
Regressions take precedence over new passes. Missing/different actual model
identities or unequal effective caps make a workflow comparison inconclusive.
The fixed order and one sample per workflow cannot prove general superiority.

## Try it

The [public greeting example](../examples/clean-slate/capsule.json) is deliberately
small and synthetic. It demonstrates the mechanics, not product demand.

```bash
# No model call. Baseline should pass Docs navigation and fail the greeting.
secondlook probe examples/clean-slate/capsule.json --output .secondlook/greeting-probe

# Use an exact available model ID; this command can spend model budget.
secondlook run examples/clean-slate/capsule.json --mode compare-three \
  --model YOUR_EXACT_MODEL_ID --budget-usd 1 --output .secondlook/greeting-trial

# Or use the same mode for a library campaign.
secondlook queue my-candidate --mode compare-three --budget-usd 3
```

`--mode rebuild` runs only D. Existing `compare` still means B/C. The standard
feedback `demo` remains a B/C example without an independent rebuild contract.
Nothing adopts a patch automatically. A passing baseline skips all model calls
unless a deliberate single-artifact run uses `--force`.
