"""Metric-agnostic ranking matrix (supervisor reframe, 2026-08-04): report
model rankings under every metric side by side -- exec_rate,
baseline_pass_rate, conditional Mut@K, coverage-adjusted Mut@K -- rather
than arguing which Mut@K definition is canonical. The conditional-Mut@K
"anomaly" (analysis/RQ5_CROSS_DEFINITION_AUDIT.md) is one row of this
matrix, not a separate definitional dispute.

Outputs:
  analysis/ranking_matrix_scores.csv        -- metric x scope x benchmark x
                                                model -> score/rank/n/n_defined
  analysis/ranking_matrix_correlations.csv  -- metric x benchmark-pair ->
                                                tau/rho/CI/p/holm_p (canonical scope)
  analysis/ranking_matrix_noise_floor.csv   -- metric -> between-model spread,
                                                mean within-model SD, ratio
  analysis/ranking_matrix_reliability.csv   -- metric -> mean pairwise Kendall
                                                tau across instantiations
  analysis/RANKING_MATRIX.md                -- readable assembly of all of the above

Usage: python scripts/build_ranking_matrix.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import pandas as pd

from coverage_matrix import CANONICAL_MODELS  # noqa: E402
from src.Analysis.correlation import compute_correlations  # noqa: E402
from src.Analysis.loader import load_records  # noqa: E402
from src.Analysis.multiple_comparisons import holm_bonferroni  # noqa: E402
from src.Analysis.provenance import stamp_block  # noqa: E402
from src.Analysis.stability import pairwise_kendall_tau, stable_mut_at_k  # noqa: E402

CROSS_FAMILY_MODELS = [
    "deepseek-ai__deepseek-coder-6.7b-instruct",
    "codellama__CodeLlama-13b-Instruct-hf",
    "bigcode__starcoder2-15b-instruct-v0.1",
    "mistralai__Mistral-7B-Instruct-v0.3",
]
SCOPES = {
    "canonical": CANONICAL_MODELS,
    "canonical_plus_cross_family": CANONICAL_MODELS + CROSS_FAMILY_MODELS,
}
METRICS = ["exec_rate", "baseline_pass_rate", "conditional_mutk", "coverage_adjusted"]
METRIC_LABELS = {
    "exec_rate": "exec_rate", "baseline_pass_rate": "baseline_pass_rate",
    "conditional_mutk": "conditional Mut@K", "coverage_adjusted": "coverage-adjusted Mut@K",
}
PUBLIC_SCORES_PATH = ROOT / "analysis" / "rq5_public_scores.csv"
ANALYSIS_DIR = ROOT / "analysis"


def _model_shortname(label: str) -> str:
    if label.startswith("Qwen__"):
        for size in ("1.5B", "7B", "32B"):
            if size in label:
                return f"Qwen {size}"
    short = {
        "deepseek-ai__deepseek-coder-6.7b-instruct": "DeepSeek-6.7B",
        "codellama__CodeLlama-13b-Instruct-hf": "CodeLlama-13B",
        "bigcode__starcoder2-15b-instruct-v0.1": "StarCoder2-15B",
        "mistralai__Mistral-7B-Instruct-v0.3": "Mistral-7B",
    }
    return short.get(label, label)


def _cell(sub: pd.DataFrame) -> dict:
    """All 4 metrics' score for one (model, benchmark-view) slice."""
    n_total = len(sub)
    if n_total == 0:
        return {m: None for m in METRICS} | {"n_total": 0, "n_defined_mutk": 0}
    exec_rate = float(sub["exec_rate"].mean())
    bp_rate = float(sub["baseline_passed"].astype(float).mean())
    defined = sub.dropna(subset=["mutation_score"])
    n_defined = len(defined)
    cond_mutk = float(defined["mutation_score"].mean()) if n_defined else None
    cov_adj = (cond_mutk * bp_rate) if cond_mutk is not None else None
    return {
        "exec_rate": exec_rate, "baseline_pass_rate": bp_rate,
        "conditional_mutk": cond_mutk, "coverage_adjusted": cov_adj,
        "n_total": n_total, "n_defined_mutk": n_defined,
    }


