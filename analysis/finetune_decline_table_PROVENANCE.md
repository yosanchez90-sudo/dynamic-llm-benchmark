# Held-out execution-rate decline table (epoch 0 vs epoch 30) — raw table

Generated: 2026-09-01T23:45:32.421755+00:00
Git commit: 8611e4e
Script: scripts/build_finetune_decline_table.py

Companion to `analysis/finetune_endpoint_table.csv` (baseline_pass_rate,
seen vs fresh, epoch 30 only). This table tracks `exec_rate`, whether
the generated suite runs at all, independent of correctness, on the
held-out (unseen inst2/3) split from epoch 0 to epoch 30, per condition.

Source glob: data/results/finetune_rebuild/epoch_perf_*.csv

## Decline table

model       condition   exec_rate_unseen_epoch0_greedy_pct  exec_rate_unseen_epoch30_greedy_pct  exec_rate_unseen_decline_pp_greedy  exec_rate_unseen_epoch30_sampling_mean_pct  exec_rate_unseen_epoch30_sampling_sd_pct
Qwen 1.5B   inst1                 92.7            94.7            -2.0            95.4             0.5
Qwen 1.5B   bp_own                92.7            92.3             0.3            89.9             0.8
Qwen 1.5B   bp_gpt5               92.7            63.3            29.3            62.8             3.5
Qwen 7B     inst1                 99.7            99.0             0.7            98.4             0.2
Qwen 7B     bp_own                99.7           100.0            -0.3            99.7             0.3
Qwen 7B     bp_gpt5               99.7            85.3            14.3            86.8             1.3
