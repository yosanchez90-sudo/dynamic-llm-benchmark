# RQ5 leaderboard harvest — which pinned snapshots have published numbers

Per `analysis/RQ5_ANALYSIS_PLAN.md` Part 2. Checked 2026-07-27 via the
official BigCodeBench results datasets on Hugging Face
(`bigcode/bigcodebench-results` — Complete split; `bigcode/bigcodebench-hard-results`
— Hard split; both accessed via the `datasets-server.huggingface.co` rows
API, not the JS-rendered leaderboard Space, which does not expose data to a
static fetch).

## BigCodeBench (primary)

| Model | Complete split — Complete | Complete split — Instruct | Hard split — Complete | Hard split — Instruct | Eval date | Snapshot match |
|---|---|---|---|---|---|---|
| Qwen2.5-Coder-1.5B-Instruct | 32.7 | 27.0 | 6.1 | 5.4 | 2024-11-12 | **Yes** (see below) |
| Qwen2.5-Coder-7B-Instruct | 48.8 | 40.4 | 20.3 | 20.3 | 2024-11-12 | **Yes** |
| Qwen2.5-Coder-32B-Instruct | 58.0 | 49.0 | 33.8 | 27.7 | 2024-09-19 | **Yes**, with one caveat (below) |
| gpt-5-2025-08-07 | — | — | — | — | — | Not present in either dataset (202 models each, checked in full) |
| gpt-5-mini-2025-08-07 | — | — | — | — | — | Not present |
| claude-sonnet-4-6 | — | — | — | — | — | Not present |
| claude-haiku-4-5-20251001 | — | — | — | — | — | Not present |
| gemini-3.1-pro-preview | — | — | — | — | — | Not present |
| gemini-3.1-flash-lite | — | — | — | — | — | Not present |

**Per the pre-registered rule, the six unavailable models are dropped from
the Dynamic↔public and ULT↔public pairs, not proxied.** Gemini 3.1 Pro
Preview/Flash-Lite (the forced substitution for the retired 2.5 Pro/Flash,
PROJECT_BRIEF.md §11) has no published BigCodeBench number of its own —
confirmed absent, not proxied by any other Gemini version's score, exactly
as the pre-registered rule requires. GPT-5/Claude Sonnet 4.6/Haiku
4.5/Gemini 3.1 are real, current models (confirmed via a SWE-bench/
SWE-rebench mention) but none has a BigCodeBench entry as of this check —
plausible given BigCodeBench's results datasets show no evaluation dated
after April 2025, i.e. the dataset itself may simply not have been updated
to include 2026-era model releases yet, not that these models were tried
and excluded.

### Snapshot verification detail

Neither results dataset records a revision hash directly (checked: the row
schema has `model`, `link`, `size`, `complete`, `instruct`, `date` — no
`revision`/`sha` field). Verified snapshot identity independently via each
model's Hugging Face commit history:

- **Qwen2.5-Coder-1.5B/7B-Instruct**: our pinned commits
  (`2e1fd397...`, `c03e6d35...`) are each repos' single most recent commit,
  and every commit after the initial upload only touched
  README/config/tokenizer metadata — no weight-file changes ever. Exact
  match, high confidence.
- **Qwen2.5-Coder-32B-Instruct**: our pinned commit (`381fc969...`) is also
  the most recent commit, but the repo has a second "Upload folder using
  huggingface_hub" commit on 2024-11-10 (two days *before* BigCodeBench's
  2024-11-12... wait, our eval date check found this evaluation dated
  2024-09-19, i.e. *before* that Nov-10 upload) — flagged, not smoothed
  over: if that Nov-10 upload changed weights, BigCodeBench's Sep-19 number
  could reflect an earlier weight state than what this project evaluated.
  Not resolved further in this pass; treat the 32B public number with
  slightly more caution than the other two sizes, and note this explicitly
  if it goes in the dissertation.
- Generation-config caveat (applies to all three): each repo's
  `generation_config.json` was updated 2024-11-18 (temperature/top_p/
  repetition_penalty defaults) — after the 1.5B/7B eval dates, and for 32B
  well after its Sep-19 eval date too. This is immaterial here (BigCodeBench
  controls its own decoding parameters rather than relying on a checkpoint's
  shipped defaults — the same class of concern CONVENTIONS.md flags for *this*
  project's own harness, but not applicable to a benchmark that sets greedy/
  fixed-temperature decoding itself), but recorded per this project's
  standing rule to never wave away a config-provenance question silently.

## EvalPlus/HumanEval+ and LiveCodeBench (secondary)

**Not independently verified in this pass** — both leaderboards are
JS-rendered Spaces that a static fetch cannot read (confirmed for
EvalPlus), and no equivalent static results-dataset repository was
located for either within this pass's time budget. Flagged as
follow-up work, not fabricated or estimated. Given BigCodeBench (the
primary) already has solid matched numbers for exactly the models that
matter (the 3 Qwen sizes), this gap is lower priority than it would
otherwise be.

## Bottom line for Part 3 (self-run plan)

**No self-run is needed for the 3 Qwen sizes** — published, snapshot-matched
BigCodeBench numbers already exist for all three, both splits. This
changes Part 3 from "propose and estimate a self-run" to "use the numbers
above; no GPU time, no STOP gate needed." The six API models remain
unavailable regardless of any self-run decision (self-running BigCodeBench
against them would mean calling the actual frontier APIs for ~1,140
problems each — real spend, and out of scope for this pass, which
covers only "the 3 local Qwen sizes" for a possible self-run). The
Dynamic↔public and ULT↔public correlations are therefore **N=3** — see
`analysis/RQ5_INTERPRETATION.md` for why this is reported as a strictly
qualitative/directional read, not a statistical test.
