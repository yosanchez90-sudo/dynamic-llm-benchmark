# L3/L4 dynamic-benchmark ingestion exclusions (inst1, zero-shot)

Source batches (OpenAI Batch API, instantiation_id=1, instantiation_seed=1,
tiers L3+L4, 150 requests submitted per model):

| Model | Batch state | Batch output | Process-batch log |
|---|---|---|---|
| gpt-5-2025-08-07 | `data/batches/batch_state_20260629T142712.json` | `data/batches/batch_output_20260629T142712.jsonl` | `logs/process-batch-9342122.out` |
| gpt-5-mini-2025-08-07 | `data/batches/batch_state_20260629T142708.json` | `data/batches/batch_output_20260629T142708.jsonl` | `logs/process-batch-9342121.out` |

Expected 150 rows/model (75 L3 + 75 L4). Ingested row counts (via
`scripts/process_batch.py`, which drops any row that errors — see "three
failure shapes" comment at `scripts/process_batch.py:137`):

- gpt-5: **144** rows (74 L3 + 70 L4) → 6 excluded
- gpt-5-mini: **149** rows (75 L3 + 74 L4) → 1 excluded

Total: **7 excluded requests**, none silently — every exclusion is a printed
`ERROR <custom_id>: <reason>` line in the process-batch log and is absent
from the output JSONL (there is no partial/placeholder row written for it).

## gpt-5 (6 exclusions)

| custom_id | template_id | seed | tier | failure |
|---|---|---|---|---|
| req-00044 | L3-nested2-001 | 1105 | L3 | HTTP 503, empty response body (transient) |
| req-00078 | L4-aggregate-001 | 1104 | L4 | HTTP 503, empty response body (transient) |
| req-00105 | L4-mega-001 | 1101 | L4 | HTTP 503, empty response body (transient) |
| req-00107 | L4-mega-001 | 1103 | L4 | `server_error`: "The server had an error while processing your request." |
| req-00110 | L4-merge-001 | 1101 | L4 | HTTP 503, empty response body (transient) |
| req-00125 | L4-pipeline-001 | 1101 | L4 | `server_error`: "The server had an error while processing your request." |

## gpt-5-mini (1 exclusion)

| custom_id | template_id | seed | tier | failure |
|---|---|---|---|---|
| req-00100 | L4-matrix-001 | 1101 | L4 | `invalid_request_error` / code `invalid_prompt`: "your prompt was flagged as potentially violating our usage policy" |

### Note on req-00100 (invalid_prompt)

This was flagged as an open item in the original ingestion pass ("was the
invalid_prompt cause ever identified?"). It was not identified at the time.
Investigated here:

The exact same rendered prompt (byte-identical function source + docstring —
`resolve_request(data)`, docstring "Rank ordered pairs that are
out-of-order and bounded, plus over-cap singles.") was sent to **both**
models for this `(template_id, instance_seed)` pair, since the batch input
is built once from the deterministic template engine and reused per model.
**gpt-5 processed the identical prompt successfully** (see `req-00100` in
`data/batches/batch_output_20260629T142712.jsonl` — 200 OK, scored
normally). Only the gpt-5-mini request was flagged.

Additionally, the function name `resolve_request` (drawn from the
5-entry `IDENTIFIER_BANKS["function_L4"]` pool in
`template_corpus/templates/_smoke/engine.py:33` — this is an identifier
bank, *not* the docstring `synonyms` table) appears 45 times across this
same gpt-5-mini batch and succeeded in all 44 other occurrences. The
docstring intro synonym "Rank" (one of 6 choices in
`L4-matrix-001`'s `docstring_template.synonyms["intro"]`) also appears
elsewhere in the batch (`req-00082`, `req-00084`, `req-00086`, `req-00089`,
`req-00147`) without triggering a flag.

**Conclusion: no single token or phrase in the prompt can be identified as
the trigger** — the same text passed moderation on gpt-5 and passed 44/45
other times under gpt-5-mini with the same fn_name and 5/6 other times with
the same docstring intro word. This is model-specific and/or non-deterministic
behavior of OpenAI's input-moderation classifier on gpt-5-mini, not a
deterministic content trigger.

**Reclassified 2026-07-14: retryable, not a permanent exclusion.** Because
the identical prompt succeeded on gpt-5, this is provider-side
non-deterministic filtering rather than content this project's prompts
must avoid — a plain retry (same template_id/instance_seed, new API call)
has no structural reason to fail again. req-00100 is added to the
supervisor retry batch below. It is *not* predictable from vocabulary and
may recur at a similarly low, non-deterministic rate on a retry or on
future batches, so the retry is not guaranteed to succeed — if it fails
again with `invalid_prompt`, that would itself be new evidence worth
re-opening this note for.

## Disposition / retry status

All 7 excluded (template_id, instance_seed) pairs are simply missing from
the corresponding per-model dynamic-benchmark JSONL — analysis code must
treat L3/L4 inst1 zero-shot as 144/150 (gpt-5) and 149/150 (gpt-5-mini)
complete, not 150/150, **until the retry batch below is ingested.**

**Supervisor retry batch — 7 IDs total** (he holds the OpenAI credits for
L3/L4 generation per `PROJECT_BRIEF.md` §11):

| Model | custom_id | template_id | seed | retry rationale |
|---|---|---|---|---|
| gpt-5 | req-00044 | L3-nested2-001 | 1105 | transient 503 |
| gpt-5 | req-00078 | L4-aggregate-001 | 1104 | transient 503 |
| gpt-5 | req-00105 | L4-mega-001 | 1101 | transient 503 |
| gpt-5 | req-00107 | L4-mega-001 | 1103 | transient server_error |
| gpt-5 | req-00110 | L4-merge-001 | 1101 | transient 503 |
| gpt-5 | req-00125 | L4-pipeline-001 | 1101 | transient server_error |
| gpt-5-mini | req-00100 | L4-matrix-001 | 1101 | non-deterministic provider-side filtering — same prompt succeeded on gpt-5 |

No retry has been submitted yet from this repo (would require a new,
separately-timestamped batch submission via `scripts/create_batch.py` +
`scripts/process_batch.py`, and per session rules that's GPU/API-submission
work requiring explicit sign-off, not a docs-only change). This table is
the handoff artifact for that retry.
