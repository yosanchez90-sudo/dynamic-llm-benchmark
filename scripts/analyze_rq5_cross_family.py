"""RQ5 cross-family extension analysis (post-hoc, supplementary to the
canonical RQ5 primary) -- per analysis/RQ5_CROSS_FAMILY_PROPOSAL.md,
approved 2026-07-28. Adds DeepSeek-Coder-6.7B-Instruct,
CodeLlama-13B-Instruct, StarCoder2-15B-Instruct-v0.1, and
Mistral-7B-Instruct-v0.3 to the Dynamic<->ULT and Dynamic/ULT<->BigCodeBench
correlations, breaking the all-Qwen n=3 size-sweep confound
(analysis/RQ5_INTERPRETATION.md's Parts 2-3 finding).

Deliberately a SEPARATE script from analyze_rq5.py, not a modification of
it: analyze_rq5.py's pooled Mut@K over the 9 canonical models remains the
pre-registered RQ5 primary result and must stay reproducible exactly as
pre-registered. This script's output is explicitly the post-hoc
cross-family extension, same discipline as analyze_rq5_diagnostics.py.

Cross-family models are NEVER added to CANONICAL_MODELS (coverage_matrix.py)
-- they must not leak into Comparison A/B or StableMut@K (see
tests/test_canonical_models_boundary.py). This script imports its own
cross-family label list, unioned with CANONICAL_MODELS only for this
script's own ranking table.

Reports, for both raw Mut@K and the coverage-adjusted score
(RQ5_DIAGNOSTICS.md sec 3): Dynamic(pooled)<->ULT and Dynamic/ULT<->
BigCodeBench (Complete-split/Instruct-prompt and Hard-split/Instruct-prompt)
correlations, at both the canonical-only n and the canonical+cross-family n,
side by side -- the direct answer to "does the coverage-adjusted agreement
survive breaking the within-family confound."

Also flags any model x benchmark cell with n_defined < 20 for conditioned
Mut@K as too thin to quote (n_defined is a fraction of n_total, not of the
model count -- a model's mean over fewer than 20 baseline-passing problems
is itself a shaky point estimate, independent of any cross-model
correlation's own n).

Output: analysis/rq5_cross_family_model_ranking.csv,
analysis/rq5_cross_family_correlations.csv,
analysis/RQ5_CROSS_FAMILY_PROVENANCE.md
Usage: python scripts/analyze_rq5_cross_family.py
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
from src.Analysis.multiple_comparisons import holm_bonferroni
from src.Analysis.provenance import stamp_block

# Must never be added to coverage_matrix.py::CANONICAL_MODELS -- see this
# script's module docstring and tests/test_canonical_models_boundary.py.
CROSS_FAMILY_MODELS = [
    "deepseek-ai__deepseek-coder-6.7b-instruct",
    "codellama__CodeLlama-13b-Instruct-hf",
    "bigcode__starcoder2-15b-instruct-v0.1",
    "mistralai__Mistral-7B-Instruct-v0.3",
]
ALL_MODELS = CANONICAL_MODELS + CROSS_FAMILY_MODELS
PUBLIC_SCORES_PATH = ROOT / "analysis" / "rq5_public_scores.csv"
THIN_N_DEFINED = 20  # below this, a model's own mean Mut@K is a shaky point estimate


def _family(label: str) -> str:
    if label in CANONICAL_MODELS:
        return "canonical"
    return "cross_family"


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


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    dynamic = dynamic[dynamic["model_label"].isin(ALL_MODELS)]
    ult = load_records("data/results/ult", benchmark="ult")
    ult = ult[ult["model_label"].isin(ALL_MODELS)]

    rows = []
    for label in ALL_MODELS:
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
            "family": _family(label),
            "dynamic_n_total": len(d),
            "dynamic_n_defined": int(d["mutation_score"].notna().sum()),
            "dynamic_mutk_pooled": _mut(d),
            "dynamic_bp_pooled": _bp(d),
            "ult_n_total": len(u),
            "ult_n_defined": int(u["mutation_score"].notna().sum()),
            "ult_mutk": _mut(u),
            "ult_bp": _bp(u),
        }
        row["dynamic_coverage_adj"] = (
            row["dynamic_mutk_pooled"] * row["dynamic_bp_pooled"]
            if row["dynamic_mutk_pooled"] is not None and row["dynamic_bp_pooled"] is not None
            else None
        )
        row["ult_coverage_adj"] = (
            row["ult_mutk"] * row["ult_bp"]
            if row["ult_mutk"] is not None and row["ult_bp"] is not None
            else None
        )
        row["dynamic_thin"] = row["dynamic_n_defined"] < THIN_N_DEFINED
        row["ult_thin"] = row["ult_n_defined"] < THIN_N_DEFINED
        rows.append(row)

    ranking = pd.DataFrame(rows)

    if PUBLIC_SCORES_PATH.exists():
        public = pd.read_csv(PUBLIC_SCORES_PATH)
        ranking = ranking.merge(public, on="model_label", how="left")
    ranking.to_csv(ROOT / "analysis" / "rq5_cross_family_model_ranking.csv", index=False)

    print("=== Cross-family model ranking table ===")
    print(ranking.to_string(index=False))

    thin = ranking[ranking["dynamic_thin"] | ranking["ult_thin"]]
    print(f"\n{len(thin)} model(s) with n_defined < {THIN_N_DEFINED} on at least one side "
          f"(too thin to quote conditioned Mut@K for on that side):")
    for _, r in thin.iterrows():
        flags = []
        if r["dynamic_thin"]:
            flags.append(f"dynamic n_defined={r['dynamic_n_defined']}")
        if r["ult_thin"]:
            flags.append(f"ult n_defined={r['ult_n_defined']}")
        print(f"  {r['model_short']}: {', '.join(flags)}")

    corr_rows = []

    def _add_pair(pair_name: str, sub_df: pd.DataFrame, col_a: str, col_b: str, scope: str):
        sub = sub_df.dropna(subset=[col_a, col_b])
        if len(sub) < 3:
            print(f"\n{pair_name} ({scope}): only {len(sub)} model(s) -- skipping (need >=3)")
            return
        res = compute_correlations(sub[col_a].to_numpy(), sub[col_b].to_numpy())
        d = {"pair": pair_name, "scope": scope, "metric_a": col_a, "metric_b": col_b, **vars(res)}
        corr_rows.append(d)
        print(f"\n=== {pair_name} [{scope}] (n_models={res.n}) ===")
        print(f"  Pearson r  = {res.pearson_r:.3f}  p_perm={res.pearson_p_perm:.4f}")
        print(f"  Spearman rho = {res.spearman_rho:.3f}  p_perm={res.spearman_p_perm:.4f}")
        print(f"  Kendall tau  = {res.kendall_tau:.3f}  CI [{res.kendall_tau_ci_lo:.3f}, {res.kendall_tau_ci_hi:.3f}]  p_perm={res.kendall_p_perm:.4f}")

    canonical_only = ranking[ranking["family"] == "canonical"]

    for metric_a, metric_b, label in [
        ("dynamic_mutk_pooled", "ult_mutk", "Dynamic(pooled) <-> ULT [raw Mut@K]"),
        ("dynamic_coverage_adj", "ult_coverage_adj", "Dynamic(pooled) <-> ULT [coverage-adjusted]"),
    ]:
        _add_pair(label, canonical_only, metric_a, metric_b, "canonical-only")
        _add_pair(label, ranking, metric_a, metric_b, "canonical+cross-family")

    if "public_score" in ranking.columns:
        for metric_a, label in [
            ("dynamic_mutk_pooled", "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]"),
            ("dynamic_coverage_adj", "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]"),
        ]:
            _add_pair(label, canonical_only, metric_a, "public_score", "canonical-only")
            _add_pair(label, ranking, metric_a, "public_score", "canonical+cross-family")
        for metric_a, label in [
            ("ult_mutk", "ULT <-> public (Complete-split/Instruct) [raw Mut@K]"),
            ("ult_coverage_adj", "ULT <-> public (Complete-split/Instruct) [coverage-adjusted]"),
        ]:
            _add_pair(label, canonical_only, metric_a, "public_score", "canonical-only")
            _add_pair(label, ranking, metric_a, "public_score", "canonical+cross-family")
    if "public_score_hard" in ranking.columns:
        for metric_a, label in [
            ("dynamic_mutk_pooled", "Dynamic(pooled) <-> public (Hard-split/Instruct) [raw Mut@K]"),
            ("ult_mutk", "ULT <-> public (Hard-split/Instruct) [raw Mut@K]"),
        ]:
            _add_pair(label, canonical_only, metric_a, "public_score_hard", "canonical-only")
            _add_pair(label, ranking, metric_a, "public_score_hard", "canonical+cross-family")

    corr_df = pd.DataFrame(corr_rows)

    # --- Holm-Bonferroni within the RQ5/H6 family (PROJECT_BRIEF.md Sec 3.1) -
    # Scoped to the 12 headline Kendall-tau tests this project's own
    # write-up (RQ5_INTERPRETATION.md) actually narrates and treats as
    # evidence for/against cross-benchmark validity: 3 benchmark pairs
    # (Dynamic<->ULT, Dynamic<->public Complete-split, ULT<->public
    # Complete-split) x 2 scopes (canonical-only, canonical+cross-family) x
    # 2 metric versions (raw Mut@K, coverage-adjusted) = 12. Hard-split
    # pairs are a secondary consistency check, not part of this headline
    # family, and are excluded from this correction on that basis (not
    # silently -- stated here explicitly).
    headline_mask = corr_df["pair"].str.startswith("Dynamic(pooled) <-> ULT") | corr_df["pair"].str.contains("Complete-split")
    headline = corr_df[headline_mask].copy()
    corr_df["kendall_p_perm_holm"] = float("nan")
    if len(headline):
        headline["kendall_p_perm_holm"] = holm_bonferroni(headline["kendall_p_perm"].tolist())
        corr_df.loc[headline.index, "kendall_p_perm_holm"] = headline["kendall_p_perm_holm"]
        n_sig_raw = int((headline["kendall_p_perm"] < 0.05).sum())
        n_sig_holm = int((headline["kendall_p_perm_holm"] < 0.05).sum())
        print(f"\n=== Holm-Bonferroni within RQ5/H6's {len(headline)} headline Kendall-tau tests "
              f"(Dynamic<->ULT + Dynamic/ULT<->public Complete-split, both scopes, both metric versions) ===")
        print(headline[["pair", "scope", "kendall_tau", "kendall_p_perm", "kendall_p_perm_holm"]].to_string(index=False))
        print(f"Significant at raw p<0.05: {n_sig_raw}/{len(headline)}. "
              f"Significant at Holm-adjusted p<0.05: {n_sig_holm}/{len(headline)}.")
    else:
        n_sig_raw = n_sig_holm = 0
        print("\n=== Holm-Bonferroni within RQ5/H6: skipped -- no headline pairs computed yet "
              "(public scores not merged) ===")

    corr_df.to_csv(ROOT / "analysis" / "rq5_cross_family_correlations.csv", index=False)

    landed = ranking[ranking["family"] == "cross_family"]
    expected_dynamic, expected_ult = 300, 400
    completeness_lines = []
    for _, r in landed.iterrows():
        dyn_status = "COMPLETE" if r["dynamic_n_total"] >= expected_dynamic else f"PARTIAL ({r['dynamic_n_total']}/{expected_dynamic})"
        ult_status = ("COMPLETE" if r["ult_n_total"] >= expected_ult
                      else ("MISSING" if r["ult_n_total"] == 0 else f"PARTIAL ({r['ult_n_total']}/{expected_ult})"))
        completeness_lines.append(f"- {r['model_short']}: Dynamic {dyn_status}, ULT {ult_status}")
    missing_cross_family = sorted(set(CROSS_FAMILY_MODELS) - set(landed["model_label"]))
    for label in missing_cross_family:
        completeness_lines.append(f"- {_model_shortname(label)}: Dynamic MISSING, ULT MISSING")

    provenance = f"""# RQ5 cross-family extension -- correlations (raw tables)