def _rank_column(df: pd.DataFrame, score_col: str) -> pd.Series:
    """Rank 1 = highest score; NaN scores get NaN rank (not silently dropped
    from the table, just unranked)."""
    return df[score_col].rank(ascending=False, method="min")


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    ult = load_records("data/results/ult", benchmark="ult")
    public = pd.read_csv(PUBLIC_SCORES_PATH) if PUBLIC_SCORES_PATH.exists() else pd.DataFrame()
    public_lookup = dict(zip(public.get("model_label", []), public.get("public_score", [])))

    # ================= TABLE 1: per-metric, per-scope, per-benchmark scores + ranks
    score_rows = []
    for scope_name, models in SCOPES.items():
        for benchmark_view, (src_df, tier_filter) in {
            "dynamic_pooled": (dynamic, None),
            "dynamic_L4": (dynamic, "L4"),
            "ult_core400": (ult, None),
        }.items():
            view_df = src_df[src_df["model_label"].isin(models)]
            if tier_filter:
                view_df = view_df[view_df["tier"] == tier_filter]
            for label in models:
                sub = view_df[view_df["model_label"] == label]
                cell = _cell(sub)
                score_rows.append({
                    "scope": scope_name, "benchmark": benchmark_view,
                    "model_label": label, "model_short": _model_shortname(label),
                    **cell,
                })
            # BigCodeBench: one published number, same value used as the (d)
            # column for every metric row -- not computed per-metric, since
            # BigCodeBench has no exec/baseline/mutation-score concept of its
            # own. Flagged explicitly in the written table, not silently
            # repeated as if it were 4 independent measurements.
        for label in models:
            score_rows.append({
                "scope": scope_name, "benchmark": "bigcodebench",
                "model_label": label, "model_short": _model_shortname(label),
                "exec_rate": None, "baseline_pass_rate": None,
                "conditional_mutk": public_lookup.get(label), "coverage_adjusted": None,
                "n_total": 1 if label in public_lookup else 0,
                "n_defined_mutk": 1 if label in public_lookup else 0,
            })

    scores_df = pd.DataFrame(score_rows)
    # ranks computed within (scope, benchmark, metric)
    for metric in METRICS:
        scores_df[f"{metric}_rank"] = np.nan
    for (scope_name, benchmark_view), grp_idx in scores_df.groupby(["scope", "benchmark"]).groups.items():
        grp = scores_df.loc[grp_idx]
        for metric in METRICS:
            score_col = "conditional_mutk" if (benchmark_view == "bigcodebench" and metric != "coverage_adjusted") else metric
            if benchmark_view == "bigcodebench" and metric != "conditional_mutk":
                continue  # BigCodeBench only has one real score column; other metric rows just borrow it for display
            scores_df.loc[grp_idx, f"{metric}_rank"] = _rank_column(grp, score_col)
    scores_df.to_csv(ANALYSIS_DIR / "ranking_matrix_scores.csv", index=False)

    # ================= TABLE 2: cross-benchmark rank agreement
    # Canonical scope is THE deliverable ("ONE table" in the written MD,
    # below); canonical+cross-family is computed too (same pairs/metrics)
    # so the ranking-matrix heatmap figure can show both scopes side by
    # side -- Holm-corrected SEPARATELY per scope (each is its own 12-test
    # family, same discipline as RQ4/H5's N=4-vs-all-pairs split), not
    # pooled into one 24-test correction.
    pairs = [
        ("Dynamic<->ULT", "dynamic_pooled", "ult_core400"),
        ("Dynamic<->BigCodeBench", "dynamic_pooled", "bigcodebench"),
        ("ULT<->BigCodeBench", "ult_core400", "bigcodebench"),
    ]

    def _pivot(scope_df: pd.DataFrame, benchmark: str, metric: str) -> pd.Series:
        sub = scope_df[scope_df["benchmark"] == benchmark].set_index("model_label")
        col = "conditional_mutk" if benchmark == "bigcodebench" else metric
        return sub[col]

    all_corr_frames = []
    for scope_name in SCOPES:
        scope_df = scores_df[scores_df["scope"] == scope_name]
        corr_rows = []
        for metric in METRICS:
            for pair_name, bench_a, bench_b in pairs:
                sa, sb = _pivot(scope_df, bench_a, metric), _pivot(scope_df, bench_b, metric)
                joint = pd.concat([sa.rename("a"), sb.rename("b")], axis=1).dropna()
                if len(joint) < 3:
                    corr_rows.append({
                        "scope": scope_name, "metric": metric, "pair": pair_name, "n": len(joint),
                        "kendall_tau": None, "kendall_p_perm": None,
                        "spearman_rho": None, "spearman_p_perm": None,
                    })
                    continue
                res = compute_correlations(joint["a"].to_numpy(), joint["b"].to_numpy())
                corr_rows.append({
                    "scope": scope_name, "metric": metric, "pair": pair_name, "n": res.n,
                    "kendall_tau": res.kendall_tau, "kendall_ci_lo": res.kendall_tau_ci_lo,
                    "kendall_ci_hi": res.kendall_tau_ci_hi, "kendall_p_perm": res.kendall_p_perm,
                    "spearman_rho": res.spearman_rho, "spearman_ci_lo": res.spearman_rho_ci_lo,
                    "spearman_ci_hi": res.spearman_rho_ci_hi, "spearman_p_perm": res.spearman_p_perm,
                })
        scope_corr_df = pd.DataFrame(corr_rows)
        scope_corr_df["kendall_p_holm"] = holm_bonferroni(scope_corr_df["kendall_p_perm"].tolist())
        all_corr_frames.append(scope_corr_df)

    corr_df_all_scopes = pd.concat(all_corr_frames, ignore_index=True)
    corr_df_all_scopes.to_csv(ANALYSIS_DIR / "ranking_matrix_correlations.csv", index=False)
    # The written MD table (below) reports canonical only, per the original
    # "ONE table" deliverable -- kept as a plain variable name for the
    # f-string block further down, unchanged from before this scope
    # extension.
    corr_df = corr_df_all_scopes[corr_df_all_scopes["scope"] == "canonical"].drop(columns=["scope"])

    # ================= TABLE 3: noise floor (canonical, Dynamic pooled)
    noise_rows = []
    for metric in METRICS:
        dyn_canon = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]
        if metric == "coverage_adjusted":
            stable_raw = stable_mut_at_k(dyn_canon, coverage_adjust=True)
        else:
            metric_col = {"exec_rate": "exec_rate", "baseline_pass_rate": "baseline_passed",
                          "conditional_mutk": "mutation_score"}[metric]
            stable_raw = stable_mut_at_k(dyn_canon, metric_col=metric_col)
        stable_2plus = stable_raw[stable_raw["n_instantiations"] >= 2]
        mean_within_sd = float(stable_2plus["sd_mut_at_k"].mean()) if len(stable_2plus) else None

        pooled_scores = scores_df[(scores_df["scope"] == "canonical") & (scores_df["benchmark"] == "dynamic_pooled")][metric].dropna()
        spread = float(pooled_scores.max() - pooled_scores.min()) if len(pooled_scores) else None
        ratio = (spread / mean_within_sd) if (spread is not None and mean_within_sd) else None
        noise_rows.append({
            "metric": metric, "between_model_spread": spread,
            "mean_within_model_sd": mean_within_sd,
            "spread_to_sd_ratio": ratio,
            "n_models_with_sd": len(stable_2plus),
        })
    noise_df = pd.DataFrame(noise_rows)
    noise_df.to_csv(ANALYSIS_DIR / "ranking_matrix_noise_floor.csv", index=False)

    # ================= TABLE 4: reliability (mean pairwise Kendall tau across instantiations)
    rel_rows = []
    dyn_canon = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]
    for metric in METRICS:
        if metric == "coverage_adjusted":
            pw = pairwise_kendall_tau(dyn_canon, coverage_adjust=True)
        else:
            metric_col = {"exec_rate": "exec_rate", "baseline_pass_rate": "baseline_passed",
                          "conditional_mutk": "mutation_score"}[metric]
            pw = pairwise_kendall_tau(dyn_canon, metric_col=metric_col)
        n4_mask = pw["instantiation_a"].isin({"1", "2", "3", "4"}) & pw["instantiation_b"].isin({"1", "2", "3", "4"})
        pw_n4 = pw[n4_mask]
        mean_tau_n4 = float(pw_n4["tau"].dropna().mean()) if pw_n4["tau"].notna().any() else None
        mean_tau_all = float(pw["tau"].dropna().mean()) if pw["tau"].notna().any() else None
        rel_rows.append({
            "metric": metric, "mean_pairwise_tau_n4": mean_tau_n4,
            "mean_pairwise_tau_all_pairs": mean_tau_all,
        })
    rel_df = pd.DataFrame(rel_rows)
    rel_df.to_csv(ANALYSIS_DIR / "ranking_matrix_reliability.csv", index=False)

    # ================= assemble RANKING_MATRIX.md
    def _fmt(x, spec=".3f"):
        return format(x, spec) if x is not None and not (isinstance(x, float) and np.isnan(x)) else "n/a"

    md_parts = [f"""# Ranking matrix — every metric, every benchmark, side by side

{stamp_block("scripts/build_ranking_matrix.py")}
Supervisor reframe (2026-08-04): the ranking exercise is metric-agnostic --
this file reports model rankings under exec_rate, baseline_pass_rate,
conditional Mut@K, and coverage-adjusted Mut@K side by side, rather than
arguing which Mut@K definition is canonical. Full per-cell data:
`analysis/ranking_matrix_scores.csv`. Hand-written interpretation, if any,
belongs in a separate file -- this one is auto-generated raw tables only.

## Table 1: per-metric scores and ranks

(a) Dynamic pooled, (b) Dynamic L4, (c) ULT core_400, (d) BigCodeBench
(published Complete-split Pass@1 -- not a per-row metric, so the SAME
BigCodeBench number/rank is shown under every metric block below; this is
noted, not an oversight). Canonical (9) and canonical+cross-family (13)
scopes shown separately.
"""]

    for scope_name in SCOPES:
        md_parts.append(f"\n### Scope: {scope_name} ({len(SCOPES[scope_name])} models)\n")
        for metric in METRICS:
            md_parts.append(f"\n**{METRIC_LABELS[metric]}**\n")
            header = "| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            lines = [header]
            for label in SCOPES[scope_name]:
                short = _model_shortname(label)
                row_cells = []
                for bench in ("dynamic_pooled", "dynamic_L4", "ult_core400"):
                    r = scores_df[(scores_df["scope"] == scope_name) & (scores_df["benchmark"] == bench) & (scores_df["model_label"] == label)]
                    if len(r) == 0:
                        row_cells += ["n/a", "n/a", "n/a"]
                        continue
                    r = r.iloc[0]
                    row_cells += [_fmt(r[metric]), _fmt(r[f"{metric}_rank"], ".0f"), f"{int(r['n_total'])}/{int(r['n_defined_mutk'])}"]
                bc = scores_df[(scores_df["scope"] == scope_name) & (scores_df["benchmark"] == "bigcodebench") & (scores_df["model_label"] == label)]
                if len(bc) and bc.iloc[0]["conditional_mutk"] is not None and not pd.isna(bc.iloc[0]["conditional_mutk"]):
                    bc = bc.iloc[0]
                    bc_cells = [_fmt(bc["conditional_mutk"], ".1f"), _fmt(bc["conditional_mutk_rank"], ".0f")]
                else:
                    bc_cells = ["n/a", "n/a"]
                lines.append(f"| {short} | " + " | ".join(row_cells) + " | " + " | ".join(bc_cells) + " |\n")
            md_parts.append("".join(lines))

    md_parts.append("""
## Table 2: cross-benchmark rank agreement (ONE table, canonical scope, Holm-corrected within this 12-test family)

Kendall tau primary (permutation p, Holm-adjusted p); Spearman rho shown alongside. Dynamic side uses pooled (matching this project's established RQ5 primary convention).

| Metric | Dynamic<->ULT | Dynamic<->BigCodeBench | ULT<->BigCodeBench |
|---|---|---|---|
""")
    for metric in METRICS:
        cells = []
        for pair_name, *_ in pairs:
            r = corr_df[(corr_df["metric"] == metric) & (corr_df["pair"] == pair_name)]
            if len(r) == 0 or r.iloc[0]["kendall_tau"] is None or pd.isna(r.iloc[0]["kendall_tau"]):
                cells.append(f"n={int(r.iloc[0]['n']) if len(r) else 0} (too few)")
                continue
            r = r.iloc[0]
            cells.append(f"τ={_fmt(r['kendall_tau'])} ρ={_fmt(r['spearman_rho'])} n={int(r['n'])} p={_fmt(r['kendall_p_perm'], '.4f')} (Holm p={_fmt(r['kendall_p_holm'], '.4f')})")
        md_parts.append(f"| {METRIC_LABELS[metric]} | " + " | ".join(cells) + " |\n")

    n_sig_raw = int((corr_df["kendall_p_perm"] < 0.05).sum())
    n_sig_holm = int((corr_df["kendall_p_holm"] < 0.05).sum())
    md_parts.append(f"\nSignificant at raw p<0.05: {n_sig_raw}/{len(corr_df)}. "
                    f"Significant at Holm-adjusted p<0.05: **{n_sig_holm}/{len(corr_df)}**.\n")

    md_parts.append("""
## Table 3: noise floor (canonical scope, Dynamic pooled) — can this metric resolve model differences?

Between-model spread (max-min across 9 canonical models) vs the mean
within-model between-instantiation SD (from stability data). A metric
whose spread is smaller than or comparable to its own noise floor cannot
reliably rank closely-scored models, independent of cross-benchmark
agreement.

| Metric | Between-model spread | Mean within-model SD | Spread/SD ratio |
|---|---|---|---|
""")
    for _, r in noise_df.iterrows():
        md_parts.append(f"| {METRIC_LABELS[r['metric']]} | {_fmt(r['between_model_spread'])} | "
                        f"{_fmt(r['mean_within_model_sd'])} | {_fmt(r['spread_to_sd_ratio'], '.1f')} |\n")

    md_parts.append("""
## Table 4: reliability — mean pairwise Kendall tau across instantiations (canonical scope, Dynamic)

| Metric | N=4 mean pairwise tau | All-pairs mean pairwise tau |
|---|---|---|
""")
    for _, r in rel_df.iterrows():
        md_parts.append(f"| {METRIC_LABELS[r['metric']]} | {_fmt(r['mean_pairwise_tau_n4'])} | {_fmt(r['mean_pairwise_tau_all_pairs'])} |\n")

    (ANALYSIS_DIR / "RANKING_MATRIX.md").write_text("".join(md_parts))
    print("".join(md_parts))
    print("\nWritten: analysis/ranking_matrix_scores.csv, analysis/ranking_matrix_correlations.csv, "
          "analysis/ranking_matrix_noise_floor.csv, analysis/ranking_matrix_reliability.csv, "
          "analysis/RANKING_MATRIX.md")


if __name__ == "__main__":
    main()
