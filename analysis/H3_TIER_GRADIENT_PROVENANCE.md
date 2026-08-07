# H3 (RQ2) tier gradient -- raw tables

Generated: 2026-08-07T15:24:54.613689+00:00
Git commit: 21d80e1
Script: scripts/analyze_h3_tier_gradient.py

Pre-registered plan (written before this script existed):
`analysis/H3_ANALYSIS_PLAN.md`. Interpretation: `analysis/H3_INTERPRETATION.md`
(hand-written, not touched by this script).

## Per-model, all-tier (L1-L4)

              model_short  n_rows    tiers_present status  spearman_rho  p_perm  p_perm_holm
         gpt-5-2025-08-07    1331 [L1, L2, L3, L4]     ok     -0.406256  0.0001       0.0009
    gpt-5-mini-2025-08-07    1257 [L1, L2, L3, L4]     ok     -0.468796  0.0001       0.0009
        claude-sonnet-4-6    1055 [L1, L2, L3, L4]     ok     -0.390368  0.0001       0.0009
claude-haiku-4-5-20251001     753 [L1, L2, L3, L4]     ok     -0.452286  0.0001       0.0009
   gemini-3.1-pro-preview     548 [L1, L2, L3, L4]     ok     -0.295734  0.0001       0.0009
    gemini-3.1-flash-lite     783 [L1, L2, L3, L4]     ok     -0.452861  0.0001       0.0009
                 Qwen 32B     436 [L1, L2, L3, L4]     ok     -0.437618  0.0001       0.0009
                  Qwen 7B     306 [L1, L2, L3, L4]     ok     -0.416123  0.0001       0.0009
                Qwen 1.5B      78     [L1, L2, L3]     ok     -0.477268  0.0001       0.0009

Significant at raw p<0.05: 9/9. Significant at Holm-adjusted p<0.05: **9/9**.

## Per-model, L2-L4 (ceiling-effect sensitivity check -- excludes near-zero-variance L1)

              model_short  n_rows tiers_present                  status  spearman_rho  p_perm  p_perm_holm
         gpt-5-2025-08-07    1046  [L2, L3, L4]                      ok     -0.416314  0.0001       0.0008
    gpt-5-mini-2025-08-07     984  [L2, L3, L4]                      ok     -0.528961  0.0001       0.0008
        claude-sonnet-4-6     737  [L2, L3, L4]                      ok     -0.424944  0.0001       0.0008
claude-haiku-4-5-20251001     566  [L2, L3, L4]                      ok     -0.422696  0.0001       0.0008
   gemini-3.1-pro-preview     299  [L2, L3, L4]                      ok     -0.254615  0.0001       0.0008
    gemini-3.1-flash-lite     591  [L2, L3, L4]                      ok     -0.421824  0.0001       0.0008
                 Qwen 32B     376  [L2, L3, L4]                      ok     -0.424755  0.0001       0.0008
                  Qwen 7B     260  [L2, L3, L4]                      ok     -0.266136  0.0001       0.0008
                Qwen 1.5B      66      [L2, L3] insufficient tier range           NaN     NaN          NaN

Significant at raw p<0.05: 8/8 computable. Significant at Holm-adjusted p<0.05: **8/8 computable**.
(1 model(s) have "insufficient tier range" in this scope -- see H3_ANALYSIS_PLAN.md's incomplete-tier-coverage section.)

## Pooled (between-model confound NOT controlled for -- see H3_ANALYSIS_PLAN.md)

All-tier: rho=-0.39243138128738925, p=9.999000099990002e-05, n_rows=6547
L2-L4: rho=-0.36102979623294146, p=9.999000099990002e-05, n_rows=4925

## Low-power tier-mean supplementary rows (n<=4 per model, NOT Holm-corrected, NOT to be read via a significance threshold)

              model_short  n_tiers  tier_mean_spearman_raw  tier_mean_spearman_covadj
         gpt-5-2025-08-07        4                    -0.8                        0.8
    gpt-5-mini-2025-08-07        4                    -0.8                        0.2
        claude-sonnet-4-6        4                    -1.0                       -0.8
claude-haiku-4-5-20251001        4                    -1.0                       -0.8
   gemini-3.1-pro-preview        4                    -1.0                        0.2
    gemini-3.1-flash-lite        4                    -1.0                       -0.8
                 Qwen 32B        4                    -1.0                       -0.4
                  Qwen 7B        4                    -1.0                       -0.8
                Qwen 1.5B        3                    -1.0                       -0.5
