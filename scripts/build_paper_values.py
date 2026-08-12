"""Generate paper/values.tex: every quantitative value the paper's prose
cites, as a LaTeX \\newcommand macro, read live from analysis/*.csv at
generation time.

This is the mechanism that makes "no hand-typed numbers in the paper"
enforceable: paper/sections/*.tex reference a number as \\NumFoo, never as
a literal digit, so a re-run after new data lands changes the number
everywhere it's used with no manual find-replace, and
scripts/check_doc_citations.py can verify paper/values.tex the same way
it verifies every hand-written analysis/*.md doc.

Macro naming: \\Num<Hypothesis><Quantity>, e.g. \\NumHOneTOneEffectR.
Digits in hypothesis names are spelled out (One, Two) because LaTeX
macro names cannot contain digits.

Usage:
    python scripts/build_paper_values.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from scipy.stats import kendalltau

ANALYSIS = ROOT / "analysis"
OUT_PATH = ROOT / "paper" / "values.tex"

macros: dict[str, str] = {}


def num(name: str, value: float, spec: str = ".3f") -> None:
    """Register a numeric macro, formatted per `spec` (Python format-spec mini-language)."""
    macros[name] = format(value, spec)


def raw(name: str, value: str) -> None:
    """Register a pre-formatted string macro (percentages, ranges, counts)."""
    macros[name] = value


def pp(name: str, value: float) -> None:
    """Register a percentage-points macro (0-1 fraction -> 'XX.Xpp')."""
    macros[name] = f"{value * 100:.1f}"


def main() -> None:
    # ---------------------------------------------------------------- H1 Test 1
    a_w = pd.read_csv(ANALYSIS / "comparison_a_wilcoxon.csv").iloc[0]
    a_w_adj = pd.read_csv(ANALYSIS / "comparison_a_coverage_adjusted_wilcoxon.csv").iloc[0]
    a_w_thick = pd.read_csv(ANALYSIS / "comparison_a_wilcoxon_thick.csv").iloc[0]
    num("HOneTOneN", a_w["n_pairs"], "g")
    num("HOneTOneEffectR", a_w["effect_r"], ".3f")
    num("HOneTOneP", a_w["p_value"], ".4f")
    num("HOneTOneMeanDyn", a_w["mean_a"], ".4f")
    num("HOneTOneMeanUlt", a_w["mean_b"], ".4f")
    num("HOneTOneAdjEffectR", a_w_adj["effect_r"], ".3f")
    num("HOneTOneAdjP", a_w_adj["p_value"], ".4f")
    num("HOneTOneThinEffectR", a_w_thick["effect_r"], ".3f")
    num("HOneTOneThinP", a_w_thick["p_value"], ".4f")
    num("HOneTOneThinN", a_w_thick["n_pairs"], "g")

    # ---------------------------------------------------------------- H1 Test 2
    b_w = pd.read_csv(ANALYSIS / "comparison_b_wilcoxon.csv").iloc[0]
    b_w_adj = pd.read_csv(ANALYSIS / "comparison_b_coverage_adjusted_wilcoxon.csv").iloc[0]
    b_w_thick = pd.read_csv(ANALYSIS / "comparison_b_wilcoxon_thick.csv").iloc[0]
    num("HOneTTwoN", b_w["n_pairs"], "g")
    num("HOneTTwoEffectR", b_w["effect_r"], ".3f")
    num("HOneTTwoP", b_w["p_value"], ".4f")
    num("HOneTTwoAdjEffectR", b_w_adj["effect_r"], ".3f")
    num("HOneTTwoAdjP", b_w_adj["p_value"], ".4f")
    num("HOneTTwoThinP", b_w_thick["p_value"], ".4f")

    holm = pd.read_csv(ANALYSIS / "comparison_rq1_holm.csv")
    def holm_p(conditioning: str, test: str) -> float:
        row = holm[(holm["conditioning"] == conditioning) & (holm["test"] == test)]
        return float(row.iloc[0]["p_value_holm"])
    num("HOneTOneRawHolmP", holm_p("raw", "H1 Test 1"), ".4f")
    num("HOneTTwoRawHolmP", holm_p("raw", "H1 Test 2"), ".4f")
    num("HOneTOneAdjHolmP", holm_p("definition_matched", "H1 Test 1"), ".4f")
    num("HOneTTwoAdjHolmP", holm_p("definition_matched", "H1 Test 2"), ".4f")

    # -------------------------------------------------------------------- H2
    gradient = pd.read_csv(ANALYSIS / "comparison_c_gradient.csv")
    did = pd.read_csv(ANALYSIS / "comparison_c_did.csv")
    mutk = pd.read_csv(ANALYSIS / "comparison_c_mutk.csv")

    def gain_row(benchmark: str) -> pd.Series:
        return gradient[gradient["benchmark"] == benchmark].iloc[0]
    seen = gain_row("seen_ult")
    unseen = gain_row("unseen_ult")
    plt_row = gain_row("plt")
    dyn_l4 = gain_row("dynamic_l4")
    dyn_l1l3 = gain_row("dynamic_l1l3")
    pp("HTwoSeenGain", seen["gain"])
    raw("HTwoSeenGainCI", f"[{seen['gain_ci_lo']*100:.1f}, {seen['gain_ci_hi']*100:.1f}]")
    pp("HTwoLOneLThreeGain", dyn_l1l3["gain"])
    raw("HTwoLOneLThreeGainCI", f"[{dyn_l1l3['gain_ci_lo']*100:.1f}, {dyn_l1l3['gain_ci_hi']*100:.1f}]")
    pp("HTwoLFourGain", dyn_l4["gain"])
    pp("HTwoPltGain", plt_row["gain"])
    pp("HTwoUnseenGain", unseen["gain"])
    raw("HTwoSeenN", f"{int(seen['n_pre'])}")

    def did_row(control: str, benchmark: str) -> pd.Series:
        return did[(did["control"] == control) & (did["benchmark"] == benchmark)].iloc[0]
    plt_did = did_row("dynamic_l1l3", "plt")
    pp("HTwoPltDid", plt_did["did"])
    raw("HTwoPltDidCI", f"[{plt_did['did_ci_lo']*100:.1f}, {plt_did['did_ci_hi']*100:.1f}]")

    seen_pre_mutk = mutk[(mutk["benchmark"] == "seen_ult") & (mutk["side"] == "pre")].iloc[0]
    seen_post_mutk = mutk[(mutk["benchmark"] == "seen_ult") & (mutk["side"] == "post")].iloc[0]
    n_undefined = int(seen_pre_mutk["n_total"]) - int(seen_pre_mutk["n_mut_defined"])
    raw("HTwoPreMutkUndefined", f"{n_undefined}")
    raw("HTwoPreMutkTotal", f"{int(seen_pre_mutk['n_total'])}")
    num("HTwoPostMutk", seen_post_mutk["mut_at_k"], ".3f")

    # ---------------------------------------------- Equivalent-mutant validation
    # analysis/equiv_mutants/inspection_sheet.xlsx is currently fully unfilled
    # (0/120 verdicts across all four tiers); scripts/compute_validated_score.py
    # correctly writes nothing until at least one tier has filled rows. This
    # block picks up its output automatically, per tier, once that happens --
    # no further code changes needed -- and stays a no-op until then, matching
    # the paper's own "not yet complete" disclosure (04_results.tex, Additional
    # Disclosures).
    validated_path = ANALYSIS / "equiv_mutants" / "validated_scores.csv"
    if validated_path.exists():
        tier_name = {"L1": "LOne", "L2": "LTwo", "L3": "LThree", "L4": "LFour"}
        for _, row in pd.read_csv(validated_path).iterrows():
            name = tier_name[row["tier"]]
            num(f"HTwoValidated{name}MutK", row["mut_at_k_validated"], ".3f")
            if pd.notna(row["mut_at_k_validated_boot_lo"]):
                raw(f"HTwoValidated{name}MutKCI",
                    f"[{row['mut_at_k_validated_boot_lo']:.3f}, {row['mut_at_k_validated_boot_hi']:.3f}]")
            num(f"HTwoValidated{name}EquivRate", row["equivalent_rate"], ".3f")

    # -------------------------------------------------------------------- H3
    all_tier = pd.read_csv(ANALYSIS / "h3_tier_gradient_all_tier.csv")
    l2l4 = pd.read_csv(ANALYSIS / "h3_tier_gradient_l2l4.csv")
    raw("HThreeAllTierSig", f"{(all_tier['p_perm_holm'] < 0.05).sum()}/{len(all_tier)}")
    computable = l2l4[l2l4["status"] == "ok"]
    raw("HThreeLTwoLFourSig", f"{(computable['p_perm_holm'] < 0.05).sum()}/{len(computable)}")

    # -------------------------------------------------------------------- H5
    # Pre-registered threshold (docs/Approved_Hypotheses.md:16: "the
    # Kendall's tau ... will exceed 0.7"), not derived from a CSV -- a
    # fixed design constant, hardcoded here rather than left as a bare
    # literal in paper prose so the two stay single-sourced.
    num("HFiveTauThreshold", 0.7, ".1f")
    stable = pd.read_csv(ANALYSIS / "stability_stablemut.csv")
    kendall = pd.read_csv(ANALYSIS / "stability_kendall.csv")
    n4_pairs = {(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)}
    n4 = kendall[kendall.apply(lambda r: (r["instantiation_a"], r["instantiation_b"]) in n4_pairs, axis=1)]
    all_pairs = kendall
    num("HFiveNFourTau", n4["tau"].mean(), ".3f")
    num("HFiveAllPairsTau", all_pairs["tau"].mean(), ".3f")
    raw("HFiveNFourSigCount", f"{(n4['p_value'] < 0.05).sum()}/{len(n4)}")
    raw("HFiveNFourHolmCount", f"{(n4['p_value_holm'] < 0.05).sum()}/{len(n4)}")
    # score-level SD range, excluding the two known outliers (Qwen 1.5B high,
    # Gemini Pro Preview low) -- "most models" reading, matching this
    # project's own established convention (analysis/STABILITY_INTERPRETATION.md)
    sd_middle = stable[~stable["model_label"].isin(
        ["Qwen__Qwen2.5-Coder-1.5B-Instruct", "gemini-3.1-pro-preview"])]["sd_mut_at_k"]
    raw("HFiveSdRange", f"{sd_middle.min():.3f}--{sd_middle.max():.3f}")

    # -------------------------------------------------------------------- H6
    # Pre-registered validity-supporting band (analysis/RQ5_ANALYSIS_PLAN.md:91:
    # "Moderate-to-strong (roughly Spearman rho in the 0.4-0.8 range ...)").
    # Fixed design constants, not derived from a CSV -- see HFiveTauThreshold above.
    num("HSixBandLow", 0.4, ".1f")
    num("HSixBandHigh", 0.8, ".1f")
    rq5_corr = pd.read_csv(ANALYSIS / "rq5_correlations.csv")
    rq5_cf_corr = pd.read_csv(ANALYSIS / "rq5_cross_family_correlations.csv")
    diag_decomp_row = None  # decomposition figures come from a fresh recompute below

    dyn_ult_pooled = rq5_corr[rq5_corr["pair"] == "Dynamic(pooled) <-> ULT"].iloc[0]
    num("HSixCondTau", dyn_ult_pooled["kendall_tau"], ".3f")

    def cf_row(pair: str, scope: str) -> pd.Series:
        return rq5_cf_corr[(rq5_cf_corr["pair"] == pair) & (rq5_cf_corr["scope"] == scope)].iloc[0]

    dyn_ult_adj_cf = cf_row("Dynamic(pooled) <-> ULT [coverage-adjusted]", "canonical-only")
    num("HSixAdjTau", dyn_ult_adj_cf["kendall_tau"], ".3f")

    dyn_bcb_raw_cf = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical+cross-family")
    dyn_bcb_adj_cf = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical+cross-family")
    ult_bcb_raw_cf = cf_row("ULT <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical+cross-family")
    ult_bcb_adj_cf = cf_row("ULT <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical+cross-family")
    num("HSixDynBcbRawTau", dyn_bcb_raw_cf["kendall_tau"], ".3f")
    num("HSixDynBcbAdjTau", dyn_bcb_adj_cf["kendall_tau"], ".3f")
    num("HSixUltBcbRawTau", ult_bcb_raw_cf["kendall_tau"], ".3f")
    num("HSixUltBcbAdjTau", ult_bcb_adj_cf["kendall_tau"], ".3f")
    num("HSixDynBcbAdjHolmP", dyn_bcb_adj_cf["kendall_p_perm_holm"], ".4f")

    dyn_bcb_raw_canon = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical-only")
    dyn_bcb_adj_canon = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical-only")
    num("HSixCanonRawTau", dyn_bcb_raw_canon["kendall_tau"], ".3f")
    num("HSixCanonAdjTau", dyn_bcb_adj_canon["kendall_tau"], ".3f")

    # RQ5 diagnostics decomposition (baseline_pass_rate alone / coverage-adjusted):
    # no standalone CSV for this table (it's embedded in RQ5_DIAGNOSTICS.md's
    # generated prose) -- recompute directly from the same source
    # analyze_rq5_diagnostics.py itself reads (rq5_model_ranking.csv's
    # baseline_pass_rate columns for the 9 canonical models), so this script
    # has no dependency on parsing markdown.
    ranking = pd.read_csv(ANALYSIS / "rq5_model_ranking.csv")
    from coverage_matrix import CANONICAL_MODELS  # noqa: E402
    ranking = ranking[ranking["model_label"].isin(CANONICAL_MODELS)]
    bp_tau, _ = kendalltau(ranking["dynamic_bp_pooled"], ranking["ult_bp"])
    num("HSixBpTau", bp_tau, ".3f")

    # -------------------------------------------------------------------- Sanitizer sensitivity
    sanitizer = pd.read_csv(ANALYSIS / "rq5_sanitizer_sensitivity.csv")
    sanitizer = sanitizer[sanitizer["model_label"].isin(CANONICAL_MODELS)]
    tau_with, _ = kendalltau(sanitizer["dyn_coverage_adj"], sanitizer["ult_coverage_adj"])
    tau_without, _ = kendalltau(sanitizer["dyn_coverage_adj_norepair"], sanitizer["ult_coverage_adj_norepair"])
    num("HSixSanitizerWithTau", tau_with, ".3f")
    num("HSixSanitizerWithoutTau", tau_without, ".3f")

    # -------------------------------------------------------------------- Thin-cell / cross-family n
    cf_ranking = pd.read_csv(ANALYSIS / "rq5_cross_family_model_ranking.csv")
    codellama = cf_ranking[cf_ranking["model_short"] == "CodeLlama-13B"].iloc[0]
    mistral = cf_ranking[cf_ranking["model_short"] == "Mistral-7B"].iloc[0]
    raw("HSixCodeLlamaUltNDefined", f"{int(codellama['ult_n_defined'])}")
    raw("HSixMistralDynNDefined", f"{int(mistral['dynamic_n_defined'])}")
    raw("HSixMistralUltNDefined", f"{int(mistral['ult_n_defined'])}")

    OUT_PATH.write_text(
        "% Auto-generated by scripts/build_paper_values.py -- DO NOT EDIT DIRECTLY.\n"
        "% Every number the paper's prose cites is a \\NumXXX macro defined here,\n"
        "% read live from analysis/*.csv at generation time. Re-run after any\n"
        "% underlying data changes; never hand-type a result value in sections/*.tex.\n\n"
        + "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(macros.items()))
        + "\n"
    )
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(macros)} macros)")


if __name__ == "__main__":
    main()
