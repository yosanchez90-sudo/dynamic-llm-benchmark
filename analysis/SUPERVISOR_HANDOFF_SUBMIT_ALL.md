# GPT-5 / GPT-5-mini batches — everything needed to submit, in one place

Three batches have been prepared and are sitting ready to go. Nothing has
been submitted or charged yet. This file is self-contained — you shouldn't
need to open the rest of the repo to act on it.

## What these are

| # | Batch | Requests | Est. cost | What it fills |
|---|---|---|---|---|
| 1 | Dynamic-benchmark coverage backfill | 2,400 | ~$43.59 | Missing gpt-5/gpt-5-mini cells (instantiations 2-5, all tiers) |
| 2 | Dynamic-benchmark retry | 7 | <$1 | 7 requests that failed transiently in the original batch |
| 3 | ULT/PLT `core_400` | 1,600 | ~$37.68 | gpt-5/gpt-5-mini's half of the static-benchmark comparison |
| | **Total** | **4,007** | **~$81** | |

(Cost estimates from `scripts/estimate_cost.py`, computed 2026-07-13/14 from
this project's own measured per-model token rates — re-run that script
first if more than a few weeks have passed and you want to double-check
before spending, in case OpenAI's Batch API pricing has changed.)

Full technical detail on what each batch covers and why:
`analysis/SUPERVISOR_HANDOFF_20260714.md` (batches 1-2) and
`analysis/SUPERVISOR_HANDOFF_ULT_PLT_20260713.md` (batch 3). This file is
just the "how do I actually press go" version.

## Turnaround

OpenAI's Batch API guarantees completion within 24h of submission (usually
much faster in practice for jobs this size) — call it same-day, this-batch,
no action needed beyond checking back once.

## How to submit (5 steps)

**Prerequisite**: an OpenAI API key with Batch API access and enough
prepaid balance to cover ~$81, set as `OPENAI_API_KEY` in this project's
`.env` file (or exported in your shell) — same key/setup already used for
every prior GPT batch this project has run.

1. `cd` into the dissertation repo, activate the venv:
   ```bash
   cd /mnt/scratch2/users/40492566/dissertation
   source .venv/bin/activate
   ```
2. Confirm your key is picked up (should print a key ID, not an error):
   ```bash
   python -c "from openai import OpenAI; print(OpenAI().api_key[:12] + '...')"
   ```
3. **Submit all three batches** — this uploads each already-prepared
   `batch_input_*.jsonl` file exactly as-is (nothing is regenerated or
   changed) and writes the returned `batch_id` back into its matching
   `batch_state_*.json`, which is what the scoring step reads afterward:
   ```bash
   python -c "
   from openai import OpenAI
   import json
   client = OpenAI()

   def submit(input_path, state_path):
       with open(input_path, 'rb') as fh:
           uploaded = client.files.create(file=fh, purpose='batch')
       batch = client.batches.create(
           input_file_id=uploaded.id,
           endpoint='/v1/chat/completions',
           completion_window='24h',
       )
       state = json.load(open(state_path))
       state['batch_id'] = batch.id
       state['input_file_id'] = uploaded.id
       state['status'] = batch.status
       json.dump(state, open(state_path, 'w'), indent=2)
       print(f'{input_path}: batch_id={batch.id} status={batch.status}')

   submit('data/batches/batch_input_20260714T131617.jsonl', 'data/batches/batch_state_20260714T131617.json')
   submit('data/batches/batch_input_20260714T131346.jsonl', 'data/batches/batch_state_20260714T131346.json')
   submit('data/batches/batch_input_20260713T124543.jsonl', 'data/batches/batch_state_20260713T124543.json')
   "
   ```
4. You'll see three lines printed back, each with a `batch_id` and
   `status=validating` (or similar) — that confirms it went through. No
   further action needed today.
5. Once you get a "batch complete" notification from OpenAI (email or by
   checking the [Batches dashboard](https://platform.openai.com/batches)),
   run, for each of the three:
   ```bash
   python scripts/process_batch.py data/batches/batch_state_20260714T131617.json
   python scripts/process_batch.py data/batches/batch_state_20260714T131346.json
   python scripts/process_batch.py data/batches/batch_state_20260713T124543.json
   ```
   Each of these polls until done, downloads the results, and scores them
   straight into `data/results/dynamic|ult|plt/` — nothing else to do on
   your end.

## If you'd rather fund this yourself (your own API key, not the lab's)

Nothing about the three JSONL files needs to change — the request bodies
only contain the model ID, messages, and generation parameters, no
account/key-specific data, so ANY valid OpenAI API key can submit them
as-is. What you'd need:

- An OpenAI account/API key with **Batch API access** and access to the
  `gpt-5-2025-08-07` / `gpt-5-mini-2025-08-07` model IDs specifically (not
  universally available on every account — worth a quick check on
  [platform.openai.com/settings](https://platform.openai.com/settings) or a
  small $0 test request before committing to the full ~$81).
- A **prepaid credit balance** covering ~$81 (Batch API is billed against
  account balance/spending limits, not invoiced after the fact) on that
  key's account.
- That key set as `OPENAI_API_KEY` (in `.env` or your shell) before running
  step 3 above — same commands, same files, just a different key behind
  the `OpenAI()` client.
- Nothing else changes: same submission steps, same scoring step, same
  output location. The distinction is purely financial (whose balance gets
  charged), not technical.

## Notes

- All three batches use each model's already-pinned snapshot
  (`gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`) and the generation config
  already used for every other GPT batch in this project (temperature 0.2,
  `max_new_tokens` sized per-benchmark for hidden reasoning-token overhead).
- If anything in step 3 errors (e.g. `RateLimitError`, model access denied),
  stop and send the error back rather than retrying blindly — that's new
  information worth a look, not something to brute-force past.
