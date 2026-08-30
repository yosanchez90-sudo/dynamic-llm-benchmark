# Collapse vs survival figure — provenance

Generated: 2026-08-30T01:30:24.158620+00:00
Git commit: 9cdef55
Script: scripts/plot_collapse_vs_survival.py

Sources: analysis/rq5_cross_family_model_ranking.csv, analysis/rq5_cross_family_correlations.csv.
n=3 minimum achievable two-sided permutation p-value (0.3333)
verified directly against src/Analysis/correlation.py's _permutation_p()
(two-sided |stat|>=|observed| test, not one-sided), NOT the 1/6~=0.167
one-sided figure, which this project's own test does not compute. Thin
cells (n_defined<20) ringed in red, same convention as
analysis/figures/ranking_matrix_heatmap.pdf and noise_floor.pdf.

Output: analysis/figures/collapse_vs_survival.pdf (+ .png).