{stamp_block("scripts/analyze_rq5_cross_family.py")}
Per `analysis/RQ5_CROSS_FAMILY_PROPOSAL.md` (approved 2026-07-28). This is a
POST-HOC, supplementary extension -- `analysis/RQ5_PROVENANCE.md`
(canonical 9 models, `scripts/analyze_rq5.py`) remains the pre-registered
RQ5 primary result and is NOT modified or superseded by anything here.
Cross-family models are never part of `coverage_matrix.py::CANONICAL_MODELS`
and never enter Comparison A/B or StableMut@K (see
`tests/test_canonical_models_boundary.py`).

## Cross-family data completeness at time of this run

{chr(10).join(completeness_lines) if completeness_lines else "(none landed yet)"}

**If any model above is PARTIAL or MISSING, every "canonical+cross-family"
correlation below is provisional** -- re-run this script once all 4
candidates' Dynamic + ULT jobs complete (see
`data/download_logs/rq5_cross_family_job_map_20260728.md` for job IDs) and
treat only a run with all 4 COMPLETE as the number that answers the
supervisor's bottom-up validity question.

## Model ranking table (n_defined flags cells too thin to quote, n_defined<{THIN_N_DEFINED})

{ranking.to_string(index=False)}

## Correlations: canonical-only vs canonical+cross-family, side by side

