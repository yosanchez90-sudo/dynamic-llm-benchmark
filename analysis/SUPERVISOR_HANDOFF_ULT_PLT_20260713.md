# Supervisor handoff — GPT-5 / GPT-5-mini batch requests: ULT/PLT core_400

Prepared 2026-07-13 with `scripts/create_batch.py --no-submit` (not uploaded
or submitted — needs your OpenAI credits per `PROJECT_BRIEF.md` Sec 11).
**Still unsubmitted as of this note** — flagging since the separate dynamic-
benchmark backfill handoff (`SUPERVISOR_HANDOFF_20260714.md`) covers a
different batch; this one is Comparison A/B (ULT/PLT) specific and was not
folded into that one.

## Batch — 1600 requests

- Input: `data/batches/batch_input_20260713T124543.jsonl`
- State: `data/batches/batch_state_20260713T124543.json`
- Covers gpt-5 and gpt-5-mini on the pinned `core_400` CC-stratified
  subsample (see `data/raw/ult_plt/subsample_manifest.json` and
  `data/raw/ult_plt/PROVENANCE.md`) for both ULT and PLT — this is the
  closed-source-model half of Comparison A (Dynamic vs ULT) and Comparison B
  (ULT vs PLT); Claude Sonnet/Haiku 4.5 and Gemini 3.1 Pro Preview/Flash-Lite
  have already run on this exact same subsample (or are running now — see
  `logs/core400v2-*` for the 2026-07-22 retry), so this batch is what's
  needed to complete all-9-model coverage for ULT/PLT.
- 4 configs x 400 problems = 1600 requests:
  `configs/gpt_5__ult__core400.yaml`, `configs/gpt_5__plt__core400.yaml`,
  `configs/gpt_5_mini__ult__core400.yaml`, `configs/gpt_5_mini__plt__core400.yaml`.
- Every request in the input file is tagged `benchmark: "ult"` or `"plt"`
  and `tier: "L4"` in the state file's per-request metadata (all ULT/PLT
  problems are CC>=8, this project's L4 band — see PROVENANCE.md).

### Cost estimate (2026-07-22, from real logged L4-tier usage — gpt-5/-mini
already have 70-74 real L4 samples from the dynamic-benchmark L3/L4 batches,
so this is measured, not the generic cross-model proxy)

| Model | Mean input tok | Mean output tok | Batch-rate $/problem | x800 problems |
|---|---|---|---|---|
| gpt-5-2025-08-07 | 231 | 5299 | $0.0400 | **~$32.00** |
| gpt-5-mini-2025-08-07 | 232 | 3102 | $0.0071 | **~$5.68** |
| **Total** | | | | **~$37.68** |

Same round-trip as the other batches: submit via the Batch API, then run
```
python scripts/process_batch.py data/batches/batch_state_20260713T124543.json \
    --results-file <path-to-results.jsonl>
```
`process_batch.py` reads `benchmark`/`tier` from the state file's per-request
metadata (same mechanism already used for the L3/L4 dynamic batches — see
`ad397dd fix(batch): derive tiers from batch metadata`), so results land in
`data/results/ult/` and `data/results/plt/` automatically per each request's
`output_dir` field — no separate handling needed on the ingestion side.

## Notes

- Uses each model's existing pinned snapshot (`gpt-5-2025-08-07`,
  `gpt-5-mini-2025-08-07`) — unaffected by the Claude/Gemini model-ID issues
  found and fixed elsewhere in July.
- `max_new_tokens` 16384/8192 as already used for the L1/L2 and L3/L4 inst1
  batches (sized for hidden reasoning-token overhead).
- No other action needed on your end beyond submit -> return results file.
