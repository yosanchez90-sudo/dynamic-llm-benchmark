# Supervisor handoff — GPT-5 / GPT-5-mini batch requests, 2026-07-14

Two batch input files, prepared with `scripts/create_batch.py --no-submit`
(not uploaded or submitted — needs your OpenAI credits per `PROJECT_BRIEF.md`
§11). Both follow the same round-trip already used for the L1/L2 and L3/L4
inst1 batches: submit via the Batch API, then run
`scripts/process_batch.py <state file> --results-file <results.jsonl>` once
results are back.

## 1. Coverage backfill — 2400 requests

- Input: `data/batches/batch_input_20260714T131617.jsonl`
- State: `data/batches/batch_state_20260714T131617.json`
- Fills every currently-missing gpt-5 / gpt-5-mini cell for the main study
  (zero-shot, K=1) per `scripts/coverage_matrix.py`:
  - L1+L2 x instantiations 2, 3, 4, 5 (both models)
  - L3+L4 x instantiations 2, 3, 4, 5 (both models)
- 16 configs x 150 problems = 2400 requests. `configs/gpt_5*__dynamic_*__inst{2,3,4,5}.yaml`.
  (An earlier draft of this batch only covered L1/L2 inst2-3 — caught and
  corrected before sending: inst4/5 are missing across every tier, not just
  L3/L4, since neither instantiation has been generated for any model yet.)
- Estimated cost at Batch API rates (50% off), per `scripts/estimate_cost.py`
  at the time of writing: gpt-5 ~$36.78 (1206 missing problems, includes the
  1+5 problems still owed from the L3/L4 inst1 exclusions until the retry
  batch below lands), gpt-5-mini ~$6.81 (1201 missing problems) — **$43.59
  total**, already netting out the 7 problems covered by the retry batch
  below (2400 backfill + 7 retry = 2407 = 1206 + 1201). Re-run the script
  for the exact current figure if this hasn't shipped immediately.

## 2. Retry batch — 7 requests

- Input: `data/batches/batch_input_20260714T131346.jsonl`
- State: `data/batches/batch_state_20260714T131346.json`
- Retries the 7 requests excluded from the original L3/L4 inst1 batch — full
  rationale in `analysis/EXCLUSIONS.md` ("Disposition / retry status"):
  - 6x gpt-5, transient 503/server_error (`req-00044`, `req-00078`,
    `req-00105`, `req-00107`, `req-00110`, `req-00125` in the original batch —
    new custom_ids in this batch, mapped by template_id+seed in the state file)
  - 1x gpt-5-mini, `L4-matrix-001` seed 1101 — `invalid_prompt` classifier
    flag, reclassified retryable (identical prompt succeeded on gpt-5, so this
    is non-deterministic provider-side filtering, not a content issue — see
    EXCLUSIONS.md for the full investigation)
- These use a new `only_instances` filter on the dynamic loader (added this
  session, `src/data/test_gen.py` / `src/eval/test_gen_runner.py`) to select
  exactly these 7 (template_id, seed) pairs through the normal
  `create_batch.py` path rather than a hand-built request list.
- Estimated cost: well under $1 (7 problems total).

## Notes

- Both batches use each model's existing pinned snapshot
  (`gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`) and the same generation
  config already used for inst1 (temperature 0.2, `max_new_tokens` 16384 /
  8192 — sized for hidden reasoning-token overhead, see comments in the
  `gpt_5__dynamic_L1L2.yaml` / `gpt_5_mini__dynamic_L1L2.yaml` originals).
- If the retry batch produces another `invalid_prompt` flag on the same
  request, that's new evidence worth a fresh look (EXCLUSIONS.md flags this
  explicitly) — please pass it back rather than re-retrying silently.
- No other action needed on your end beyond submit -> return results file.
