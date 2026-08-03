# Comparison C — canonical 2x3 DiD results (raw tables)

Generated: 2026-08-03T19:05:15.641637+00:00
Git commit: 5a56a97
Script: scripts/analyze_comparison_c.py

**Interpretation lives in `analysis/COMPARISON_C_INTERPRETATION.md`**
(hand-written, not touched by this script) — this file is the regenerable
raw-tables companion; re-run this script freely after new data lands.

Per analysis/COMPARISON_C_ANALYSIS_PLAN.md (pre-registered 2026-07-26,
amended same day for Dynamic-arm tier composition, both before this script's
first run). Primary metric: baseline_pass_rate. Mut@K reported alongside,
secondary (see PRE-data-sparsity note in the analysis plan).

## Sources

- PRE ULT/PLT/Dynamic: base Qwen-1.5B, already-landed (2026-07-13/06-09).
- POST ULT: Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__ult__zero_shot__instcore_400__20260726T142439.jsonl (Stage 3a).
- POST PLT: Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__plt__zero_shot__instcore_400__20260726T224725.jsonl (Stage 3b).
- POST Dynamic: 6 files, inst1-3 x {L1L2,L3L4} (Stage 3b).
- Seen/unseen split: data/raw/ult_plt/comparison_c_seen_manifest.json (frozen).

## Primary DiD (vs Dynamic-L4, CC-matched control)

 benchmark  pre_mean  post_mean    delta  control_delta      did  did_ci_lo  did_ci_hi  n_pre  n_post  n_pre_control  n_post_control    control
  seen_ult  0.008929   1.000000 0.991071            0.0 0.991071   0.973214   1.000000    112     112            225             225 dynamic_l4
unseen_ult  0.024306   0.180556 0.156250            0.0 0.156250   0.111111   0.204861    288     288            225             225 dynamic_l4
       plt  0.075000   0.300000 0.225000            0.0 0.225000   0.172500   0.275000    400     400            225             225 dynamic_l4

## Robustness DiD (vs Dynamic-L1-L3 pooled, headroom control)

 benchmark  pre_mean  post_mean    delta  control_delta      did  did_ci_lo  did_ci_hi  n_pre  n_post  n_pre_control  n_post_control      control
  seen_ult  0.008929   1.000000 0.991071       0.087407 0.903664   0.865106   0.940741    112     112            675             675 dynamic_l1l3
unseen_ult  0.024306   0.180556 0.156250       0.087407 0.068843   0.013330   0.129769    288     288            675             675 dynamic_l1l3
       plt  0.075000   0.300000 0.225000       0.087407 0.137593   0.077130   0.201211    400     400            675             675 dynamic_l1l3

## Four-level gradient (raw gain, no control subtraction)

   benchmark  n_pre  n_post  pre_mean  post_mean     gain  gain_ci_lo  gain_ci_hi
    seen_ult    112     112  0.008929   1.000000 0.991071    0.973214    1.000000
  unseen_ult    288     288  0.024306   0.180556 0.156250    0.107639    0.204861
         plt    400     400  0.075000   0.300000 0.225000    0.172500    0.277500
  dynamic_l4    225     225  0.000000   0.000000 0.000000    0.000000    0.000000
dynamic_l1l3    675     675  0.066667   0.154074 0.087407    0.056296    0.120000

## Mut@K (secondary; n_mut_defined shows how much of n_total this covers)

   benchmark  n_total  n_mut_defined  mut_at_k side
    seen_ult      112              1  0.885714  pre
  unseen_ult      288              7  0.338192  pre
         plt      400             30  0.594996  pre
  dynamic_l4      225              0       NaN  pre
dynamic_l1l3      675             45  0.816779  pre
    seen_ult      112            112  0.437699 post
  unseen_ult      288             52  0.138737 post
         plt      400            120  0.259132 post
  dynamic_l4      225              0       NaN post
dynamic_l1l3      675            104  0.693866 post
