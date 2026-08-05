# Noise floor by metric and tier — provenance

Generated: 2026-08-05T13:33:41.719489+00:00
Git commit: c60a84a
Script: scripts/plot_noise_floor.py

Computed directly from data/results/dynamic/*.jsonl (canonical 9 models),
using src.Analysis.stability.stable_mut_at_k per tier (extra_group_cols
not used here -- filtered per tier instead, then aggregated). Raw table:
analysis/noise_floor_by_tier.csv.

4-model unresolvable-cluster annotation is a named citation of
analysis/RQ5_DIAGNOSTICS.md's finding (pooled conditional Mut@K only), not
re-derived generically for every metric/tier cell in this figure.

Output: analysis/figures/noise_floor.pdf (+ .png).
