# RQ5 cross-family extension -- correlations (raw tables)

Generated: 2026-08-07T15:19:38.499845+00:00
Git commit: 21d80e1
Script: scripts/analyze_rq5_cross_family.py

Per `analysis/RQ5_CROSS_FAMILY_PROPOSAL.md` (approved 2026-07-28). This is a
POST-HOC, supplementary extension -- `analysis/RQ5_PROVENANCE.md`
(canonical 9 models, `scripts/analyze_rq5.py`) remains the pre-registered
RQ5 primary result and is NOT modified or superseded by anything here.
Cross-family models are never part of `coverage_matrix.py::CANONICAL_MODELS`
and never enter Comparison A/B or StableMut@K (see
`tests/test_canonical_models_boundary.py`).

## Cross-family data completeness at time of this run

- DeepSeek-6.7B: Dynamic COMPLETE, ULT COMPLETE
- CodeLlama-13B: Dynamic COMPLETE, ULT COMPLETE
- StarCoder2-15B: Dynamic COMPLETE, ULT COMPLETE
- Mistral-7B: Dynamic COMPLETE, ULT COMPLETE

**If any model above is PARTIAL or MISSING, every "canonical+cross-family"
correlation below is provisional** -- re-run this script once all 4
candidates' Dynamic + ULT jobs complete (see
`data/download_logs/rq5_cross_family_job_map_20260728.md` for job IDs) and
treat only a run with all 4 COMPLETE as the number that answers the
supervisor's bottom-up validity question.

## Model ranking table (n_defined flags cells too thin to quote, n_defined<20)

                              model_label               model_short       family  dynamic_n_total  dynamic_n_defined  dynamic_mutk_pooled  dynamic_bp_pooled  ult_n_total  ult_n_defined  ult_mutk   ult_bp  dynamic_coverage_adj  ult_coverage_adj  dynamic_thin  ult_thin  public_score  public_score_hard public_benchmark                                           public_split public_eval_date                                                    public_source
                         gpt-5-2025-08-07          gpt-5-2025-08-07    canonical             1500               1331             0.960116           0.887333          400            279  0.868811 0.697500              0.851943          0.605996         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                    gpt-5-mini-2025-08-07     gpt-5-mini-2025-08-07    canonical             1500               1257             0.958190           0.838000          400            219  0.851139 0.547500              0.802963          0.465999         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                        claude-sonnet-4-6         claude-sonnet-4-6    canonical             1500               1055             0.954187           0.703333          400             78  0.755780 0.195000              0.671112          0.147377         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                claude-haiku-4-5-20251001 claude-haiku-4-5-20251001    canonical             1500                753             0.955328           0.502000          400             35  0.801189 0.087500              0.479575          0.070104         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                   gemini-3.1-pro-preview    gemini-3.1-pro-preview    canonical              583                548             0.968545           0.939966          101             74  0.888442 0.732673              0.910399          0.650938         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
                    gemini-3.1-flash-lite     gemini-3.1-flash-lite    canonical             1200                783             0.953452           0.652500          400            106  0.821318 0.265000              0.622128          0.217649         False     False           NaN                NaN              NaN                                                    NaN              NaN                                                              NaN
         Qwen__Qwen2.5-Coder-32B-Instruct                  Qwen 32B    canonical             1500                436             0.955056           0.290667          400             31  0.900857 0.077500              0.277603          0.069816         False     False          49.0               27.7     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-09-19 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
          Qwen__Qwen2.5-Coder-7B-Instruct                   Qwen 7B    canonical             1500                306             0.924870           0.204000          400              7  0.893750 0.017500              0.188674          0.015641         False      True          40.4               20.3     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-11-12 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
        Qwen__Qwen2.5-Coder-1.5B-Instruct                 Qwen 1.5B    canonical             1500                 78             0.812977           0.052000          400              8  0.406632 0.020000              0.042275          0.008133         False      True          27.0                5.4     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-11-12 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
