"""RQ5/H6 — cross-benchmark validity analysis, per the pre-registered
analysis/RQ5_ANALYSIS_PLAN.md.

Part 1 (zero-compute, always runs): Dynamic (pooled Mut@K across all
landed tiers/instantiations, baseline_pass_rate secondary) vs ULT core_400
Mut@K, per model -- score correlation (Pearson/Spearman) + rank consistency
(Kendall tau), with bootstrap CIs and permutation p-values
(src/Analysis/correlation.py).

Parts 2-3 (public-benchmark pairs: Dynamic<->public, ULT<->public) are
gated on analysis/rq5_public_scores.csv existing (written by the
leaderboard harvest / self-run pipeline) -- this script runs Part 1 alone
until that file exists, and adds the other two pairs once it does, so it is
safe to re-run at any point without editing code.

Outputs:
  analysis/rq5_model_ranking.csv       -- per-model scores, both benchmarks
  analysis/rq5_correlations.csv        -- one row per benchmark pair
  analysis/RQ5_PROVENANCE.md           -- raw tables (regenerable)

Usage: python scripts/analyze_rq5.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd

from coverage_matrix import CANONICAL_MODELS
from src.Analysis.correlation import compute_correlations
from src.Analysis.loader import load_records
from src.Analysis.provenance import stamp_block

PUBLIC_SCORES_PATH = ROOT / "analysis" / "rq5_public_scores.csv"


def _model_shortname(label: str) -> str:
    if label.startswith("Qwen__"):
        for size in ("1.5B", "7B", "32B"):
            if size in label:
                return f"Qwen {size}"
    return label


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    dynamic = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]
    ult = load_records("data/results/ult", benchmark="ult")
    ult = ult[ult["model_label"].isin(CANONICAL_MODELS)]

    # --- pooled + per-tier Dynamic, per model --------------------------------
    rows = []
    for label in CANONICAL_MODELS:
        d = dynamic[dynamic["model_label"] == label]
        u = ult[ult["model_label"] == label]
        if d.empty and u.empty:
            continue

        def _mut(df):
            s = df["mutation_score"].dropna()
            return float(s.mean()) if len(s) else None

        def _bp(df):
            s = df["baseline_passed"].dropna()
            return float(s.astype(float).mean()) if len(s) else None

        row = {
            "model_label": label,
            "model_short": _model_shortname(label),
            "dynamic_mutk_pooled": _mut(d),
            "dynamic_bp_pooled": _bp(d),
            "dynamic_n_pooled": len(d),
            "ult_mutk": _mut(u),
            "ult_bp": _bp(u),
            "ult_n": len(u),
        }
        for tier in ("L1", "L2", "L3", "L4"):
            row[f"dynamic_mutk_{tier}"] = _mut(d[d["tier"] == tier])
        rows.append(row)

    ranking = pd.DataFrame(rows)

    if PUBLIC_SCORES_PATH.exists():
        public = pd.read_csv(PUBLIC_SCORES_PATH)
        ranking = ranking.merge(public, on="model_label", how="left")
        print(f"Merged public scores from {PUBLIC_SCORES_PATH}")
    else:
        print(f"No public scores yet ({PUBLIC_SCORES_PATH} not found) -- "
              f"Part 1 (Dynamic<->ULT) only.")

    ranking.to_csv(ROOT / "analysis" / "rq5_model_ranking.csv", index=False)
    print("\n=== Model ranking table ===")
    print(ranking.to_string(index=False))

    # --- correlations ---------------------------------------------------------
    corr_rows = []

    def _add_pair(pair_name: str, col_a: str, col_b: str):
        sub = ranking.dropna(subset=[col_a, col_b])
        if len(sub) < 3:
            print(f"\n{pair_name}: only {len(sub)} model(s) with both scores -- skipping (need >=3)")
            return
        res = compute_correlations(sub[col_a].to_numpy(), sub[col_b].to_numpy())
        d = {"pair": pair_name, "metric_a": col_a, "metric_b": col_b, **vars(res)}
        corr_rows.append(d)
        print(f"\n=== {pair_name} (n={res.n}) ===")
        print(f"  Pearson r  = {res.pearson_r:.3f}  CI [{res.pearson_r_ci_lo:.3f}, {res.pearson_r_ci_hi:.3f}]  p_perm={res.pearson_p_perm:.4f}")
        print(f"  Spearman rho = {res.spearman_rho:.3f}  CI [{res.spearman_rho_ci_lo:.3f}, {res.spearman_rho_ci_hi:.3f}]  p_perm={res.spearman_p_perm:.4f}")
        print(f"  Kendall tau  = {res.kendall_tau:.3f}  CI [{res.kendall_tau_ci_lo:.3f}, {res.kendall_tau_ci_hi:.3f}]  p_perm={res.kendall_p_perm:.4f}")

    _add_pair("Dynamic(pooled) <-> ULT", "dynamic_mutk_pooled", "ult_mutk")

    if "public_score" in ranking.columns:
        _add_pair("Dynamic(pooled) <-> public (Complete-split)", "dynamic_mutk_pooled", "public_score")
        _add_pair("ULT <-> public (Complete-split)", "ult_mutk", "public_score")
    if "public_score_hard" in ranking.columns:
        _add_pair("Dynamic(pooled) <-> public (Hard-split)", "dynamic_mutk_pooled", "public_score_hard")
        _add_pair("ULT <-> public (Hard-split)", "ult_mutk", "public_score_hard")

    corr_df = pd.DataFrame(corr_rows)
    corr_df.to_csv(ROOT / "analysis" / "rq5_correlations.csv", index=False)

    provenance = f"""# RQ5 / H6 — cross-benchmark validity (raw tables)

{stamp_block("scripts/analyze_rq5.py")}
Per analysis/RQ5_ANALYSIS_PLAN.md (pre-registered 2026-07-27, before this
script's first run). Interpretation, once the public-benchmark pairs land,
belongs in a separate RQ5_INTERPRETATION.md (same split as Comparison C,
analysis/COMPARISON_C_INTERPRETATION.md) -- not embedded here.

## Model ranking table

{ranking.to_string(index=False)}

## Correlations

{corr_df.to_string(index=False) if len(corr_df) else "(none computed -- see skip messages above)"}
"""
    (ROOT / "analysis" / "RQ5_PROVENANCE.md").write_text(provenance)
    print(f"\nWritten: analysis/rq5_model_ranking.csv, analysis/rq5_correlations.csv, "
          f"analysis/RQ5_PROVENANCE.md")


if __name__ == "__main__":
    main()
