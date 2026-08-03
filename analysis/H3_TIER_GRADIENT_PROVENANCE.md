# H3 (RQ2) tier gradient -- raw tables

Generated: 2026-08-03T19:16:09.177093+00:00
Git commit: 5a56a97
Script: scripts/analyze_h3_tier_gradient.py

Pre-registered plan (written before this script existed):
`analysis/H3_ANALYSIS_PLAN.md`. Interpretation: `analysis/H3_INTERPRETATION.md`
(hand-written, not touched by this script).

## Per-model, all-tier (L1-L4)

              model_short  n_rows    tiers_present status  spearman_rho  p_perm  p_perm_holm
         gpt-5-2025-08-07     263 [L1, L2, L3, L4]     ok     -0.412676  0.0001       0.0009
    gpt-5-mini-2025-08-07     250 [L1, L2, L3, L4]     ok     -0.495620  0.0001       0.0009
        claude-sonnet-4-6     946 [L1, L2, L3, L4]     ok     -0.379323  0.0001       0.0009
claude-haiku-4-5-20251001     663 [L1, L2, L3, L4]     ok     -0.462663  0.0001       0.0009
   gemini-3.1-pro-preview     510     [L1, L2, L3]     ok     -0.193774  0.0001       0.0009
    gemini-3.1-flash-lite     783 [L1, L2, L3, L4]     ok     -0.452861  0.0001       0.0009
                 Qwen 32B     436 [L1, L2, L3, L4]     ok     -0.437618  0.0001       0.0009
                  Qwen 7B     306 [L1, L2, L3, L4]     ok     -0.416123  0.0001       0.0009
                Qwen 1.5B      78     [L1, L2, L3]     ok     -0.477268  0.0001       0.0009

Significant at raw p<0.05: 9/9. Significant at Holm-adjusted p<0.05: **9/9**.

## Per-model, L2-L4 (ceiling-effect sensitivity check -- excludes near-zero-variance L1)

              model_short  n_rows tiers_present                  status  spearman_rho  p_perm  p_perm_holm
         gpt-5-2025-08-07     205  [L2, L3, L4]                      ok     -0.433320  0.0001       0.0007
    gpt-5-mini-2025-08-07     195  [L2, L3, L4]                      ok     -0.551758  0.0001       0.0007
        claude-sonnet-4-6     628  [L2, L3, L4]                      ok     -0.398453  0.0001       0.0007
claude-haiku-4-5-20251001     476  [L2, L3, L4]                      ok     -0.421122  0.0001       0.0007
   gemini-3.1-pro-preview     261      [L2, L3] insufficient tier range           NaN     NaN          NaN
    gemini-3.1-flash-lite     591  [L2, L3, L4]                      ok     -0.421824  0.0001       0.0007
                 Qwen 32B     376  [L2, L3, L4]                      ok     -0.424755  0.0001       0.0007
                  Qwen 7B     260  [L2, L3, L4]                      ok     -0.266136  0.0001       0.0007
                Qwen 1.5B      66      [L2, L3] insufficient tier range           NaN     NaN          NaN

Significant at raw p<0.05: 7/7 computable. Significant at Holm-adjusted p<0.05: **7/7 computable**.
(2 model(s) have "insufficient tier range" in this scope -- see H3_ANALYSIS_PLAN.md's incomplete-tier-coverage section.)

## Pooled (between-model confound NOT controlled for -- see H3_ANALYSIS_PLAN.md)

All-tier: rho=-0.38420428687662705, p=9.999000099990002e-05, n_rows=4235
L2-L4: rho=-0.3250252564477078, p=9.999000099990002e-05, n_rows=3058

## Low-power tier-mean supplementary rows (n<=4 per model, NOT Holm-corrected, NOT to be read via a significance threshold)

              model_short  n_tiers  tier_mean_spearman_raw  tier_mean_spearman_covadj
         gpt-5-2025-08-07        4                    -0.8                        0.2
    gpt-5-mini-2025-08-07        4                    -0.8                        0.2
        claude-sonnet-4-6        4                    -1.0                       -0.8
claude-haiku-4-5-20251001        4                    -1.0                       -0.8
   gemini-3.1-pro-preview        3                    -1.0                        0.5
    gemini-3.1-flash-lite        4                    -1.0                       -0.8
                 Qwen 32B        4                    -1.0                       -0.4
                  Qwen 7B        4                    -1.0                       -0.8
                Qwen 1.5B        3                    -1.0                       -0.5