deepseek-ai__deepseek-coder-6.7b-instruct             DeepSeek-6.7B cross_family              300                 46             0.954611           0.153333          400             25  0.657325 0.062500              0.146374          0.041083         False     False          35.5               10.1     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2023-10-28 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
     codellama__CodeLlama-13b-Instruct-hf             CodeLlama-13B cross_family              300                 44             0.876221           0.146667          400              8  0.604564 0.020000              0.128512          0.012091         False      True          28.5                9.5     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2023-08-25 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
    bigcode__starcoder2-15b-instruct-v0.1            StarCoder2-15B cross_family              300                 75             0.918533           0.250000          400             56  0.553557 0.140000              0.229633          0.077498         False     False          37.6               12.2     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-04-30 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results
      mistralai__Mistral-7B-Instruct-v0.3                Mistral-7B cross_family              300                  5             0.935000           0.016667          400              1  0.931034 0.002500              0.015583          0.002328          True      True          19.5                4.7     BigCodeBench Complete-split/Instruct-prompt (+ Hard-split/Instruct)       2024-05-22 bigcode/bigcodebench-results + bigcode/bigcodebench-hard-results

## Correlations: canonical-only vs canonical+cross-family, side by side

                                                                    pair                  scope             metric_a          metric_b  n  pearson_r  pearson_r_ci_lo  pearson_r_ci_hi  pearson_p_perm  spearman_rho  spearman_rho_ci_lo  spearman_rho_ci_hi  spearman_p_perm  kendall_tau  kendall_tau_ci_lo  kendall_tau_ci_hi  kendall_p_perm  kendall_p_perm_holm
                                     Dynamic(pooled) <-> ULT [raw Mut@K]         canonical-only  dynamic_mutk_pooled          ult_mutk  9   0.911693        -0.478376         0.993619        0.057694      0.350000           -0.446429            1.000000         0.354965     0.333333          -0.250000           1.000000        0.253975             1.000000
                                     Dynamic(pooled) <-> ULT [raw Mut@K] canonical+cross-family  dynamic_mutk_pooled          ult_mutk 13   0.785874        -0.059265         0.947821        0.003000      0.483516           -0.164345            0.883457         0.101290     0.384615          -0.085969           0.777854        0.074293             0.594341
                             Dynamic(pooled) <-> ULT [coverage-adjusted]         canonical-only dynamic_coverage_adj  ult_coverage_adj  9   0.882689         0.780254         0.983933        0.003000      0.983333            0.818182            1.000000         0.000100     0.944444           0.724138           1.000000        0.000200             0.002200
                             Dynamic(pooled) <-> ULT [coverage-adjusted] canonical+cross-family dynamic_coverage_adj  ult_coverage_adj 13   0.896059         0.793154         0.980520        0.000100      0.972527            0.849151            1.000000         0.000100     0.897436           0.725932           1.000000        0.000100             0.001200
        Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]         canonical-only  dynamic_mutk_pooled      public_score  3   0.980997         0.980997         1.000000        0.169383      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167             1.000000
        Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K] canonical+cross-family  dynamic_mutk_pooled      public_score  7   0.461405        -0.134811         0.986379        0.310769      0.464286           -0.584906            1.000000         0.306269     0.428571          -0.335294           1.000000        0.241276             1.000000
Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]         canonical-only dynamic_coverage_adj      public_score  3   0.999891         0.999891         1.000000        0.169383      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167             1.000000
Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted] canonical+cross-family dynamic_coverage_adj      public_score  7   0.946262         0.814270         0.998376        0.000700      0.964286            0.565217            1.000000         0.002500     0.904762           0.555556           1.000000        0.003400             0.033997
                    ULT <-> public (Complete-split/Instruct) [raw Mut@K]         canonical-only             ult_mutk      public_score  3   0.926517         0.926517         1.000000        0.169383      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167             1.000000
                    ULT <-> public (Complete-split/Instruct) [raw Mut@K] canonical+cross-family             ult_mutk      public_score  7   0.242563        -0.687390         0.956749        0.610039      0.142857           -0.764706            1.000000         0.782422     0.238095          -0.647059           1.000000        0.569743             1.000000
            ULT <-> public (Complete-split/Instruct) [coverage-adjusted]         canonical-only     ult_coverage_adj      public_score  3   0.859179         0.859179         1.000000        0.511749      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167             1.000000
            ULT <-> public (Complete-split/Instruct) [coverage-adjusted] canonical+cross-family     ult_coverage_adj      public_score  7   0.747140         0.311561         0.987193        0.052795      0.821429            0.058824            1.000000         0.034297     0.714286           0.058824           1.000000        0.031697             0.285271
            Dynamic(pooled) <-> public (Hard-split/Instruct) [raw Mut@K]         canonical-only  dynamic_mutk_pooled public_score_hard  3   0.991719         0.991719         1.000000        0.169383      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167                  NaN
            Dynamic(pooled) <-> public (Hard-split/Instruct) [raw Mut@K] canonical+cross-family  dynamic_mutk_pooled public_score_hard  7   0.505150        -0.175479         0.938577        0.240776      0.464286           -0.584906            1.000000         0.306269     0.428571          -0.335294           1.000000        0.241276                  NaN
                        ULT <-> public (Hard-split/Instruct) [raw Mut@K]         canonical-only             ult_mutk public_score_hard  3   0.949466         0.949466         1.000000        0.169383      1.000000            1.000000            1.000000         0.340766     1.000000           1.000000           1.000000        0.331167                  NaN
                        ULT <-> public (Hard-split/Instruct) [raw Mut@K] canonical+cross-family             ult_mutk public_score_hard  7   0.515856        -0.523106         0.975775        0.256874      0.142857           -0.764706            1.000000         0.782422     0.238095          -0.647059           1.000000        0.569743                  NaN

