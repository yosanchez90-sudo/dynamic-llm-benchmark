"""H3 (RQ2) -- tier gradient: Spearman correlation between tier index and
mutation score, per model and pooled. Implements analysis/H3_ANALYSIS_PLAN.md
(pre-registered 2026-08-04, before this script existed) -- every design
choice here (estimands, ceiling-effect handling, conditioning, coverage-
adjusted companion, incomplete-tier-coverage handling, Holm correction
scope) was decided in that plan, not tuned after seeing results.

Usage: python scripts/analyze_h3_tier_gradient.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd

from coverage_matrix import CANONICAL_MODELS  # noqa: E402
from src.Analysis.correlation import compute_correlations  # noqa: E402
from src.Analysis.loader import load_records  # noqa: E402
from src.Analysis.multiple_comparisons import holm_bonferroni  # noqa: E402
from src.Analysis.provenance import stamp_block  # noqa: E402

TIER_INDEX = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
THIN_N_DEFINED = 20  # same convention as Comparison A/B and RQ5
MIN_DISTINCT_TIERS = 3  # below this, a "gradient" correlation isn't meaningful


def _model_shortname(label: str) -> str:
    if label.startswith("Qwen__"):
        for size in ("1.5B", "7B", "32B"):
            if size in label:
                return f"Qwen {size}"
    return label


def _per_model_correlation(defined: pd.DataFrame, tiers_scope: set[str]) -> dict:
    sub = defined[defined["tier"].isin(tiers_scope)]
    distinct_tiers = sorted(sub["tier"].unique())
    if len(distinct_tiers) < MIN_DISTINCT_TIERS:
        return {
            "n_rows": len(sub), "tiers_present": distinct_tiers,
            "status": "insufficient tier range", "spearman_rho": None,
            "p_perm": None, "ci_lo": None, "ci_hi": None,
        }
    tier_idx = sub["tier"].map(TIER_INDEX).to_numpy()
    scores = sub["mutation_score"].to_numpy()
    res = compute_correlations(tier_idx, scores)
    return {
        "n_rows": len(sub), "tiers_present": distinct_tiers, "status": "ok",
        "spearman_rho": res.spearman_rho, "p_perm": res.spearman_p_perm,
        "ci_lo": res.spearman_rho_ci_lo, "ci_hi": res.spearman_rho_ci_hi,
    }


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    dynamic = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]

    all_tier_rows = []
    l2l4_rows = []
    tier_mean_rows = []

    for label in CANONICAL_MODELS:
        sub = dynamic[dynamic["model_label"] == label]
        defined = sub.dropna(subset=["mutation_score"])
        short = _model_shortname(label)

        all_tier = _per_model_correlation(defined, {"L1", "L2", "L3", "L4"})
        all_tier_rows.append({"model_label": label, "model_short": short, **all_tier})

        l2l4 = _per_model_correlation(defined, {"L2", "L3", "L4"})
        l2l4_rows.append({"model_label": label, "model_short": short, **l2l4})

        # --- low-power tier-mean supplementary row (n<=4), raw + coverage-adjusted ---
        tier_means = {}
        for tier in ("L1", "L2", "L3", "L4"):
            tsub = sub[sub["tier"] == tier]
            tdef = tsub.dropna(subset=["mutation_score"])
            n_total, n_defined = len(tsub), len(tdef)
            mutk = float(tdef["mutation_score"].mean()) if n_defined else None
            bp_rate = (n_defined / n_total) if n_total else None
            cov_adj = (mutk * bp_rate) if (mutk is not None and bp_rate is not None) else None
            tier_means[tier] = {
                "mutk": mutk, "bp_rate": bp_rate, "coverage_adj": cov_adj,
                "n_total": n_total, "n_defined": n_defined,
                "thin": n_defined < THIN_N_DEFINED,
            }
        present = [t for t in ("L1", "L2", "L3", "L4") if tier_means[t]["mutk"] is not None]
        if len(present) >= MIN_DISTINCT_TIERS:
            idx = [TIER_INDEX[t] for t in present]
            raw_vals = [tier_means[t]["mutk"] for t in present]
            adj_vals = [tier_means[t]["coverage_adj"] for t in present]
            import numpy as np
            from scipy.stats import spearmanr
            raw_rho, _ = spearmanr(idx, raw_vals)
            adj_rho, _ = spearmanr(idx, adj_vals)
        else:
            raw_rho = adj_rho = None
        tier_mean_rows.append({
            "model_label": label, "model_short": short,
            "tiers_present": present, "n_tiers": len(present),
            "tier_mean_spearman_raw": raw_rho, "tier_mean_spearman_covadj": adj_rho,
            **{f"{t}_mutk": tier_means[t]["mutk"] for t in ("L1", "L2", "L3", "L4")},
            **{f"{t}_covadj": tier_means[t]["coverage_adj"] for t in ("L1", "L2", "L3", "L4")},
            **{f"{t}_thin": tier_means[t]["thin"] for t in ("L1", "L2", "L3", "L4")},
        })

    all_tier_df = pd.DataFrame(all_tier_rows)
    l2l4_df = pd.DataFrame(l2l4_rows)
    tier_mean_df = pd.DataFrame(tier_mean_rows)

    # --- pooled estimand (both scopes), stated confound: between-model pooling ---
    all_defined = dynamic.dropna(subset=["mutation_score"])
    pooled_all_tier = _per_model_correlation(all_defined, {"L1", "L2", "L3", "L4"})
    pooled_l2l4 = _per_model_correlation(all_defined, {"L2", "L3", "L4"})

    # --- Holm-Bonferroni: two separate per-model families (all-tier, L2-L4) ---
    all_tier_df["p_perm_holm"] = holm_bonferroni(all_tier_df["p_perm"].tolist())
    l2l4_df["p_perm_holm"] = holm_bonferroni(l2l4_df["p_perm"].tolist())
    all_tier_n_sig_raw = int((all_tier_df["p_perm"] < 0.05).sum())
    all_tier_n_sig_holm = int((all_tier_df["p_perm_holm"] < 0.05).sum())
    l2l4_valid = l2l4_df.dropna(subset=["p_perm"])
    l2l4_n_sig_raw = int((l2l4_valid["p_perm"] < 0.05).sum())
    l2l4_n_sig_holm = int((l2l4_valid["p_perm_holm"] < 0.05).sum())

    print("=== H3 per-model, all-tier (L1-L4) ===")
    print(all_tier_df[["model_short", "n_rows", "tiers_present", "status",
                       "spearman_rho", "p_perm", "p_perm_holm"]].to_string(index=False))
    print(f"Significant at raw p<0.05: {all_tier_n_sig_raw}/{len(all_tier_df)}. "
          f"Holm-adjusted p<0.05: {all_tier_n_sig_holm}/{len(all_tier_df)}.")

    print("\n=== H3 per-model, L2-L4 (ceiling-effect sensitivity check) ===")
    print(l2l4_df[["model_short", "n_rows", "tiers_present", "status",
                   "spearman_rho", "p_perm", "p_perm_holm"]].to_string(index=False))
    print(f"Significant at raw p<0.05: {l2l4_n_sig_raw}/{len(l2l4_valid)} computable. "
          f"Holm-adjusted p<0.05: {l2l4_n_sig_holm}/{len(l2l4_valid)} computable.")

    print(f"\n=== H3 pooled (between-model confound not controlled for -- see H3_ANALYSIS_PLAN.md) ===")
    print(f"All-tier: rho={pooled_all_tier['spearman_rho']}, p={pooled_all_tier['p_perm']}, "
          f"n_rows={pooled_all_tier['n_rows']}")
    print(f"L2-L4: rho={pooled_l2l4['spearman_rho']}, p={pooled_l2l4['p_perm']}, "
          f"n_rows={pooled_l2l4['n_rows']}")

    print("\n=== H3 low-power tier-mean supplementary rows (n<=4, not Holm-corrected, "
          "not to be read via a significance threshold) ===")
    print(tier_mean_df[["model_short", "n_tiers", "tier_mean_spearman_raw",
                        "tier_mean_spearman_covadj"]].to_string(index=False))

    ANALYSIS_DIR = ROOT / "analysis"
    all_tier_df.to_csv(ANALYSIS_DIR / "h3_tier_gradient_all_tier.csv", index=False)
    l2l4_df.to_csv(ANALYSIS_DIR / "h3_tier_gradient_l2l4.csv", index=False)
    tier_mean_df.to_csv(ANALYSIS_DIR / "h3_tier_gradient_tier_means.csv", index=False)

    provenance = f"""# H3 (RQ2) tier gradient -- raw tables

