# StableMut@K + pairwise Kendall tau (RQ4.1) — raw tables

Generated: 2026-07-27T23:19:06.167448+00:00
Git commit: 2b3ff2c
Script: scripts/analyze_stability.py

Args: --results-dir data/results/dynamic  --out analysis/stability  --min-instantiations 2

## StableMut@K (mean Mut@K across instantiations, SD)

                                                 model_label  stable_mut_at_k  sd_mut_at_k  n_instantiations
                           Qwen__Qwen2.5-Coder-1.5B-Instruct         0.815858     0.042065                 5
Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep         0.694613     0.020123                 3
                            Qwen__Qwen2.5-Coder-32B-Instruct         0.955050     0.003353                 5
                             Qwen__Qwen2.5-Coder-7B-Instruct         0.924741     0.003804                 5
       Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_inst1         0.913725     0.009922                 3
                                   claude-haiku-4-5-20251001         0.956100     0.004645                 5
                                           claude-sonnet-4-6         0.955901     0.003574                 5
                                       gemini-3.1-flash-lite         0.953551     0.003559                 4
                                      gemini-3.1-pro-preview         0.973191     0.004201                 4

## StableMut@K by tier

                                                 model_label tier  stable_mut_at_k  sd_mut_at_k  n_instantiations
                           Qwen__Qwen2.5-Coder-1.5B-Instruct   L1         1.000000     0.000000                 5
                           Qwen__Qwen2.5-Coder-1.5B-Instruct   L2         0.782065     0.052221                 5
                           Qwen__Qwen2.5-Coder-1.5B-Instruct   L3         0.722222     0.392837                 2
Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep   L1         1.000000     0.000000                 3
Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep   L2         0.588802     0.063806                 3
Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep   L3         0.642857     0.235702                 2
                            Qwen__Qwen2.5-Coder-32B-Instruct   L1         0.995804     0.005778                 5
                            Qwen__Qwen2.5-Coder-32B-Instruct   L2         0.976195     0.003779                 5
                            Qwen__Qwen2.5-Coder-32B-Instruct   L3         0.916154     0.019587                 5
                            Qwen__Qwen2.5-Coder-32B-Instruct   L4         0.542179     0.036475                 5
                             Qwen__Qwen2.5-Coder-7B-Instruct   L1         1.000000     0.000000                 5
                             Qwen__Qwen2.5-Coder-7B-Instruct   L2         0.926021     0.004942                 5
                             Qwen__Qwen2.5-Coder-7B-Instruct   L3         0.849525     0.016609                 5
       Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_inst1   L1         1.000000     0.000000                 3
       Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_inst1   L2         0.892462     0.010097                 3
                                   claude-haiku-4-5-20251001   L1         0.986411     0.006941                 5
                                   claude-haiku-4-5-20251001   L2         0.973100     0.006717                 5
                                   claude-haiku-4-5-20251001   L3         0.928959     0.007751                 5
                                   claude-haiku-4-5-20251001   L4         0.871663     0.014557                 4
                                           claude-sonnet-4-6   L1         0.983123     0.000678                 5
                                           claude-sonnet-4-6   L2         0.970499     0.019433                 5
                                           claude-sonnet-4-6   L3         0.939472     0.013343                 5
                                           claude-sonnet-4-6   L4         0.828873     0.014977                 4
                                       gemini-3.1-flash-lite   L1         0.988117     0.003062                 4
                                       gemini-3.1-flash-lite   L2         0.976719     0.001307                 4
                                       gemini-3.1-flash-lite   L3         0.940342     0.008628                 4
                                       gemini-3.1-flash-lite   L4         0.881176     0.007363                 4
                                      gemini-3.1-pro-preview   L1         0.983772     0.001397                 4
                                      gemini-3.1-pro-preview   L2         0.973584     0.013150                 2
                                      gemini-3.1-pro-preview   L3         0.955980     0.006526                 4

## Pairwise Kendall tau between instantiation rankings (model-level Mut@K)

instantiation_a instantiation_b  n_models      tau  p_value
              1               2         9 0.888889 0.000243
              1               3         9 0.833333 0.000854
              1               4         7 0.428571 0.238889
              1               5         5 0.600000 0.233333
              2               3         9 0.722222 0.005886
              2               4         7 0.619048 0.069048
              2               5         5 0.800000 0.083333
              3               4         7 0.714286 0.030159
              3               5         5 0.600000 0.233333
              4               5         5 0.800000 0.083333

Mean pairwise tau: 0.701