## Holm-Bonferroni within RQ5/H6 (PROJECT_BRIEF.md Sec 3.1)

Scoped to the 12 headline Kendall-tau tests this project's
own interpretation (`analysis/RQ5_INTERPRETATION.md`) actually narrates:
3 benchmark pairs (Dynamic<->ULT, Dynamic<->public Complete-split,
ULT<->public Complete-split) x 2 scopes (canonical-only, canonical+
cross-family) x 2 metric versions (raw Mut@K, coverage-adjusted).
Hard-split pairs are a secondary consistency check, excluded from this
family on that basis, not silently.

                                                                    pair                  scope  kendall_tau  kendall_p_perm  kendall_p_perm_holm
                                     Dynamic(pooled) <-> ULT [raw Mut@K]         canonical-only     0.333333        0.253975             1.000000
                                     Dynamic(pooled) <-> ULT [raw Mut@K] canonical+cross-family     0.384615        0.074293             0.594341
                             Dynamic(pooled) <-> ULT [coverage-adjusted]         canonical-only     0.944444        0.000200             0.002200
                             Dynamic(pooled) <-> ULT [coverage-adjusted] canonical+cross-family     0.897436        0.000100             0.001200
        Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]         canonical-only     1.000000        0.331167             1.000000
        Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K] canonical+cross-family     0.428571        0.241276             1.000000
Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]         canonical-only     1.000000        0.331167             1.000000
Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted] canonical+cross-family     0.904762        0.003400             0.033997
                    ULT <-> public (Complete-split/Instruct) [raw Mut@K]         canonical-only     1.000000        0.331167             1.000000
                    ULT <-> public (Complete-split/Instruct) [raw Mut@K] canonical+cross-family     0.238095        0.569743             1.000000
            ULT <-> public (Complete-split/Instruct) [coverage-adjusted]         canonical-only     1.000000        0.331167             1.000000
            ULT <-> public (Complete-split/Instruct) [coverage-adjusted] canonical+cross-family     0.714286        0.031697             0.285271

Significant at raw p<0.05: 4/12. Significant at Holm-adjusted p<0.05: **3/12**.
