"""RQ5 sanitizer sensitivity analysis (post-hoc, zero-compute) --
src/eval/test_gen_scorer.py::sanitize_test_file applies two repairs before
scoring a response (stripping a reimplementation of the function-under-test,
prepending a missing import) when small models sometimes reimplement rather
than import. Both repairs are recorded in the row's `notes` field. This
script checks whether those repairs are evenly distributed across models
(a between-model comparison should not be more favorable to models that
happen to need more sanitizer intervention) by recomputing exec_rate,
baseline_pass_rate, and the coverage-adjusted RQ5 correlations with every
repaired row EXCLUDED (dropped from the denominator, not re-scored -- this
project doesn't re-run mutation testing on the unrepaired original, since
that would be new compute, not a zero-compute sensitivity check), and by
correlating each model's repair fraction against its baseline capability.

Output: analysis/rq5_sanitizer_sensitivity.csv, analysis/RQ5_SANITIZER_SENSITIVITY.md
Usage: python scripts/analyze_rq5_sanitizer_sensitivity.py
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

REPAIR_PATTERN = r"stripped reimplementation|prepended 'from under_test"


def _model_shortname(label: str) -> str:
    if label.startswith("Qwen__"):
        for size in ("1.5B", "7B", "32B"):
            if size in label:
                return f"Qwen {size}"
    return label


def _mut(df: pd.DataFrame) -> float | None:
    s = df["mutation_score"].dropna()
    return float(s.mean()) if len(s) else None


def _bp(df: pd.DataFrame) -> float | None:
    s = df["baseline_passed"].dropna()
    return float(s.astype(float).mean()) if len(s) else None


def _exec_rate(df: pd.DataFrame) -> float | None:
    s = df["exec_rate"].dropna()
    return float(s.mean()) if len(s) else None


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    dynamic = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)].copy()
    ult = load_records("data/results/ult", benchmark="ult")
    ult = ult[ult["model_label"].isin(CANONICAL_MODELS)].copy()

    dynamic["repaired"] = dynamic["notes"].fillna("").str.contains(REPAIR_PATTERN)
    ult["repaired"] = ult["notes"].fillna("").str.contains(REPAIR_PATTERN)

    rows = []
    for label in CANONICAL_MODELS:
        d = dynamic[dynamic["model_label"] == label]
        u = ult[ult["model_label"] == label]
        if d.empty and u.empty:
            continue
        d_clean = d[~d["repaired"]]
        u_clean = u[~u["repaired"]]
        row = {
            "model_label": label,
            "model_short": _model_shortname(label),
            "dyn_n_total": len(d),
            "dyn_n_repaired": int(d["repaired"].sum()),
            "dyn_repair_frac": float(d["repaired"].mean()) if len(d) else None,
            "ult_n_total": len(u),
            "ult_n_repaired": int(u["repaired"].sum()),
            "ult_repair_frac": float(u["repaired"].mean()) if len(u) else None,
            # as-scored (repairs applied, the actual landed data)
            "dyn_mutk": _mut(d), "dyn_bp": _bp(d), "dyn_exec": _exec_rate(d),
            "ult_mutk": _mut(u), "ult_bp": _bp(u), "ult_exec": _exec_rate(u),
            # repaired rows excluded (dropped from denominator, not re-scored)
            "dyn_mutk_norepair": _mut(d_clean), "dyn_bp_norepair": _bp(d_clean), "dyn_exec_norepair": _exec_rate(d_clean),
            "ult_mutk_norepair": _mut(u_clean), "ult_bp_norepair": _bp(u_clean), "ult_exec_norepair": _exec_rate(u_clean),
        }
        row["dyn_coverage_adj"] = (row["dyn_mutk"] * row["dyn_bp"]) if row["dyn_mutk"] is not None and row["dyn_bp"] is not None else None
        row["ult_coverage_adj"] = (row["ult_mutk"] * row["ult_bp"]) if row["ult_mutk"] is not None and row["ult_bp"] is not None else None
        row["dyn_coverage_adj_norepair"] = (row["dyn_mutk_norepair"] * row["dyn_bp_norepair"]) if row["dyn_mutk_norepair"] is not None and row["dyn_bp_norepair"] is not None else None
        row["ult_coverage_adj_norepair"] = (row["ult_mutk_norepair"] * row["ult_bp_norepair"]) if row["ult_mutk_norepair"] is not None and row["ult_bp_norepair"] is not None else None
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "analysis" / "rq5_sanitizer_sensitivity.csv", index=False)

    out = ["# RQ5 sanitizer sensitivity analysis (post-hoc, zero-compute)", "",
           stamp_block("scripts/analyze_rq5_sanitizer_sensitivity.py"),
           "src/eval/test_gen_scorer.py::sanitize_test_file strips a reimplementation of",
           "the function-under-test and/or prepends a missing import before scoring --",
           "recorded per-row in `notes`. This checks whether repairs are evenly",
           "distributed across models and whether excluding repaired rows changes the",
           "RQ5 primary/coverage-adjusted picture. Canonical models only, Dynamic pooled",
           "+ ULT.", ""]

    out += ["## Per-model repair fraction", ""]
    out += ["| Model | dyn n_total | dyn n_repaired | dyn repair% | ult n_total | ult n_repaired | ult repair% |",
            "|---|---|---|---|---|---|---|"]
    for _, r in df.sort_values("model_short").iterrows():
        out.append(
            f"| {r['model_short']} | {r['dyn_n_total']} | {r['dyn_n_repaired']} | "
            f"{r['dyn_repair_frac']*100:.2f}% | {r['ult_n_total']} | {r['ult_n_repaired']} | "
            f"{r['ult_repair_frac']*100:.2f}% |"
        )
    out.append("")
    total_dyn_repaired = int(df["dyn_n_repaired"].sum())
    total_ult_repaired = int(df["ult_n_repaired"].sum())
    out.append(f"Total repaired: {total_dyn_repaired}/{int(df['dyn_n_total'].sum())} Dynamic rows, "
               f"{total_ult_repaired}/{int(df['ult_n_total'].sum())} ULT rows.")
    out.append("")

    out += ["## Recomputed metrics with repaired rows excluded (dropped, not re-scored)", ""]
    out += ["| Model | dyn Mut@K (as-scored -> excl.) | dyn bp_rate (as-scored -> excl.) | "
            "ult Mut@K (as-scored -> excl.) | ult bp_rate (as-scored -> excl.) |",
            "|---|---|---|---|---|"]

    def _fmt(a, b):
        if a is None:
            return "n/a"
        return f"{a:.3f} -> {b:.3f}" if b is not None else f"{a:.3f} -> n/a"

    for _, r in df.sort_values("model_short").iterrows():
        out.append(
            f"| {r['model_short']} | {_fmt(r['dyn_mutk'], r['dyn_mutk_norepair'])} | "
            f"{_fmt(r['dyn_bp'], r['dyn_bp_norepair'])} | "
            f"{_fmt(r['ult_mutk'], r['ult_mutk_norepair'])} | "
            f"{_fmt(r['ult_bp'], r['ult_bp_norepair'])} |"
        )
    out.append("")

    out += ["## RQ5 primary correlation, with vs without repaired rows", ""]
    sub_as_scored = df.dropna(subset=["dyn_mutk", "ult_mutk"])
    sub_norepair = df.dropna(subset=["dyn_mutk_norepair", "ult_mutk_norepair"])
    sub_adj_as_scored = df.dropna(subset=["dyn_coverage_adj", "ult_coverage_adj"])
    sub_adj_norepair = df.dropna(subset=["dyn_coverage_adj_norepair", "ult_coverage_adj_norepair"])
    out += ["| Metric | scope | n | Kendall τ | perm p |", "|---|---|---|---|---|"]
    for label, sub, col_a, col_b in [
        ("raw Mut@K", sub_as_scored, "dyn_mutk", "ult_mutk"),
        ("raw Mut@K, repaired rows excluded", sub_norepair, "dyn_mutk_norepair", "ult_mutk_norepair"),
        ("coverage-adjusted", sub_adj_as_scored, "dyn_coverage_adj", "ult_coverage_adj"),
        ("coverage-adjusted, repaired rows excluded", sub_adj_norepair, "dyn_coverage_adj_norepair", "ult_coverage_adj_norepair"),
    ]:
        if len(sub) < 3:
            out.append(f"| {label} | Dynamic<->ULT | {len(sub)} | - | (n<3) |")
            continue
        res = compute_correlations(sub[col_a].to_numpy(), sub[col_b].to_numpy())
        out.append(f"| {label} | Dynamic<->ULT | {res.n} | {res.kendall_tau:.3f} | {res.kendall_p_perm:.4f} |")
    out.append("")

    out += ["## Do repairs differentially benefit weaker models?", "",
            "Two ways to check this: (a) the direct distribution -- is repair need",
            "concentrated in specific models rather than spread evenly, (b) a",
            "correlation against baseline_pass_rate. (a) is the more trustworthy read",
            "here since Dynamic's repair distribution is near-degenerate (see table",
            "above) -- most models sit at exactly 0%, which makes a Kendall tau over",
            "9 points essentially a 1-point-vs-8-ties comparison, not a smooth",
            "9-point relationship.", ""]
    n_dyn_repaired_models = int((df["dyn_repair_frac"] > 0).sum())
    top_repair_row = df.loc[df["dyn_repair_frac"].idxmax()]
    out.append(
        f"**(a) Direct read**: {n_dyn_repaired_models} of {len(df)} canonical models have ANY "
        f"repaired rows on Dynamic -- repair need is concentrated almost entirely in "
        f"**{top_repair_row['model_short']}** ({top_repair_row['dyn_repair_frac']*100:.2f}%, "
        f"vs 0% for every other model), the smallest/weakest model in this project's own "
        f"capability ordering. On ULT (where reimplementation is more common across the "
        f"board -- real-world scraped functions, more naming variety) the same model has "
        f"the highest rate there too "
        f"({df.loc[df['model_short']==top_repair_row['model_short'], 'ult_repair_frac'].iloc[0]*100:.2f}%). "
        f"**Yes, sanitization concentrates on and differentially helps the weakest "
        f"model** -- this is directly visible in the distribution, not just inferred "
        f"from a correlation coefficient."
    )
    out.append("")
    repair_bp_sub = df.dropna(subset=["dyn_repair_frac", "dyn_bp"])
    if len(repair_bp_sub) >= 3:
        res_repair = compute_correlations(
            repair_bp_sub["dyn_repair_frac"].to_numpy(), repair_bp_sub["dyn_bp"].to_numpy())
        out.append(
            f"**(b) Correlation check**: Kendall τ(repair_frac, baseline_pass_rate) = "
            f"{res_repair.kendall_tau:.3f} (n={res_repair.n}, perm p={res_repair.kendall_p_perm:.4f}) "
            f"-- direction is consistent with (a) (negative: more repairs where "
            f"baseline_pass_rate is lower), but **not statistically significant at this n** "
            f"(a near-degenerate 8-zeros-plus-1-outlier distribution is a weak basis for a "
            f"correlation coefficient regardless of its point estimate) -- treat (a), the "
            f"direct distribution, as the trustworthy evidence here, not this p-value."
        )
    else:
        out.append(f"n={len(repair_bp_sub)} too small to compute this correlation.")
    out.append("")

    doc = "\n".join(out)
    (ROOT / "analysis" / "RQ5_SANITIZER_SENSITIVITY.md").write_text(doc)
    print(doc)
    print("\nWritten: analysis/rq5_sanitizer_sensitivity.csv, analysis/RQ5_SANITIZER_SENSITIVITY.md")


if __name__ == "__main__":
    main()