{corr_df.to_string(index=False) if len(corr_df) else "(none computed)"}

## Holm-Bonferroni within RQ5/H6 (PROJECT_BRIEF.md Sec 3.1)

Scoped to the {len(headline)} headline Kendall-tau tests this project's
own interpretation (`analysis/RQ5_INTERPRETATION.md`) actually narrates:
3 benchmark pairs (Dynamic<->ULT, Dynamic<->public Complete-split,
ULT<->public Complete-split) x 2 scopes (canonical-only, canonical+
cross-family) x 2 metric versions (raw Mut@K, coverage-adjusted).
Hard-split pairs are a secondary consistency check, excluded from this
family on that basis, not silently.

{headline[["pair", "scope", "kendall_tau", "kendall_p_perm", "kendall_p_perm_holm"]].to_string(index=False) if len(headline) else "(skipped -- no headline pairs computed yet, public scores not merged)"}

Significant at raw p<0.05: {n_sig_raw}/{len(headline)}. Significant at Holm-adjusted p<0.05: **{n_sig_holm}/{len(headline)}**.
"""
    (ROOT / "analysis" / "RQ5_CROSS_FAMILY_PROVENANCE.md").write_text(provenance)
    print("\nWritten: analysis/rq5_cross_family_model_ranking.csv, "
          "analysis/rq5_cross_family_correlations.csv, "
          "analysis/RQ5_CROSS_FAMILY_PROVENANCE.md")


if __name__ == "__main__":
    main()
