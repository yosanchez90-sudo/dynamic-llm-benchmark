# Stability (RQ4.1) — raw tables

Generated: 2026-08-12T00:05:42.210985+00:00
Git commit: ce774c2
Script: scripts/analyze_stability.py

**Interpretation lives in `analysis/STABILITY_INTERPRETATION.md`**
(hand-written, not touched by this script) — this file is the regenerable
raw-tables companion; re-run this script freely after new data lands. Any
number quoted from this file elsewhere (e.g. RQ5's disattenuation
correction) is only current as of the commit above, not frozen.

Args: --results-dir data/results/dynamic  --out analysis/stability  --min-instantiations 2
Canonical models only (9); excluded non-canonical
model_label(s): ['Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep', 'Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_inst1', 'bigcode__starcoder2-15b-instruct-v0.1', 'codellama__CodeLlama-13b-Instruct-hf', 'deepseek-ai__deepseek-coder-6.7b-instruct', 'mistralai__Mistral-7B-Instruct-v0.3']

## StableMut@K (mean Mut@K across instantiations, SD)

                      model_label  stable_mut_at_k  sd_mut_at_k  n_instantiations
Qwen__Qwen2.5-Coder-1.5B-Instruct         0.815858     0.042065                 5
 Qwen__Qwen2.5-Coder-32B-Instruct         0.955050     0.003353                 5
  Qwen__Qwen2.5-Coder-7B-Instruct         0.924741     0.003804                 5
        claude-haiku-4-5-20251001         0.955334     0.003907                 5
                claude-sonnet-4-6         0.954239     0.002966                 5
            gemini-3.1-flash-lite         0.953551     0.003559                 4
           gemini-3.1-pro-preview         0.959604     0.000570                 4
                 gpt-5-2025-08-07         0.960076     0.002314                 5
            gpt-5-mini-2025-08-07         0.958190     0.001344                 5

## StableMut@K by tier

                      model_label tier  stable_mut_at_k  sd_mut_at_k  n_instantiations
Qwen__Qwen2.5-Coder-1.5B-Instruct   L1         1.000000     0.000000                 5
Qwen__Qwen2.5-Coder-1.5B-Instruct   L2         0.782065     0.052221                 5
Qwen__Qwen2.5-Coder-1.5B-Instruct   L3         0.722222     0.392837                 2
 Qwen__Qwen2.5-Coder-32B-Instruct   L1         0.995804     0.005778                 5
 Qwen__Qwen2.5-Coder-32B-Instruct   L2         0.976195     0.003779                 5
 Qwen__Qwen2.5-Coder-32B-Instruct   L3         0.916154     0.019587                 5
 Qwen__Qwen2.5-Coder-32B-Instruct   L4         0.542179     0.036475                 5
  Qwen__Qwen2.5-Coder-7B-Instruct   L1         1.000000     0.000000                 5
  Qwen__Qwen2.5-Coder-7B-Instruct   L2         0.926021     0.004942                 5
  Qwen__Qwen2.5-Coder-7B-Instruct   L3         0.849525     0.016609                 5
        claude-haiku-4-5-20251001   L1         0.986411     0.006941                 5
        claude-haiku-4-5-20251001   L2         0.976217     0.001895                 5
        claude-haiku-4-5-20251001   L3         0.929282     0.008103                 5
        claude-haiku-4-5-20251001   L4         0.875139     0.014810                 5
                claude-sonnet-4-6   L1         0.983123     0.000678                 5
                claude-sonnet-4-6   L2         0.979062     0.001884                 5
                claude-sonnet-4-6   L3         0.943717     0.005849                 5
                claude-sonnet-4-6   L4         0.828275     0.013040                 5
            gemini-3.1-flash-lite   L1         0.988117     0.003062                 4
            gemini-3.1-flash-lite   L2         0.976719     0.001307                 4
            gemini-3.1-flash-lite   L3         0.940342     0.008628                 4
            gemini-3.1-flash-lite   L4         0.881176     0.007363                 4
           gemini-3.1-pro-preview   L1         0.984981     0.001170                 4
           gemini-3.1-pro-preview   L2         0.980265     0.001815                 4
           gemini-3.1-pro-preview   L3         0.956093     0.001493                 4
           gemini-3.1-pro-preview   L4         0.918941     0.002670                 4
                 gpt-5-2025-08-07   L1         0.985481     0.003231                 5
                 gpt-5-2025-08-07   L2         0.990686     0.002183                 5
                 gpt-5-2025-08-07   L3         0.961006     0.004096                 5
                 gpt-5-2025-08-07   L4         0.911122     0.001328                 5
            gpt-5-mini-2025-08-07   L1         0.982852     0.002283                 5
            gpt-5-mini-2025-08-07   L2         0.990440     0.002997                 5
            gpt-5-mini-2025-08-07   L3         0.960710     0.005183                 5
            gpt-5-mini-2025-08-07   L4         0.896360     0.004837                 5

## Pairwise Kendall tau between instantiation rankings (model-level Mut@K)

instantiation_a instantiation_b  n_models      tau  p_value
              1               2         9 0.888889 0.000243
              1               3         9 0.555556 0.044615
              1               4         9 0.500000 0.075176
              1               5         7 0.428571 0.238889
              2               3         9 0.444444 0.119439
              2               4         9 0.611111 0.024741
              2               5         7 0.333333 0.381349
              3               4         9 0.500000 0.075176
              3               5         7 0.904762 0.002778
              4               5         7 0.523810 0.136111

N=4 (pairs among instantiations ['1', '2', '3', '4'], headline scope) mean pairwise tau: 0.583
All-pairs mean pairwise tau (incl. instantiation 5): 0.569

## Holm-Bonferroni within RQ4/H5 (PROJECT_BRIEF.md Sec 3.1)

Two SEPARATE corrections (not one 16-test family): the N=4 set (6 pairs
among instantiations 1-4, the headline scope) and the all-pairs set (10
pairs, including instantiation 5) are corrected independently, since they
are two different reported scopes, not one pooled family.

### N=4 set (6 pairs)

instantiation_a instantiation_b  n_models      tau  p_value  p_value_holm
              1               2         9 0.888889 0.000243      0.001455
              1               3         9 0.555556 0.044615      0.178461
              1               4         9 0.500000 0.075176      0.225529
              2               3         9 0.444444 0.119439      0.225529
              2               4         9 0.611111 0.024741      0.123705
              3               4         9 0.500000 0.075176      0.225529

Significant at raw p<0.05: 3/6. Significant at Holm-adjusted p<0.05: **1/6**.

### All-pairs set (10 pairs, corrected separately from the N=4 set above)

instantiation_a instantiation_b  n_models      tau  p_value  p_value_holm
              1               2         9 0.888889 0.000243      0.002425
              1               3         9 0.555556 0.044615      0.312307
              1               4         9 0.500000 0.075176      0.451058
              1               5         7 0.428571 0.238889      0.477778
              2               3         9 0.444444 0.119439      0.477756
              2               4         9 0.611111 0.024741      0.197928
              2               5         7 0.333333 0.381349      0.477778
              3               4         9 0.500000 0.075176      0.451058
              3               5         7 0.904762 0.002778      0.025000
              4               5         7 0.523810 0.136111      0.477756

Significant at raw p<0.05: 4/10. Significant at Holm-adjusted p<0.05: **2/10**.
