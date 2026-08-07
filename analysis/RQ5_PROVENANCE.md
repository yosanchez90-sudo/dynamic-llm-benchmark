# RQ5 / H6 — cross-benchmark validity (raw tables)

Generated: 2026-08-07T15:13:26.235916+00:00
Git commit: 21d80e1
Script: scripts/analyze_rq5.py

Per analysis/RQ5_ANALYSIS_PLAN.md (pre-registered 2026-07-27, before this
script's first run). Interpretation, once the public-benchmark pairs land,
belongs in a separate RQ5_INTERPRETATION.md (same split as Comparison C,
analysis/COMPARISON_C_INTERPRETATION.md) -- not embedded here.

## Model ranking table

                      model_label               model_short  dynamic_mutk_pooled  dynamic_bp_pooled  dynamic_n_pooled  ult_mutk   ult_bp  ult_n  dynamic_mutk_L1  dynamic_mutk_L2  dynamic_mutk_L3  dynamic_mutk_L4  public_score  public_score_hard public_benchmark                                           public_split public_eval_date                                                    public_source
                 gpt-5-2025-08-07          gpt-5-2025-08-07             0.960116           0.887333              1500  0.868811 0.697500    400         0.985487         0.990774         0.960990         0.911118           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
            gpt-5-mini-2025-08-07     gpt-5-mini-2025-08-07             0.958190           0.838000              1500  0.851139 0.547500    400         0.982875         0.990388         0.960842         0.896494           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                claude-sonnet-4-6         claude-sonnet-4-6             0.954187           0.703333              1500  0.755780 0.195000    400         0.983124         0.979042         0.943678         0.827469           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
        claude-haiku-4-5-20251001 claude-haiku-4-5-20251001             0.955328           0.502000              1500  0.801189 0.087500    400         0.986364         0.976215         0.929498         0.874541           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
           gemini-3.1-pro-preview    gemini-3.1-pro-preview             0.968545           0.939966               583  0.888442 0.732673    101         0.983824         0.977778         0.956195         0.895325           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
            gemini-3.1-flash-lite     gemini-3.1-flash-lite             0.953452           0.652500              1200  0.821318 0.265000    400         0.988021         0.976741         0.940100         0.881025           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
 Qwen__Qwen2.5-Coder-32B-Instruct                  Qwen 32B             0.955056           0.290667              1500  0.900857 0.077500    400         0.995833         0.976099         0.916413         0.546589          49.0               27.7     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-09-19 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
  Qwen__Qwen2.5-Coder-7B-Instruct                   Qwen 7B             0.924870           0.204000              1500  0.893750 0.017500    400         1.000000         0.926020         0.851142         0.540541          40.4               20.3     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-11-12 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
Qwen__Qwen2.5-Coder-1.5B-Instruct                 Qwen 1.5B             0.812977           0.052000              1500  0.406632 0.020000    400         1.000000         0.780746         0.722222              NaN          27.0                5.4     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-11-12 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results

## Correlations

                                       pair            metric_a          metric_b  n  pearson_r  pearson_r_ci_lo  pearson_r_ci_hi  pearson_p_perm  spearman_rho  spearman_rho_ci_lo  spearman_rho_ci_hi  spearman_p_perm  kendall_tau  kendall_tau_ci_lo  kendall_tau_ci_hi  kendall_p_perm
                    Dynamic(pooled) <-> ULT dynamic_mutk_pooled          ult_mutk  9   0.911693        -0.478376         0.993619        0.057694          0.35           -0.446429                 1.0         0.354965     0.333333              -0.25                1.0        0.253975
Dynamic(pooled) <-> public (Complete-split) dynamic_mutk_pooled      public_score  3   0.980997         0.980997         1.000000        0.169383          1.00            1.000000                 1.0         0.340766     1.000000               1.00                1.0        0.331167
            ULT <-> public (Complete-split)            ult_mutk      public_score  3   0.926517         0.926517         1.000000        0.169383          1.00            1.000000                 1.0         0.340766     1.000000               1.00                1.0        0.331167
    Dynamic(pooled) <-> public (Hard-split) dynamic_mutk_pooled public_score_hard  3   0.991719         0.991719         1.000000        0.169383          1.00            1.000000                 1.0         0.340766     1.000000               1.00                1.0        0.331167
                ULT <-> public (Hard-split)            ult_mutk public_score_hard  3   0.949466         0.949466         1.000000        0.169383          1.00            1.000000                 1.0         0.340766     1.000000               1.00                1.0        0.331167
