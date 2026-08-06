# Gemini 3.1 Pro Preview — daily self-chaining crawl

Written 2026-08-05. Closes the remaining Gemini Pro Preview Dynamic-benchmark
coverage gap (instantiations 1-4 only — inst5 was cut from this model's
target scope 2026-07-15, per `PROJECT_BRIEF.md` §11 and the "N=4 scope"
comment already on every `gemini_3_1_pro_preview__dynamic_*.yaml` config).

## Why a self-chaining SLURM job, not scrontab

`scrontab` is disabled on Kelvin2 (confirmed directly: `scrontab -l` →
`"scrontab is disabled on this cluster"`). Fallback: a SLURM job that
resubmits itself with `sbatch --begin=now+24hours` after each day's run,
per `scripts/slurm/run_gemini_daily_crawl.slurm`.

## What's missing and how it's prioritized

Live count as of 2026-08-05 (`scripts/check_gemini_pro_crawl_done.py`):
**655 problems missing** across instantiations 1-4. **L4 is completely
empty (0/75 in all four instantiations, 300 of the 655)** — the single
biggest, most distorting gap, since a model with zero rows at a tier can't
appear in any per-tier or tier-gradient analysis at all and skews every
pooled ranking it's absent from (`RQ5_INTERPRETATION.md`).

| Tier | inst1 | inst2 | inst3 | inst4 | Missing |
|---|---|---|---|---|---|
| L1 | 0 | 0 | 10 | 12 | 22 |
| L2 | 0 | 47 | 75 | 75 | 197 |
| L3 | 32 | 32 | 36 | 36 | 136 |
| L4 | 75 | 75 | 75 | 75 | **300** |

`scripts/run_gemini_daily_crawl.py` processes all four `..._L3L4__inst{1-4}.yaml`
configs first (with `tier_priority=["L4"]`, so within each config L4
problems are generated before L3), then the four `..._L1L2__inst{1-4}.yaml`
configs. Every config call is resume-safe (`test_gen_runner.py`'s existing
tier-aware resume matcher) — re-running the same config, whether later the
same day or in tomorrow's chained job, only ever requests problems not
already on disk. Nothing is re-sent, nothing is double-charged against the
daily quota.

## Code changes this required

- **`src/eval/test_gen_runner.py`**: two small, generic, opt-in additions
  to `run_test_gen_experiment` — `config["tier_priority"]` (stable-sorts
  loaded problems so listed tiers come first) and `config["max_requests"]`
  (caps a single call to at most N new requests, leaving the rest for a
  future resumed call). Both no-ops when absent, so every existing config's
  behaviour is unchanged — verified via the existing test suite
  (`tests/test_gen_runner_resume.py`, `tests/test_runner_benchmark_dispatch.py`,
  9/9 passing after the change).
- **`src/models/gemini_model.py`**: `runtime_info` now also logs
  `model_version`/`model_status` from the Gemini SDK's own response object
  (`GenerateContentResponse.model_version`/`.model_status`, confirmed to
  exist on the installed `google-genai` SDK). This is the audit trail for
  preview-endpoint drift — `gemini-3.1-pro-preview` is an alias that can
  point to a different underlying checkpoint over multiple days of
  crawling, and without this field that drift would be invisible in the
  logged data.
- **`scripts/run_gemini_daily_crawl.py`** (new): one day's worth of the
  crawl — budget-capped (240/day, a buffer under the real 250 quota),
  priority-ordered, catches Gemini's `APIError` on a 429 specifically and
  stops cleanly (not a crash) with whatever completed already safely on
  disk (`append_jsonl` never overwrites). Any other exception still
  propagates — a real error, not an expected daily-limit stop.
- **`scripts/check_gemini_pro_crawl_done.py`** (new): exit 0 if the
  inst1-4 × L1-L4 target is fully covered, exit 1 (printing what's still
  missing) otherwise. Used by the SLURM script to decide whether to
  resubmit.
- **`scripts/slurm/run_gemini_daily_crawl.slurm`** (new): runs one day's
  crawl, checks completion, resubmits itself `+24h` if incomplete or stops
  the chain if complete. CPU-only (`k2-medpri`, the same partition already
  used for every other Gemini API-model job in this project, e.g.
  `run_eval_api.slurm`) — this is API calls, not GPU/CPU model compute, so
  no GPU partition is needed or used.

## Wall-clock sanity check (real measured data, not guessed)

Gemini Pro Preview's own real logged `generation_latency_seconds`
(n_problems=545 existing rows): mean 31.0s/problem (p25=14.8s, median=20.0s,
p75=37.3s). 240 sequential generation calls ≈ 2.1 hours; with mutation
scoring layered on top (parallelized across 4 workers, using this
project's existing 1.6x wall-clock convention for scoring overhead —
`scripts/estimate_cost.py`'s own assumption 5) ≈ **3.3 hours**, comfortably
inside the SLURM script's 6-hour time limit.

## Expected completion

**Best case: 3 daily runs** (655 ÷ 240 ≈ 2.73, rounds up to 3) — if the
first link is submitted 2026-08-05, that's as early as **2026-08-07
evening / 2026-08-08**. **Realistic range: 3-5 days** — the daily budget
assumes a clean 240-request day every time, but the actual Google-side
quota reset doesn't necessarily align exactly with this job's 24h
resubmit cadence (a day could hit its 429 wall earlier than expected if
the reset window has already partially drained from a prior day's job
running late, or the SLURM queue delays a resubmission past its
`--begin` time under load).

## Starting the chain (not done in this pass — no API calls were made)

```bash
env -u BASH_ENV sbatch scripts/slurm/run_gemini_daily_crawl.slurm
```

**Check progress** (one line):

```bash
python scripts/check_gemini_pro_crawl_done.py
```

**Check the chain is still alive** (one line):

```bash
squeue -u $USER --name=gemini-pro-daily-crawl
```
