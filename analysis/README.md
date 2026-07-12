# Contamination notice: `epoch_perf_finetune_*.csv`

**Four of the six files in this directory were measured under a generation
config that fabricated a near-total collapse. Do not use them as the
"post-fine-tune" numbers for Comparison C. Do not edit or delete them —
append-only applies to this quarantine too — this notice is the correction,
not a rewrite of the data.**

## Which files, and why

| File | Status |
|---|---|
| `epoch_perf_finetune_qwen1_5b_bp_own_30ep.csv` | **Contaminated** |
| `epoch_perf_finetune_qwen1_5b_bp_gpt5_30ep.csv` | **Contaminated** |
| `epoch_perf_finetune_qwen7b_bp_own_30ep.csv` | **Contaminated** |
| `epoch_perf_finetune_qwen7b_bp_gpt5_30ep.csv` | **Contaminated** |
| `epoch_perf_finetune_qwen1_5b_inst1_30ep.csv` | Unaffected (measured 2026-06-28/29, before the bug existed) |
| `epoch_perf_finetune_qwen7b_inst1_30ep.csv` | Unaffected (measured 2026-06-28/29, before the bug existed) |
| `stability_*.csv` | Unrelated — Dynamic-benchmark data via `src/models/local.py`, which never used the setting below |

## Root cause

`scripts/eval_checkpoints.py` carried an uncommitted change (added
2026-07-07, sitting in the working tree until 2026-07-12) that passed
`no_repeat_ngram_size=4` to `model.generate()`. HuggingFace's
`NoRepeatNGramLogitsProcessor` applies over the **full** sequence, prompt
included. The system prompt (`src/data/test_gen.py:SYSTEM_INSTRUCTION`)
contains the literal phrase `` `from under_test import <function_name>` ``
as a formatting instruction. Any checkpoint that correctly followed that
instruction had its own mandatory first line corrupted — writing it again
tripped the n-gram repeat ban, forcing a wrong token in its place
(`from under_testimport format_value`, `from under_test imporformat_value`,
etc.), which broke the Python syntax and failed the exec gate on nearly
every problem.

Confirmed at n=50: 0/50 clean import lines with `no_repeat_ngram_size=4`
enabled vs 50/50 with it disabled, reproduced under both greedy and
sampling decoding, independent of `repetition_penalty`. This single setting
explains the entire recorded collapse in `bp_own` (both sizes, which turned
out to have been healthy the whole time) and the great majority of it in
`bp_gpt5` (both sizes, which have a smaller genuine residual fragility —
see below).

The wall-clock stopping criteria that was added alongside it (guarding
against a checkpoint that never emits EOS) was solving a **real** problem —
job `9315777` (2026-07-05, the original `bp_gpt5`/7B sweep) genuinely hung
for ~11.5 hours at epoch 5/instantiation 1 before SLURM killed it at the
12-hour limit — and was kept, with its timeout resized from an inherited
45s to an empirically-justified 240s (see `scripts/eval_checkpoints.py`'s
module docstring for the measurement).

## Date range

- Contaminated sweeps: 2026-07-05 (original) and 2026-07-09 (partial
  re-runs) through 2026-07-12, all using the uncommitted, unfixed script.
- Bug fixed and committed: 2026-07-12.

## Where the corrected data lives

`data/results/finetune_rebuild/epoch_perf_*.csv`, written by the patched
`scripts/eval_checkpoints.py` (no `no_repeat_ngram_size`, sized wall-clock
guard, full resolved generation config logged into every row, including a
`draw` column since each (epoch, instantiation) cell can now carry both a
greedy draw and several sampling draws). `src/Contamination/data.py`
defaults to this location.

## Why this is here instead of just fixed silently

This quarantine-with-explanation is itself part of the reproducibility
record: a measurement artifact was found, explained with evidence
(including cross-referencing to the exact SLURM job that hung), and
isolated without touching the original data. See the investigation's
diagnostic scripts (`scripts/diagnose_collapse*.py`) and their outputs
(`data/results/debug_collapse/`) for the full evidence chain.
