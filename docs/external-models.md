# Use the AI tool you already have

`prepare` and `assess` make **zero model calls**. Use an existing chat subscription,
coding assistant, or local model to generate a response, then measure that output
locally. External generation may still have a cost or subscription limit.
This workflow currently evaluates trusted static HTML/CSS/JS.

## 1. Freeze your task

Start with a capsule whose original intent and acceptance checks you reviewed and
confirmed. See [capture your own app](quickstart.md#use-your-own-static-app).

```bash
# Patch the existing app using the selected source context:
secondlook prepare ./capsule.json --mode ordinary --output ./request

# Or start over from independently recorded requirements:
secondlook prepare ./capsule.json --mode rebuild --output ./fresh-request
```

Rebuild is the default. It requires a confirmed independent `rebuild` brief plus
intent and preservation checks, and does not support script-only projection.
It exports the requirements and declared read-only data, excluding old writable
source. Ordinary exports the selected source, so it can preserve exact anchors.

Only **`request/request.md`** goes to the AI tool. The other files contain private
source, checks and identities. Use a fresh conversation with only that request;
disable extra repository context/tools where your tool supports it. This is a
recommended procedure, not enforced or verified by Second Look.

The original files are never modified. The snapshot is portable: you can move the
request directory or delete the original source and still assess a response.
Changing the snapshot, capsule or request invalidates it; prepare a new request
when the requirements change. Hashes detect inconsistent contents, not forgery.

## 2. Save one or more responses

Ask your AI tool to follow the JSON schema inside `request.md`. Save its output as
`response-a.json`. For another candidate, use exactly the same request in a fresh
conversation and save `response-b.json`. Do not send either candidate to the other.

An ordinary response has this shape (copy the actual request ID):

```json
{
  "request_id": "COPY_THE_64_CHARACTER_ID_FROM_REQUEST_MD",
  "summary": "Correct the welcome heading while preserving the documentation link",
  "edits": [{"path": "index.html", "old": "Helo", "new": "Hello"}]
}
```

Each old anchor must occur exactly once. Rebuild responses use `files`, each with
`path` and full `content`, for every writable file exactly once. Do not return
read-only files. One enclosing Markdown JSON fence is accepted; unrelated prose,
duplicate keys, nonfinite numbers, extra fields and mismatched IDs are refused.

## 3. Compare locally

```bash
secondlook assess ./request \
  --response ./response-a.json --label 'Tool A / selected model version' \
  --response ./response-b.json --label 'Tool B / selected model version' \
  --output ./comparison
```

Open `comparison/report.html`. A is the saved artifact; E1–E4 are imported
candidates. Inspect every pair for newly passing checks and regressions. There
is no automatic winner or adoption. A failed candidate is retained. Exit code 1
means an incomplete evaluation; completed behavior regressions still return 0.
Bad input returns 2 before evaluation. Output must be a new directory outside
the request. This command intentionally assesses passing baselines too: there is
no model dispatch to save, and an already-created candidate can still regress.

Model labels are **owner-reported and unverified**. Unknown tokens/cost stay
unknown. Optional `--usage ./usage.json` accepts an array in response order:

```json
[
  {"cost_usd": 0.03, "input_tokens": 1200, "output_tokens": 240},
  null
]
```

Use values from your tool's usage record, not estimates invented by the generated
response. Even supplied values remain unverified. Partial token records do not
produce a complete total. Failed candidates retain their reported generation
costs. Identical candidate source reuses browser evidence within this batch and
is marked as reuse, not an independent repeated trial.

## 4. Share the measured result

```bash
secondlook share ./comparison/result.json --output ./shareable
# Optional, after reviewing the visible content:
secondlook share ./comparison/result.json --output ./visual-share \
  --include-screenshots --include-intent
```

Keep `index.html` beside `summary.json`. By default source, requests, candidate
responses, detailed errors, private paths and owner-supplied labels are omitted.
Unverified usage and evidence reuse remain marked. Nothing is uploaded.

## Reproduce the public no-model example

From a source checkout, after installing Second Look and Chromium:

```bash
python examples/imported-candidates/make_demo.py --output .secondlook/import-demo
```

The script prepares a task, writes two explicitly hand-authored responses,
assesses them and exports a report. It demonstrates improvement and regression;
neither response is evidence of a model's performance. No provider is contacted.
