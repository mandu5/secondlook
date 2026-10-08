# Preserve the problem, not just its last answer

The original request, observations, and constraints are the input to a future attempt. An old model's assumptions should remain identifiable as assumptions. Second Look does not summarize your history with another model during harvest.

Start from [the general record example](../examples/problem.json). `secondlook harvest problem.json --problem` stores a version without pretending it can execute the task. A static-app capsule can be harvested directly; it adds a source fingerprint and frozen checks.

| Field | Meaning |
|---|---|
| `intent.text` / `source` / `confirmed` | Original request, where it came from, and whether its scope has been reviewed |
| `constraints` | Requirements that a new attempt must respect |
| `failures` | Observed shortcomings; include the observation or evidence reference in the text |
| `assumptions` | Legacy hypotheses with `text` and `source`; do not relabel them as facts |
| `revisit.capabilities` | Declared reasons a different model might help |
| `revisit.impact` / `estimated_usd` | Owner estimates used for selection, not predicted success or actual spend |
| Capsule `checks` | Independently reviewable acceptance criteria, frozen before the attempt |
| Capsule `baseline` | Known model provenance, or explicitly `unknown` |
| Capsule `rebuild` | Independently sourced `brief`, `source`, and reviewed scope `confirmed` for clean-slate work |
| Capsule `readonly_files` | Explicit independent inputs; no candidate may change them |
| Check `category` / `basis` | `intent` or `preservation`, with the criterion's provenance |
| Check `inputs` | Check-local JSON responses replacing declared read-only data only; withheld from generation |

A changed record or source creates another immutable revision; repeating the same harvest does not. The library keeps the earlier revision and compressed, content-addressed copies of the allowlisted source. Identical source bytes share a stored object. This uses local disk, not model tokens. Execution still checks the live source binding for unexpected changes.

Recover an earlier original into a new directory with `secondlook restore TASK_ID --revision REVISION --output restored-project`. Omitting the revision restores the current harvested version. Restore validates blob hashes and the complete artifact identity before writing files, and never overwrites a destination. It works after the original files are deleted. Older metadata-only library entries must be re-harvested while their originals are still available; missing historical contents cannot be reconstructed from a hash.

Example candidate profile (replace the model ID and evidence before use):

```json
{
  "id": "my-candidate",
  "provider": "claude-cli",
  "runtime_model": "claude-REPLACE-WITH-AVAILABLE-ID",
  "revision": "release-or-explicit-profile-version",
  "capabilities": ["coding"],
  "evidence": "Link a release claim or state your trial hypothesis; this is not measured uplift"
}
```

Optional `catalog_id` and `catalog_source` bind the profile to a specific inventory entry and source. For live OpenRouter observations the source is `https://openrouter.ai/api/v1/models`. This is explicit mapping: the tool does not guess that two vendors' IDs or capabilities are equivalent. `watch --queue` prepares plans only for mapped additions/changes. Catalog removals do not trigger spending.

Candidate revisions, source and checks, the execution harness, environment, workflow, and explicit trial identify an attempt. Attempt suppression saves calls; it does not turn cached outputs into measurements of a new model. The intent-first workflow sees the original goal before source code, then applies bounded edits. v0.4 also offers a clean-slate workflow from an independent brief and explicitly shared data. [Contract and example](clean-slate.md).
