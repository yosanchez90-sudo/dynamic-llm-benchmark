# Fine-tune endpoint table (epoch 30, n_problems=150) — raw table

Generated: 2026-08-12T00:05:43.342361+00:00
Git commit: ce774c2
Script: scripts/build_finetune_endpoint_table.py

This is the regenerable raw-table companion to the hand-written
`analysis/FINETUNE_ENDPOINT_PROVENANCE.md` (methodology/interpretation,
not touched by this script) -- re-run this script freely after new
data lands in `data/results/finetune_rebuild/`.

Source glob: data/results/finetune_rebuild/epoch_perf_*.csv

## Endpoint table

model                   condition                      epoch             n  split                   baseline_pass_greedy_pct  baseline_pass_sampling_mean_pct  baseline_pass_sampling_sd_pct  n_sampling_draws  baseline_pass_gap_pp_greedy  baseline_pass_gap_pp_sampling_mean
Qwen 1.5B               inst1                             30           150  seen (inst1)                    10.0          10.7           0.0             3           2.3           2.6
Qwen 1.5B               inst1                             30           150  unseen (mean inst2/3)            7.7           8.1           0.7             3           2.3           2.6
Qwen 1.5B               bp_own                            30           150  seen (inst1)                    27.3          25.6           1.4             3           8.7           7.0
Qwen 1.5B               bp_own                            30           150  unseen (mean inst2/3)           18.7          18.6           1.0             3           8.7           7.0
Qwen 1.5B               bp_gpt5                           30           150  seen (inst1)                    54.0          53.3           2.4             3          52.7          51.7
Qwen 1.5B               bp_gpt5                           30           150  unseen (mean inst2/3)            1.3           1.7           0.6             3          52.7          51.7
Qwen 7B                 inst1                             30           150  seen (inst1)                    31.3          31.6           0.4             3          -2.3          -1.0
Qwen 7B                 inst1                             30           150  unseen (mean inst2/3)           33.7          32.6           0.8             3          -2.3          -1.0
Qwen 7B                 bp_own                            30           150  seen (inst1)                    60.0          60.7           0.7             3           4.7           5.4
Qwen 7B                 bp_own                            30           150  unseen (mean inst2/3)           55.3          55.2           1.4             3           4.7           5.4
Qwen 7B                 bp_gpt5                           30           150  seen (inst1)                    80.0          79.8           0.8             3          68.0          65.8
Qwen 7B                 bp_gpt5                           30           150  unseen (mean inst2/3)           12.0          14.0           1.5             3          68.0          65.8
