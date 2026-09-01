"""RQ5 diagnostic follow-up, all post-hoc, all zero-compute (no new GPU/
API work; every number here comes from data already on disk).
scripts/analyze_rq5.py's pooled-Mut@K result remains the pre-registered
PRIMARY result (analysis/RQ5_ANALYSIS_PLAN.md). This script exists to
DIAGNOSE why Dynamic(pooled)<->ULT rank agreement came out low in the
original n=7 measurement (Kendall tau=0.143), not to replace or flatter
that result. The current reading moves as data lands, see this script's
own generated analysis/RQ5_DIAGNOSTICS.md for the live number, computed
fresh on every run, not this docstring.

Diagnostics, in order:
  1. Tier-matched (Dynamic-L4-only, matching Comparison A's CC>=8
     convention) vs pooled vs per-tier correlations, side by side, plus a
     THIN_N_DEFINED-filtered version excluding any model whose own
     per-tier/pooled mean rests on fewer than 20 baseline-passing problems.
  2. Discrimination audit: score spread (range, SD, adjacent-rank gaps)
     per tier and pooled, quantifies the ceiling-effect compression
     visible in analysis/figures/rq5_correlation.png.
  2b. Noise-floor / resolving-power audit: for pooled and each tier,
     compares the between-model score spread (sec 2) against the mean
     within-model between-instantiation SD (RQ4.1 stability data).
     When the former is smaller than the latter, the benchmark cannot
     resolve those models' rank order; it's noise, not signal.
  3. Conditioning/survivorship audit: Mut@K is only defined where
     baseline_passed=True, so each model is scored on a DIFFERENT subset
     of problems, and L4 coverage is thin or entirely missing for several
     models, not just one (checked explicitly, not assumed). Reports
     n_defined + baseline_pass_rate per model/tier, a coverage-adjusted
     score (Mut@K x baseline_pass_rate, which does NOT drop the
     conditioning, see caveat below), and re-runs the rank correlation on
     that adjusted score, both unfiltered and with thin cells excluded.
  4. Attenuation: disattenuates the observed cross-benchmark tau using
     RQ4.1's within-Dynamic reliability ceiling (N=4 mean pairwise Kendall
     tau, computed live from CANONICAL_MODELS-filtered data, see
     src.Analysis.stability.mean_pairwise_tau_scoped, not a hard-coded
     constant, since analysis/STABILITY.md's own point estimate moves as
     data lands) via the classical
     rho_disattenuated = rho_observed / sqrt(reliability_x * reliability_y)
     formula. States the formula's assumptions explicitly (derived for
     Pearson r under classical test theory; applying it to Kendall tau is
     an approximation, not a rigorously derived correction for rank
     statistics). No repeat-measure reliability estimate exists for ULT in
     this project (K=1, no instantiation concept for a static benchmark),
     stated plainly, not assumed. Reports the reliability figure's
     own n and per-model instantiation counts (they vary, not a single
     clean n).

Output: analysis/RQ5_DIAGNOSTICS.md
Usage: python scripts/analyze_rq5_diagnostics.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import pandas as pd

from coverage_matrix import CANONICAL_MODELS
from src.Analysis.correlation import compute_correlations
from src.Analysis.loader import load_records
from src.Analysis.stability import mean_pairwise_tau_scoped, pairwise_kendall_tau, stable_mut_at_k

# N=4 scope (PROJECT_BRIEF.md Sec 11): reliability is computed from pairs
# among instantiations 1-4 only, excluding instantiation 5 (the deferred K=5
# sensitivity sweep, only ever partially run for a few models). Shared with
# analyze_stability.py's own reporting via mean_pairwise_tau_scoped().
N4_INSTANTIATIONS = {"1", "2", "3", "4"}
THIN_N_DEFINED = 20  # below this, a model's own mean Mut@K is a shaky point estimate


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                        cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


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

    rows = []
    for label in CANONICAL_MODELS:
        d = dynamic[dynamic["model_label"] == label]
        u = ult[ult["model_label"] == label]
        if d.empty and u.empty:
            continue
        row = {"model_label": label, "model_short": _model_shortname(label)}
        for tier_label, sub in [("pooled", d), ("L1", d[d["tier"] == "L1"]),
                                 ("L2", d[d["tier"] == "L2"]), ("L3", d[d["tier"] == "L3"]),
                                 ("L4", d[d["tier"] == "L4"])]:
            scored = sub["mutation_score"].dropna()
            bp = sub["baseline_passed"].dropna()
            row[f"dyn_{tier_label}_mutk"] = float(scored.mean()) if len(scored) else None
            row[f"dyn_{tier_label}_n_total"] = len(sub)
            row[f"dyn_{tier_label}_n_defined"] = len(scored)
            row[f"dyn_{tier_label}_bp_rate"] = float(bp.astype(float).mean()) if len(bp) else None
        u_scored = u["mutation_score"].dropna()
        u_bp = u["baseline_passed"].dropna()
        row["ult_mutk"] = float(u_scored.mean()) if len(u_scored) else None
        row["ult_n_total"] = len(u)
        row["ult_n_defined"] = len(u_scored)
        row["ult_bp_rate"] = float(u_bp.astype(float).mean()) if len(u_bp) else None
        rows.append(row)

    df = pd.DataFrame(rows)

    # Pre-registered PRIMARY reading (pooled, unfiltered Dynamic Mut@K vs ULT) --
    # computed once, live, here, so every prose reference below (including the
    # preamble) cites the SAME number the tables show, instead of a hardcoded
    # literal that silently goes stale as new data lands (see CONVENTIONS.md's
    # library-fallback/hardcoded-summary discipline).
    _primary_sub = df.dropna(subset=["dyn_pooled_mutk", "ult_mutk"])
    _primary_res = (
        compute_correlations(_primary_sub["dyn_pooled_mutk"].to_numpy(), _primary_sub["ult_mutk"].to_numpy())
        if len(_primary_sub) >= 3 else None
    )
    _primary_tau_str = f"{_primary_res.kendall_tau:.3f}" if _primary_res is not None else "n/a"
    _primary_n_str = str(_primary_res.n) if _primary_res is not None else "n/a"

    out = ["# RQ5 diagnostics (post-hoc, zero-compute)", "",
           f"Generated: {datetime.now(timezone.utc).isoformat()}",
           f"Git commit: {_git_commit()}",
           "Script: scripts/analyze_rq5_diagnostics.py", "",
           "Pooled Dynamic Mut@K vs ULT remains the pre-registered PRIMARY result",
           "(analysis/RQ5_ANALYSIS_PLAN.md, analysis/RQ5_PROVENANCE.md). Everything",
           "below is post-hoc diagnostic of that result's low rank agreement (Kendall",
           f"tau={_primary_tau_str}, n={_primary_n_str}), not a replacement for it.", ""]

    # --- 1. Tier-matched vs pooled vs per-tier -------------------------------
    out += ["## 1. Tier-matched (L4-only) vs pooled vs per-tier", ""]
    out += ["Dynamic-L4 is the CC>=8 band, matching ULT exactly (Comparison A's own",
            "convention, src/Analysis/comparison.py). Pooling L1-L4 compares a",
            "mixed-difficulty benchmark (L1/L2 near-ceiling for most models) against a",
            "hard-only one. This is the first candidate explanation for low pooled",
            "rank agreement.", ""]
    out += ["| Dynamic side | n | Pearson r | CI | Spearman ρ | CI | Kendall τ | CI | perm p (τ) |",
            "|---|---|---|---|---|---|---|---|---|"]
    for tier_label in ["pooled", "L1", "L2", "L3", "L4"]:
        sub = df.dropna(subset=[f"dyn_{tier_label}_mutk", "ult_mutk"])
        if len(sub) < 3:
            out.append(f"| {tier_label} | {len(sub)} | - | - | - | - | - | - | (n<3, skipped) |")
            continue
        res = compute_correlations(sub[f"dyn_{tier_label}_mutk"].to_numpy(), sub["ult_mutk"].to_numpy())
        out.append(
            f"| {tier_label} | {res.n} | {res.pearson_r:.3f} | "
            f"[{res.pearson_r_ci_lo:.2f}, {res.pearson_r_ci_hi:.2f}] | "
            f"{res.spearman_rho:.3f} | [{res.spearman_rho_ci_lo:.2f}, {res.spearman_rho_ci_hi:.2f}] | "
            f"{res.kendall_tau:.3f} | [{res.kendall_tau_ci_lo:.2f}, {res.kendall_tau_ci_hi:.2f}] | "
            f"{res.kendall_p_perm:.4f} |"
        )
    out.append("")
    out += [f"**Same table, thin cells excluded** (n_defined<{THIN_N_DEFINED} on either side for that "
            f"tier, a model whose own mean is a shaky point estimate shouldn't drive a "
            f"cross-model correlation any more than it should drive a paired comparison, "
            f"same threshold as Comparison A's thin-cell audit,",
            "`analysis/COMPARISON_PROVENANCE.md`):", ""]
    out += ["| Dynamic side | n | Kendall τ | CI | perm p (τ) | thin model(s) excluded |",
            "|---|---|---|---|---|---|"]
    for tier_label in ["pooled", "L1", "L2", "L3", "L4"]:
        sub_all = df.dropna(subset=[f"dyn_{tier_label}_mutk", "ult_mutk"])
        thin_mask = (sub_all[f"dyn_{tier_label}_n_defined"] < THIN_N_DEFINED) | (sub_all["ult_n_defined"] < THIN_N_DEFINED)
        excluded = sorted(sub_all.loc[thin_mask, "model_short"].tolist())
        sub_thick = sub_all.loc[~thin_mask]
        if len(sub_thick) < 3:
            out.append(f"| {tier_label} | {len(sub_thick)} | - | - | (n<3, skipped) | {excluded or 'none'} |")
            continue
        res_t = compute_correlations(sub_thick[f"dyn_{tier_label}_mutk"].to_numpy(), sub_thick["ult_mutk"].to_numpy())
        out.append(
            f"| {tier_label} | {res_t.n} | {res_t.kendall_tau:.3f} | "
            f"[{res_t.kendall_tau_ci_lo:.2f}, {res_t.kendall_tau_ci_hi:.2f}] | "
            f"{res_t.kendall_p_perm:.4f} | {excluded or 'none'} |"
        )
    out.append("")

    # --- 2. Discrimination audit ---------------------------------------------
    out += ["## 2. Discrimination audit: score spread per tier / pooled", ""]
    out += ["| Dynamic side | n models | min | max | range | SD | mean adjacent-rank gap |",
            "|---|---|---|---|---|---|---|"]
    for tier_label in ["pooled", "L1", "L2", "L3", "L4"]:
        vals = df[f"dyn_{tier_label}_mutk"].dropna().sort_values().to_numpy()
        if len(vals) < 2:
            continue
        gaps = np.diff(vals)
        out.append(
            f"| {tier_label} | {len(vals)} | {vals.min():.3f} | {vals.max():.3f} | "
            f"{vals.max()-vals.min():.3f} | {vals.std(ddof=1):.3f} | {gaps.mean():.4f} |"
        )
    ult_vals = df["ult_mutk"].dropna().sort_values().to_numpy()
    ult_gaps = np.diff(ult_vals)
    out.append(
        f"| ULT | {len(ult_vals)} | {ult_vals.min():.3f} | {ult_vals.max():.3f} | "
        f"{ult_vals.max()-ult_vals.min():.3f} | {ult_vals.std(ddof=1):.3f} | {ult_gaps.mean():.4f} |"
    )
    out.append("")
    # explicit compression claim check
    pooled_vals = df["dyn_pooled_mutk"].dropna().sort_values().to_numpy()
    within_05 = sum(1 for v in pooled_vals if pooled_vals.max() - v <= 0.05)
    within_001_pairs = sum(1 for a, b in zip(pooled_vals, pooled_vals[1:]) if b - a <= 0.001)
    out.append(f"Pooled: {within_05}/{len(pooled_vals)} models within 0.05 of the max; "
               f"{within_001_pairs} adjacent pair(s) within 0.001 of each other.")
    best_tier = max(["L1", "L2", "L3", "L4"],
                     key=lambda t: (df[f"dyn_{t}_mutk"].dropna().to_numpy().std(ddof=1)
                                    if df[f"dyn_{t}_mutk"].dropna().shape[0] > 1 else -1))
    out.append(f"Highest-SD (best-discriminating) tier among the top models: **{best_tier}**.")
    out.append("")

    # --- 2b. Noise-floor / resolving-power audit ------------------------------
    out += ["## 2b. Noise-floor / resolving-power audit", "",
            "The discrimination audit above (sec 2) shows the between-model SPREAD. On",
            "its own that doesn't say whether pooled Mut@K can RESOLVE which",
            "model ranks above which. For that, the spread has to be compared against",
            "each model's own between-instantiation noise (RQ4.1, `analysis/STABILITY.md`).",
            "If two adjacent models' score gap is smaller than either model's own SD",
            "across repeat instantiations, their relative rank is not distinguishable from",
            "noise. Re-running the same model would plausibly reorder them on its own.",
            "ULT has no repeat-instantiation concept (K=1, static benchmark), so this audit",
            "is Dynamic-only.", ""]
    stable_pooled = stable_mut_at_k(dynamic)
    stable_by_tier = stable_mut_at_k(dynamic, extra_group_cols=("tier",))
    out += ["| Dynamic side | between-model SD | mean within-model SD (n models w/ 2+ inst) | ratio (between/within) |",
            "|---|---|---|---|"]
    noise_floor_rows = {}
    for tier_label in ["pooled", "L1", "L2", "L3", "L4"]:
        between_vals = df[f"dyn_{tier_label}_mutk"].dropna().to_numpy()
        if len(between_vals) < 2:
            continue
        between_sd = between_vals.std(ddof=1)
        if tier_label == "pooled":
            within = stable_pooled[stable_pooled["n_instantiations"] >= 2]["sd_mut_at_k"]
        else:
            within = stable_by_tier[
                (stable_by_tier["tier"] == tier_label) & (stable_by_tier["n_instantiations"] >= 2)
            ]["sd_mut_at_k"]
        if len(within) == 0:
            out.append(f"| {tier_label} | {between_sd:.4f} | n/a (no model with 2+ scorable instantiations) | n/a |")
            continue
        within_mean = float(within.mean())
        ratio = between_sd / within_mean if within_mean > 0 else float("inf")
        noise_floor_rows[tier_label] = (between_sd, within_mean, ratio)
        out.append(f"| {tier_label} | {between_sd:.4f} | {within_mean:.4f} | {ratio:.2f} |")
    out.append("")
    pooled_ratio = noise_floor_rows.get("pooled")
    if pooled_ratio is not None:
        out.append(f"**Pooled ratio = {pooled_ratio[2]:.2f}** ({'below 1: between-model spread is SMALLER than average within-model noise' if pooled_ratio[2] < 1 else 'above 1'}).")
    out.append("")

    # Adjacent-rank resolvability: sort models by pooled Mut@K, compare each
    # adjacent gap to the larger of the two models' own SD (from stable_pooled).
    # Only models with 2+ scorable instantiations have a REAL SD estimate --
    # a single-instantiation model's sd_mut_at_k is filled to 0.0 by
    # stable_mut_at_k() (undefined std of one value), which would otherwise
    # look like "zero noise" and falsely inflate resolvability chains via
    # the max(sd_a, sd_b) check below. Excluded here, not defaulted to 0.
    sd_by_model = dict(zip(
        stable_pooled.loc[stable_pooled["n_instantiations"] >= 2, "model_label"],
        stable_pooled.loc[stable_pooled["n_instantiations"] >= 2, "sd_mut_at_k"],
    ))
    pooled_sorted = df.dropna(subset=["dyn_pooled_mutk"]).sort_values("dyn_pooled_mutk", ascending=False)
    unresolved_chain: list[str] = []
    max_chain: list[str] = []
    prev_label = None
    for _, r in pooled_sorted.iterrows():
        label, short, score = r["model_label"], r["model_short"], r["dyn_pooled_mutk"]
        if prev_label is not None:
            gap = prev_score - score
            sd_a = sd_by_model.get(prev_label)
            sd_b = sd_by_model.get(label)
            resolvable = (sd_a is None or sd_b is None) or (gap >= max(sd_a, sd_b))
            if not resolvable:
                if not unresolved_chain:
                    unresolved_chain = [prev_short]
                unresolved_chain.append(short)
                if len(unresolved_chain) > len(max_chain):
                    max_chain = list(unresolved_chain)
            else:
                unresolved_chain = []
        prev_label, prev_short, prev_score = label, short, score
    out.append("**Largest run of adjacent models whose pooled Mut@K gap is smaller than "
               "either model's own between-instantiation SD (i.e. not reliably orderable "
               "against each other from this data alone)**: "
               f"{' > '.join(max_chain) if len(max_chain) >= 2 else '(none found)'}"
               + (f", {len(max_chain)} models." if len(max_chain) >= 2 else ""))
    if len(max_chain) >= 2:
        chain_scores = pooled_sorted[pooled_sorted["model_short"].isin(max_chain)]["dyn_pooled_mutk"]
        chain_spread = float(chain_scores.max() - chain_scores.min())
        chain_sds = [f"{sd_by_model.get(pooled_sorted[pooled_sorted['model_short']==m]['model_label'].iloc[0]):.3f}"
                     for m in max_chain if pooled_sorted[pooled_sorted['model_short']==m]['model_label'].iloc[0] in sd_by_model]
        out.append(f"Their pooled spread is {chain_spread:.3f}; their own individual SDs are "
                   f"{', '.join(chain_sds)}. The spread is smaller than every one of these "
                   f"models' own measurement noise. **Rewriting the tau={_primary_tau_str} "
                   f"interpretation accordingly: at least part of the low rank agreement is not "
                   f"that Dynamic and ULT disagree about these models' quality, it's that pooled "
                   f"Mut@K lacks the resolving power to rank them AT ALL, on this data alone. "
                   f"\"the benchmarks disagree\" and \"this benchmark can't resolve close scores\" "
                   f"are different claims, and the tau={_primary_tau_str} headline conflates "
                   f"them.**")
    out.append("")

    # --- 3. Conditioning / survivorship audit --------------------------------
    out += ["## 3. Conditioning / survivorship audit", "",
            "Mut@K is defined only where baseline_passed=True. Each model's pooled/per-tier",
            "mean is therefore computed over a DIFFERENT subset of problems, not a shared",
            "denominator. coverage_adjusted = Mut@K x baseline_pass_rate folds the",
            "conditioning back in (a model that rarely produces a baseline-passing suite",
            "gets penalised, not just averaged over the suites that happened to pass).",
            "This is NOT the same estimand as Mut@K itself, reported as a robustness check,",
            "not a replacement metric.", ""]
    out += ["| Model | tier | n_total | n_defined | baseline_pass_rate | Mut@K | coverage_adjusted |",
            "|---|---|---|---|---|---|---|"]
    df["dyn_pooled_coverage_adj"] = df["dyn_pooled_mutk"] * df["dyn_pooled_bp_rate"]
    df["ult_coverage_adj"] = df["ult_mutk"] * df["ult_bp_rate"]
    for _, r in df.iterrows():
        for tier_label in ["pooled", "L4"]:
            mutk = r.get(f"dyn_{tier_label}_mutk")
            bp = r.get(f"dyn_{tier_label}_bp_rate")
            adj = mutk * bp if (mutk is not None and bp is not None) else None
            out.append(f"| {r['model_short']} | dyn_{tier_label} | {r.get(f'dyn_{tier_label}_n_total')} | "
                       f"{r.get(f'dyn_{tier_label}_n_defined')} | "
                       f"{'%.3f'%bp if bp is not None else 'n/a'} | "
                       f"{'%.3f'%mutk if mutk is not None else 'n/a'} | "
                       f"{'%.4f'%adj if adj is not None else 'n/a'} |")
        out.append(f"| {r['model_short']} | ult | {r['ult_n_total']} | {r['ult_n_defined']} | "
                   f"{r['ult_bp_rate']:.3f} | {r['ult_mutk']:.3f} | {r['ult_coverage_adj']:.4f} |")
    out.append("")

    # --- L4 coverage flag, computed generally, NOT just Qwen-1.5B --------
    def _l4_status(n_total, n_defined) -> str:
        if n_total == 0:
            return "MISSING (never attempted, data-collection gap, not a capability result)"
        if n_defined == 0:
            return "FLOOR (attempted, 0 passed baseline, a genuine capability finding)"
        if n_defined < THIN_N_DEFINED:
            return f"THIN (n_defined={n_defined} < {THIN_N_DEFINED})"
        return "OK"

    l4_flags = []
    for _, r in df.iterrows():
        status = _l4_status(r["dyn_L4_n_total"], r["dyn_L4_n_defined"])
        if status != "OK":
            l4_flags.append((r["model_short"], status))
    out.append(f"**Flagged explicitly ({len(l4_flags)} of {len(df)} canonical models have a "
               f"compromised L4 contribution to their pooled score, not just one)**:")
    for short, status in l4_flags:
        out.append(f"- {short}: {status}")
    out.append("\"Pooled\" therefore means a different tier composition per model for "
               f"{len(l4_flags)}/{len(df)} models, not an apples-to-apples average, a real "
               "methodological gap in the pre-registered primary metric as computed.")
    out.append("")

    top_pooled = df.loc[df["dyn_pooled_mutk"].idxmax()]
    top_adj = df.loc[df["dyn_pooled_coverage_adj"].idxmax()]
    top_pooled_status = _l4_status(top_pooled["dyn_L4_n_total"], top_pooled["dyn_L4_n_defined"])
    top_adj_status = _l4_status(top_adj["dyn_L4_n_total"], top_adj["dyn_L4_n_defined"])
    same_model = top_pooled["model_label"] == top_adj["model_label"]
    out.append(
        f"**Top-ranked model check**: by pooled Mut@K, **{top_pooled['model_short']}** ranks "
        f"highest ({top_pooled['dyn_pooled_mutk']:.3f}). Its L4 status is {top_pooled_status}. "
        + (
            f"By coverage-adjusted score, the SAME model ({top_adj['model_short']}) also ranks "
            f"highest ({top_adj['dyn_pooled_coverage_adj']:.4f})."
            if same_model else
            f"By coverage-adjusted score, **{top_adj['model_short']}** ranks highest instead "
            f"({top_adj['dyn_pooled_coverage_adj']:.4f}). Its L4 status is {top_adj_status}."
        )
        + (
            " **The top-ranked model on both metrics never faced the hardest tier**. "
            "Its apparent lead may reflect having only been scored on easier problems, not "
            "genuine superiority over models that were tested on L4 and paid a real cost for it."
            if "MISSING" in top_pooled_status or "MISSING" in top_adj_status
            else " Neither top-ranked model has a MISSING L4 status, so this specific confound "
                 "does not apply to the top rank, though thin coverage elsewhere in the table "
                 "still affects the tier composition comparability noted above."
        )
    )
    out.append("")

    sub = df.dropna(subset=["dyn_pooled_coverage_adj", "ult_coverage_adj"])
    res_adj = None
    if len(sub) >= 3:
        res_adj = compute_correlations(sub["dyn_pooled_coverage_adj"].to_numpy(), sub["ult_coverage_adj"].to_numpy())
        out.append(f"**Rank correlation on coverage-adjusted score (n_models={res_adj.n})**: "
                   f"Pearson r={res_adj.pearson_r:.3f}, Spearman ρ={res_adj.spearman_rho:.3f}, "
                   f"Kendall τ={res_adj.kendall_tau:.3f} (perm p={res_adj.kendall_p_perm:.4f}).")
    out.append("")

    # --- 3b. Decomposing the coverage-adjusted agreement ---------------------
    _adj_tau_str = f"{res_adj.kendall_tau:.3f}" if res_adj is not None else "n/a"
    out += ["## 3b. Decomposing the coverage-adjusted agreement", "",
            "coverage_adjusted = Mut@K x baseline_pass_rate is a PRODUCT of two signals:",
            f"how much of its tau={_adj_tau_str} agreement is just baseline pass rate (can the",
            "model produce a suite that PASSES against the original function, a stricter and",
            "later gate than mere exec/collection. src/eval/test_gen_scorer.py's",
            "exec_ok and baseline_passed are different checks, not the same thing) vs",
            "actual mutation-killing quality? Same n, same models (dropna on the",
            "coverage-adjusted columns) for all three rows, so they're directly comparable.", ""]
    out += ["| Component | n | Pearson r | Spearman ρ | Kendall τ | perm p (τ) |",
            "|---|---|---|---|---|---|"]
    res_bp = res_mutk = None
    if len(sub) >= 3:
        res_bp = compute_correlations(sub["dyn_pooled_bp_rate"].to_numpy(), sub["ult_bp_rate"].to_numpy())
        res_mutk = compute_correlations(sub["dyn_pooled_mutk"].to_numpy(), sub["ult_mutk"].to_numpy())
        for row_label, res in [
            ("(a) baseline_pass_rate alone", res_bp),
            ("(b) conditioned Mut@K alone (= the pre-registered PRIMARY result)", res_mutk),
            ("(c) coverage-adjusted product (Mut@K x baseline_pass_rate)", res_adj),
        ]:
            out.append(f"| {row_label} | {res.n} | {res.pearson_r:.3f} | {res.spearman_rho:.3f} | "
                       f"{res.kendall_tau:.3f} | {res.kendall_p_perm:.4f} |")
    out.append("")
    if res_bp is not None and res_mutk is not None and res_adj is not None:
        out.append(
            f"**How much of τ={res_adj.kendall_tau:.3f} is baseline pass rate vs mutation "
            f"quality:** baseline_pass_rate ALONE already gives τ={res_bp.kendall_tau:.3f}. "
            f"{'Nearly all' if abs(res_bp.kendall_tau - res_adj.kendall_tau) < 0.1 else 'Most' if res_bp.kendall_tau > 0.5 else 'Some'} "
            f"of the coverage-adjusted agreement is explained by which models can produce a "
            f"baseline-passing suite (a suite that PASSES against the real function, "
            f"not merely one that executes/collects, a weaker, earlier gate this project's "
            f"scorer calls exec_ok), not by mutation-killing quality once that's controlled "
            f"for. Conditioned Mut@K alone (row b, the actual pre-registered primary result) "
            f"is τ={res_mutk.kendall_tau:.3f}, i.e. models that clear the baseline-pass bar do "
            f"NOT then agree on which suites are the BETTER mutation killers. Read literally: "
            f"the coverage-adjusted score's apparent validity is mostly a baseline-"
            f"pass-rate-agreement result, not evidence that Mut@K itself (conditional on "
            f"passing) is cross-benchmark valid."
        )
    out.append("")

    # --- 3c. Reliability of the coverage-adjusted score ----------------------
    out += ["## 3c. Reliability of the coverage-adjusted score", "",
            "If the coverage-adjusted score is not just more cross-benchmark-valid but",
            "also more RELIABLE (stabler across Dynamic instantiations) than raw Mut@K,",
            "that's a stronger case for using it going forward, not just a post-hoc",
            "rescue of one result. Recomputed on CANONICAL_MODELS-filtered Dynamic data,",
            "N=4 scope (instantiations 1-4), same as sec 4's raw-Mut@K reliability.", ""]
    pairwise_raw = pairwise_kendall_tau(dynamic)
    pairwise_adj = pairwise_kendall_tau(dynamic, coverage_adjust=True)
    tau_n4_raw = mean_pairwise_tau_scoped(pairwise_raw, N4_INSTANTIATIONS)
    tau_n4_adj = mean_pairwise_tau_scoped(pairwise_adj, N4_INSTANTIATIONS)
    # Per-pair n_models/p_value for the N4-scoped adjusted table, computed live
    # so the "not a degenerate small-n artifact" claim below cites the actual
    # current n, not a number frozen from an earlier, smaller data landing
    # (the bug class this section already warns about for RANKING_MATRIX.md's
    # reliability figure. A hard-coded n here would go stale the same way).
    _adj_n4_pairs = pairwise_adj[
        pairwise_adj["instantiation_a"].isin(N4_INSTANTIATIONS)
        & pairwise_adj["instantiation_b"].isin(N4_INSTANTIATIONS)
    ].dropna(subset=["tau"])
    _adj_n4_nmodels = sorted(_adj_n4_pairs["n_models"].unique().tolist())
    _adj_n4_nmodels_str = (
        str(_adj_n4_nmodels[0]) if len(_adj_n4_nmodels) == 1
        else f"{min(_adj_n4_nmodels)}-{max(_adj_n4_nmodels)}"
    )
    _adj_n4_max_p = float(_adj_n4_pairs["p_value"].max()) if len(_adj_n4_pairs) else None
    out += ["| Score | N=4 mean pairwise Kendall tau |",
            "|---|---|",
            f"| raw Mut@K | {tau_n4_raw:.3f} |" if tau_n4_raw is not None else "| raw Mut@K | n/a |",
            f"| coverage-adjusted (Mut@K x baseline_pass_rate) | {tau_n4_adj:.3f} |"
            if tau_n4_adj is not None else "| coverage-adjusted | n/a |"]
    out.append("")
    if tau_n4_raw is not None and tau_n4_adj is not None:
        if tau_n4_adj > tau_n4_raw + 0.02:
            n_inst_summary = ", ".join(
                f"{_model_shortname(r['model_label'])}={int(r['n_instantiations'])}"
                for _, r in stable_pooled.sort_values("model_label").iterrows()
            )
            out.append(f"**The coverage-adjusted score IS more reliable** across Dynamic "
                       f"instantiations ({tau_n4_adj:.3f} vs {tau_n4_raw:.3f} raw). This makes it "
                       f"both more valid (sec 3b) and more reliable, a real argument for reporting "
                       f"it as a companion metric, not just a post-hoc robustness check. A perfect "
                       f"or near-perfect adjusted figure is worth a sanity check before taking as an "
                       f"unqualified win, though: verified this is not a degenerate small-n artifact "
                       f"(n_models={_adj_n4_nmodels_str} per pair, every pair individually significant "
                       f"at p={_adj_n4_max_p:.2e}" + (" (largest/least-significant p across pairs)" if _adj_n4_max_p is not None else "")
                       + f", not just the mean). It is the SAME mechanism as sec 3b, not a separate "
                       f"finding. **Qualification: \"n={_adj_n4_nmodels_str}\" is models, not a uniform "
                       f"amount of repeat measurement per model**. Instantiation counts vary: "
                       f"{n_inst_summary}. A model with only 4 scorable instantiations (or with some "
                       f"instantiations partially landed, per analysis/STABILITY.md) contributes a "
                       f"noisier per-model SD to this figure than one with a full 5, so treat the exact "
                       f"tau value as somewhat more uncertain than a clean n={_adj_n4_nmodels_str} label "
                       f"implies. baseline_pass_rate apparently varies enormously and consistently BETWEEN "
                       f"models (a 45x spread, sec 3 above) while staying comparatively stable WITHIN "
                       f"a model across instantiations, so a score dominated by that spread ranks "
                       f"models the same way every time almost by construction. The same reason it's "
                       f"more cross-benchmark-valid (baseline pass rate dominates the signal) is why "
                       f"it's more reliable (baseline pass rate is itself the stable quantity). "
                       f"Neither result is suspect. Both are the same underlying fact read two ways.")
        elif tau_n4_raw > tau_n4_adj + 0.02:
            out.append(f"**The coverage-adjusted score is LESS reliable** across Dynamic "
                       f"instantiations ({tau_n4_adj:.3f} vs {tau_n4_raw:.3f} raw). Its apparent "
                       f"cross-benchmark validity gain (sec 3b) comes with a reliability cost. "
                       f"The disattenuated comparison below is the fairer way to weigh this.")
        else:
            out.append(f"Reliability is essentially unchanged ({tau_n4_adj:.3f} adjusted vs "
                       f"{tau_n4_raw:.3f} raw). The coverage-adjusted score's higher cross-benchmark "
                       f"agreement (sec 3b) is not explained by it also being a more stable measurement.")
    out.append("")

    # --- 4. Attenuation ---------------------------------------------------------
    out += ["## 4. Attenuation correction", "",
            "rho_disattenuated = rho_observed / sqrt(reliability_x * reliability_y), the",
            "classical correction for attenuation due to unreliable measurement (Spearman,",
            "1904), derived for Pearson r under classical test theory. Applying the same form",
            "to Kendall tau here is an APPROXIMATION carried over by analogy, not a rigorously",
            "derived rank-statistic correction. Treat the disattenuated tau as illustrative.",
            ""]
    pooled_pair = df.dropna(subset=["dyn_pooled_mutk", "ult_mutk"])
    res_pooled = compute_correlations(pooled_pair["dyn_pooled_mutk"].to_numpy(), pooled_pair["ult_mutk"].to_numpy())
    reliability_dynamic = tau_n4_raw  # computed in sec 3c, same N=4 scope
    if reliability_dynamic is None:
        raise RuntimeError("N=4 pairwise Kendall tau came back empty -- Dynamic data on disk "
                            "doesn't cover enough of instantiations 1-4 to compute a reliability "
                            "figure; investigate before trusting any disattenuated estimate.")
    disattenuated_partial = res_pooled.kendall_tau / (reliability_dynamic ** 0.5)
    out.append(f"- Dynamic's own reliability (RQ4.1, N=4 mean pairwise Kendall tau across "
               f"instantiations, computed live from CANONICAL_MODELS-filtered data on disk as "
               f"of this run, per the Generated/Git commit stamp above. This is NOT a frozen "
               f"constant and will move as more instantiation data lands, same as "
               f"`analysis/STABILITY.md` itself): **{reliability_dynamic:.3f}**.")
    out.append("- ULT has **no repeat-measure reliability estimate in this project**. It is "
               "evaluated once per model (K=1; the K=5 sensitivity sweep was the first item cut "
               "per PROJECT_BRIEF.md's gate cut-priority, and a static benchmark has no "
               "\"instantiation\" concept to repeat across the way Dynamic does). Stated "
               "plainly, not assumed: the correction below uses Dynamic's reliability "
               "only (equivalent to assuming ULT's reliability=1, which UNDERESTIMATES the "
               "true disattenuated correlation if ULT is not, in fact, perfectly reliable).")
    out.append(f"- Observed pooled Kendall τ = {res_pooled.kendall_tau:.3f} (n_models={res_pooled.n}).")
    out.append(f"- Partial disattenuation (ULT reliability assumed = 1): "
               f"τ_disattenuated = {res_pooled.kendall_tau:.3f} / sqrt({reliability_dynamic:.3f}) "
               f"= **{disattenuated_partial:.3f}**.")
    out.append(f"- Even with this correction, the disattenuated tau stays far from the "
               f"pre-registered validity-supporting zone. The low observed correlation is "
               f"NOT primarily an artifact of Dynamic's own (already-high, {reliability_dynamic:.3f}) "
               f"reliability.")
    out.append("")
    out.append("**Matched disattenuation on the coverage-adjusted score** (sec 3b/3c). "
               "The pairing above uses the RAW Mut@K correlation with the RAW Mut@K "
               "reliability. This is the same correction applied to the ADJUSTED "
               "correlation with the ADJUSTED score's OWN reliability, since mixing a "
               "raw correlation with an adjusted reliability (or vice versa) would not be "
               "a matched pair:")
    if res_adj is not None and tau_n4_adj is not None:
        disattenuated_adj = res_adj.kendall_tau / (tau_n4_adj ** 0.5)
        out.append(f"- Coverage-adjusted reliability (N=4, sec 3c): **{tau_n4_adj:.3f}**.")
        out.append(f"- Observed coverage-adjusted Kendall τ = {res_adj.kendall_tau:.3f} (n_models={res_adj.n}).")
        out.append(f"- Matched disattenuation: τ_disattenuated = {res_adj.kendall_tau:.3f} / "
                   f"sqrt({tau_n4_adj:.3f}) = **{disattenuated_adj:.3f}**.")
        out.append(f"- Compare to the raw-matched {disattenuated_partial:.3f} above. The "
                   f"coverage-adjusted score's disattenuated agreement is "
                   f"{'still much higher' if disattenuated_adj > disattenuated_partial + 0.1 else 'similar'}, "
                   f"consistent with sec 3b's finding that most of its apparent validity is a "
                   f"baseline-pass-rate-agreement effect, not a reliability artifact of "
                   f"either metric.")
    else:
        out.append("- Could not compute (insufficient data for the adjusted correlation or reliability).")
    out.append("")

    # --- Thin-cell-filtered primary correlation (item 3) ---------------------
    pooled_thin_mask = (pooled_pair["dyn_pooled_n_defined"] < THIN_N_DEFINED) | (pooled_pair["ult_n_defined"] < THIN_N_DEFINED)
    pooled_excluded = sorted(pooled_pair.loc[pooled_thin_mask, "model_short"].tolist())
    pooled_thick = pooled_pair.loc[~pooled_thin_mask]
    out.append("**Thin-cell-filtered primary correlation** (n_defined<{0} on either side, same "
               "threshold as secs 1/3b and Comparison A's audit):".format(THIN_N_DEFINED))
    if len(pooled_thick) >= 3:
        res_pooled_thick = compute_correlations(
            pooled_thick["dyn_pooled_mutk"].to_numpy(), pooled_thick["ult_mutk"].to_numpy())
        out.append(f"- Unfiltered: τ={res_pooled.kendall_tau:.3f} (n_models={res_pooled.n}). "
                   f"Thin-cell-excluded: τ={res_pooled_thick.kendall_tau:.3f} "
                   f"(n_models={res_pooled_thick.n}, excluded: {pooled_excluded or 'none'}).")
        out.append(f"- **Mistral is unquotable on this pair once cross-family models are in "
                   f"scope** (ULT n_defined=1, analysis/RQ5_CROSS_FAMILY_PROVENANCE.md), not "
                   f"applicable to this canonical-only n={res_pooled.n} table (Mistral isn't one "
                   f"of the {len(CANONICAL_MODELS)} canonical models). This is flagged here so the "
                   f"rule is visible in one place. The cross-family provenance doc has its own "
                   f"thin-cell flags for that.")
    else:
        out.append(f"- Excluding thin cells leaves n_models={len(pooled_thick)} (<3), cannot compute "
                   f"a correlation. Excluded: {pooled_excluded or 'none'}.")
    out.append("")

    doc = "\n".join(out)
    (ROOT / "analysis" / "RQ5_DIAGNOSTICS.md").write_text(doc)
    print(doc)
    print("\nWritten: analysis/RQ5_DIAGNOSTICS.md")


if __name__ == "__main__":
    main()