{stamp_block("scripts/analyze_h3_tier_gradient.py")}
Pre-registered plan (written before this script existed):
`analysis/H3_ANALYSIS_PLAN.md`. Interpretation: `analysis/H3_INTERPRETATION.md`
(hand-written, not touched by this script).

## Per-model, all-tier (L1-L4)

{all_tier_df[["model_short", "n_rows", "tiers_present", "status", "spearman_rho", "p_perm", "p_perm_holm"]].to_string(index=False)}

Significant at raw p<0.05: {all_tier_n_sig_raw}/{len(all_tier_df)}. Significant at Holm-adjusted p<0.05: **{all_tier_n_sig_holm}/{len(all_tier_df)}**.

## Per-model, L2-L4 (ceiling-effect sensitivity check, excludes near-zero-variance L1)

{l2l4_df[["model_short", "n_rows", "tiers_present", "status", "spearman_rho", "p_perm", "p_perm_holm"]].to_string(index=False)}

Significant at raw p<0.05: {l2l4_n_sig_raw}/{len(l2l4_valid)} computable. Significant at Holm-adjusted p<0.05: **{l2l4_n_sig_holm}/{len(l2l4_valid)} computable**.
({len(l2l4_df) - len(l2l4_valid)} model(s) have "insufficient tier range" in this scope, per H3_ANALYSIS_PLAN.md's incomplete-tier-coverage section.)

## Pooled (between-model confound NOT controlled for, per H3_ANALYSIS_PLAN.md)

All-tier: rho={pooled_all_tier['spearman_rho']}, p={pooled_all_tier['p_perm']}, n_rows={pooled_all_tier['n_rows']}
L2-L4: rho={pooled_l2l4['spearman_rho']}, p={pooled_l2l4['p_perm']}, n_rows={pooled_l2l4['n_rows']}

## Low-power tier-mean supplementary rows (n<=4 per model, NOT Holm-corrected, NOT to be read via a significance threshold)

{tier_mean_df[["model_short", "n_tiers", "tier_mean_spearman_raw", "tier_mean_spearman_covadj"]].to_string(index=False)}
"""
    (ANALYSIS_DIR / "H3_TIER_GRADIENT_PROVENANCE.md").write_text(provenance)
    print(f"\nWritten: analysis/h3_tier_gradient_all_tier.csv, "
          f"analysis/h3_tier_gradient_l2l4.csv, analysis/h3_tier_gradient_tier_means.csv, "
          f"analysis/H3_TIER_GRADIENT_PROVENANCE.md")


if __name__ == "__main__":
    main()
