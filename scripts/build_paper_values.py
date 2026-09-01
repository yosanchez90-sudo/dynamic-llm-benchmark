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
import yaml
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


_SMALL_INT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                    6: "six", 7: "seven", 8: "eight", 9: "nine"}


def word_count(name: str, value: int) -> None:
    """Register a small-integer macro spelled out as a word (e.g. "eight"),
    for a model/sample count quoted in the same sentence as another count
    this paper always spells out (e.g. "the nine canonical models"). Mixing
    a numeral with a spelled-out number in one phrase reads as inconsistent
    (build_paper_values.py's own style-consistency pass, 2026-08-27); the
    value itself stays live, only its rendering as a word is fixed."""
    if value not in _SMALL_INT_WORDS:
        raise ValueError(f"{name}={value} has no word form registered (only 1-9)")
    macros[name] = _SMALL_INT_WORDS[value]


def pp(name: str, value: float) -> None:
    """Register a percentage-points macro (0-1 fraction -> 'XX.Xpp')."""
    macros[name] = f"{value * 100:.1f}"


def main() -> None:
    # ---------------------------------------------------------------- H1 Test 1
    a_w = pd.read_csv(ANALYSIS / "comparison_a_wilcoxon.csv").iloc[0]
    a_w_adj = pd.read_csv(ANALYSIS / "comparison_a_coverage_adjusted_wilcoxon.csv").iloc[0]
    a_w_thick = pd.read_csv(ANALYSIS / "comparison_a_wilcoxon_thick.csv").iloc[0]
    word_count("HOneTOneN", int(a_w["n_pairs"]))
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
    pp("HTwoUnseenNetOfControl", unseen["gain"] - dyn_l1l3["gain"])
    raw("HTwoSeenN", f"{int(seen['n_pre'])}")

    # Endpoint table (population, n, pre, post, gain, CI), five
    # populations, one row per benchmark in comparison_c_gradient.csv.
    # Kind-suffix at the very end of each name (N/Pre/Post), matching this
    # file's own \Num<Hyp><Quantity> convention, so check_doc_citations.py's
    # suffix matching (which reads right-to-left) tags each correctly.
    for label, row in (
        ("Seen", seen), ("Unseen", unseen), ("Plt", plt_row),
        ("LFour", dyn_l4), ("LOneLThree", dyn_l1l3),
    ):
        raw(f"HTwoEndpoint{label}N", f"{int(row['n_pre'])}")
        pp(f"HTwoEndpoint{label}Pre", row["pre_mean"])
        pp(f"HTwoEndpoint{label}Post", row["post_mean"])

    def did_row(control: str, benchmark: str) -> pd.Series:
        return did[(did["control"] == control) & (did["benchmark"] == benchmark)].iloc[0]
    plt_did = did_row("dynamic_l1l3", "plt")
    pp("HTwoPltDid", plt_did["did"])
    raw("HTwoPltDidCI", f"[{plt_did['did_ci_lo']*100:.1f}, {plt_did['did_ci_hi']*100:.1f}]")
    seen_did = did_row("dynamic_l1l3", "seen_ult")
    pp("HTwoSeenDid", seen_did["did"])

    seen_pre_mutk = mutk[(mutk["benchmark"] == "seen_ult") & (mutk["side"] == "pre")].iloc[0]
    seen_post_mutk = mutk[(mutk["benchmark"] == "seen_ult") & (mutk["side"] == "post")].iloc[0]
    n_undefined = int(seen_pre_mutk["n_total"]) - int(seen_pre_mutk["n_mut_defined"])
    raw("HTwoPreMutkUndefined", f"{n_undefined}")
    raw("HTwoPreMutkTotal", f"{int(seen_pre_mutk['n_total'])}")
    # Percentage form (pp(), not a raw 0-1 fraction): every other Mut@K/
    # baseline-pass value quoted in Section 4/5's prose and tables is a
    # percentage (P2-3, paper review action file, 2026-08-30 -- Section 5
    # previously quoted this pair as a bare 0.438/1.0 fraction while every
    # other figure/table in the paper reports %, a unit inconsistency).
    pp("HTwoPostMutk", seen_post_mutk["mut_at_k"])
    # Mutation score's own theoretical ceiling (every mutant killed), not a
    # value derived from any CSV, contrasted against HTwoPostMutk in the
    # discussion's "byte-identical recall does not imply Mut@K=100%" point.
    # Given its own macro rather than a bare literal for the same reason as
    # SigLevel above: it sits mid-paragraph, where a same-line `% cite:`
    # comment would swallow the rest of that physical line.
    pp("MutkCeiling", 1.0)

    # Coverage-adjusted gain + DiD: reported alongside baseline_pass_rate,
    # not as a replacement for it, because coverage_adjusted is defined
    # pre-treatment (unlike raw Mut@K, undefined for all but one seen-ULT
    # PRE row) -- it gives H2's headline result a second, independently
    # defined metric to confirm it.
    cov_adj_gradient = pd.read_csv(ANALYSIS / "comparison_c_coverage_adjusted_gradient.csv")
    cov_adj_did = pd.read_csv(ANALYSIS / "comparison_c_coverage_adjusted_did.csv")

    def cov_adj_gain_row(benchmark: str) -> pd.Series:
        return cov_adj_gradient[cov_adj_gradient["benchmark"] == benchmark].iloc[0]

    def cov_adj_did_row(benchmark: str) -> pd.Series:
        return cov_adj_did[cov_adj_did["benchmark"] == benchmark].iloc[0]

    seen_cov = cov_adj_gain_row("seen_ult")
    pp("HTwoCovAdjSeenGain", seen_cov["gain"])
    seen_cov_did = cov_adj_did_row("seen_ult")
    pp("HTwoCovAdjSeenDid", seen_cov_did["did"])
    raw("HTwoCovAdjSeenDidCI", f"[{seen_cov_did['did_ci_lo']*100:.1f}, {seen_cov_did['did_ci_hi']*100:.1f}]")
    unseen_cov_did = cov_adj_did_row("unseen_ult")
    pp("HTwoCovAdjUnseenDid", unseen_cov_did["did"])
    raw("HTwoCovAdjUnseenDidCI", f"[{unseen_cov_did['did_ci_lo']*100:.1f}, {unseen_cov_did['did_ci_hi']*100:.1f}]")
    plt_cov_did = cov_adj_did_row("plt")
    pp("HTwoCovAdjPltDid", plt_cov_did["did"])
    raw("HTwoCovAdjPltDidCI", f"[{plt_cov_did['did_ci_lo']*100:.1f}, {plt_cov_did['did_ci_hi']*100:.1f}]")

    # ---------------------------------------------- Equivalent-mutant validation
    # analysis/equiv_mutants/inspection_sheet.xlsx is currently fully unfilled
    # (0/120 verdicts across all four tiers); scripts/compute_validated_score.py
    # correctly writes nothing until at least one tier has filled rows. This
    # block picks up its output automatically, per tier, once that happens,
    # no further code changes needed, and stays a no-op until then, matching
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

    # ---------------------------------------------------- H2-supplementary
    # Post-hoc, not one of the six pre-registered hypotheses, see
    # analysis/HYPOTHESIS_COVERAGE_AUDIT.md's H2-supplementary section.
    # Metric: baseline_pass_rate (seen vs fresh instantiation), greedy
    # primary with R=3 sampling mean+-SD as a robustness note, same
    # convention as build_finetune_endpoint_table.py itself.
    endpoint = pd.read_csv(ANALYSIS / "finetune_endpoint_table.csv")

    def endpoint_cell(model: str, condition: str, split: str) -> pd.Series:
        return endpoint[
            (endpoint["model"] == model) & (endpoint["condition"] == condition)
            & (endpoint["split"] == split)
        ].iloc[0]

    supp_model_tag = {"Qwen 1.5B": "OneFiveB", "Qwen 7B": "SevenB"}
    supp_cond_tag = {"inst1": "Control", "bp_own": "Self", "bp_gpt5": "Cross"}
    for model, mtag in supp_model_tag.items():
        for cond, ctag in supp_cond_tag.items():
            seen = endpoint_cell(model, cond, "seen (inst1)")
            fresh = endpoint_cell(model, cond, "unseen (mean inst2/3)")
            num(f"HSupp{mtag}{ctag}Seen", seen["baseline_pass_greedy_pct"], ".1f")
            num(f"HSupp{mtag}{ctag}Fresh", fresh["baseline_pass_greedy_pct"], ".1f")
            num(f"HSupp{mtag}{ctag}Gap", seen["baseline_pass_gap_pp_greedy"], ".1f")

    # Held-out exec_rate decline (cross-model conditions only show a real
    # one; self-contamination and control do not, see
    # analysis/finetune_decline_table_PROVENANCE.md).
    decline = pd.read_csv(ANALYSIS / "finetune_decline_table.csv")

    def decline_cell(model: str, condition: str) -> pd.Series:
        return decline[(decline["model"] == model) & (decline["condition"] == condition)].iloc[0]

    for model, mtag in supp_model_tag.items():
        row = decline_cell(model, "bp_gpt5")
        num(f"HSupp{mtag}DeclineEpochZero", row["exec_rate_unseen_epoch0_greedy_pct"], ".1f")
        num(f"HSupp{mtag}DeclineEpochThirty", row["exec_rate_unseen_epoch30_greedy_pct"], ".1f")

    # -------------------------------------------------------------------- H3
    all_tier = pd.read_csv(ANALYSIS / "h3_tier_gradient_all_tier.csv")
    l2l4 = pd.read_csv(ANALYSIS / "h3_tier_gradient_l2l4.csv")
    raw("HThreeAllTierSig", f"{(all_tier['p_perm_holm'] < 0.05).sum()}/{len(all_tier)}")
    computable = l2l4[l2l4["status"] == "ok"]
    raw("HThreeLTwoLFourSig", f"{(computable['p_perm_holm'] < 0.05).sum()}/{len(computable)}")

    # -------------------------------------------------------------------- H5
    # Pre-registered threshold (docs/Approved_Hypotheses.md:16: "the
    # Kendall's tau ... will exceed 0.7"), not derived from a CSV, a
    # fixed design constant, hardcoded here, not left as a bare
    # literal in paper prose so the two stay single-sourced.
    num("HFiveTauThreshold", 0.7, ".1f")
    # Standard statistical significance convention (p<0.05), not project-
    # specific, given its own macro, not an inline `% cite:`
    # marker because it sits mid-paragraph, where a same-line LaTeX
    # comment would swallow the rest of that physical line.
    num("SigLevel", 0.05, ".2f")
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
    # Gemini Pro Preview low), "most models" reading, matching this
    # project's own established convention (analysis/STABILITY_INTERPRETATION.md)
    sd_middle = stable[~stable["model_label"].isin(
        ["Qwen__Qwen2.5-Coder-1.5B-Instruct", "gemini-3.1-pro-preview"])]["sd_mut_at_k"]
    raw("HFiveSdRange", f"{sd_middle.min():.3f}--{sd_middle.max():.3f}")

    # -------------------------------------------------------------------- H6
    # Pre-registered validity-supporting band (analysis/RQ5_ANALYSIS_PLAN.md:91:
    # "Moderate-to-strong (roughly Spearman rho in the 0.4-0.8 range ...)").
    # Fixed design constants, not derived from a CSV, see HFiveTauThreshold above.
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
    num("HSixAdjHolmP", dyn_ult_adj_cf["kendall_p_perm_holm"], ".4f")

    dyn_bcb_raw_cf = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical+cross-family")
    dyn_bcb_adj_cf = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical+cross-family")
    ult_bcb_raw_cf = cf_row("ULT <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical+cross-family")
    ult_bcb_adj_cf = cf_row("ULT <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical+cross-family")
    num("HSixDynBcbRawTau", dyn_bcb_raw_cf["kendall_tau"], ".3f")
    num("HSixDynBcbAdjTau", dyn_bcb_adj_cf["kendall_tau"], ".3f")
    num("HSixUltBcbRawTau", ult_bcb_raw_cf["kendall_tau"], ".3f")
    num("HSixUltBcbAdjTau", ult_bcb_adj_cf["kendall_tau"], ".3f")
    num("HSixDynBcbRawP", dyn_bcb_raw_cf["kendall_p_perm"], ".4f")
    num("HSixDynBcbAdjRawP", dyn_bcb_adj_cf["kendall_p_perm"], ".4f")
    num("HSixDynBcbAdjHolmP", dyn_bcb_adj_cf["kendall_p_perm_holm"], ".4f")

    dyn_bcb_raw_canon = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical-only")
    dyn_bcb_adj_canon = cf_row("Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical-only")
    num("HSixCanonRawTau", dyn_bcb_raw_canon["kendall_tau"], ".3f")
    num("HSixCanonAdjTau", dyn_bcb_adj_canon["kendall_tau"], ".3f")

    # RQ5 diagnostics decomposition (baseline_pass_rate alone / coverage-adjusted):
    # no standalone CSV for this table (it's embedded in RQ5_DIAGNOSTICS.md's
    # generated prose). Recompute directly from the same source
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
    # P1-8 (paper review action file, 2026-08-30): the paper's own prose
    # previously named only 2 of the 7 cross-family points as ULT-side
    # thin cells (CodeLlama, Mistral). Checking cf_ranking's own ult_thin
    # column directly against the full 7-model BigCodeBench-scored subset
    # shows 4 are thin, not 2 -- Qwen 7B and Qwen 1.5B were never
    # mentioned. Corrected here, not silently: both extra macros below are
    # new, the two above are unchanged.
    qwen7b_cf = cf_ranking[cf_ranking["model_short"] == "Qwen 7B"].iloc[0]
    qwen1_5b_cf = cf_ranking[cf_ranking["model_short"] == "Qwen 1.5B"].iloc[0]
    raw("HSixQwenSevenBUltNDefined", f"{int(qwen7b_cf['ult_n_defined'])}")
    raw("HSixQwenOneFiveBUltNDefined", f"{int(qwen1_5b_cf['ult_n_defined'])}")

    # Robustness check (P1-8): the two headline cross-family BigCodeBench
    # correlations (HSixDynBcb*/HSixUltBcb* above), recomputed excluding
    # each pair's own thin cells (n_defined<20 on the relevant side, same
    # threshold and ult_thin/dynamic_thin flags analyze_rq5_cross_family.py
    # already computes), alongside the full-sample values reported above.
    # A re-derivation from already-collected cf_ranking data, not new compute.
    cf_bcb = cf_ranking.dropna(subset=["public_score"])
    dyn_no_thin = cf_bcb[~cf_bcb["dynamic_thin"]]
    ult_no_thin = cf_bcb[~cf_bcb["ult_thin"]]
    raw("HSixDynBcbNoThinN", f"{len(dyn_no_thin)}")
    raw("HSixUltBcbNoThinN", f"{len(ult_no_thin)}")
    dyn_raw_nothin_tau, dyn_raw_nothin_p = kendalltau(dyn_no_thin["dynamic_mutk_pooled"], dyn_no_thin["public_score"])
    dyn_adj_nothin_tau, dyn_adj_nothin_p = kendalltau(dyn_no_thin["dynamic_coverage_adj"], dyn_no_thin["public_score"])
    ult_raw_nothin_tau, ult_raw_nothin_p = kendalltau(ult_no_thin["ult_mutk"], ult_no_thin["public_score"])
    ult_adj_nothin_tau, ult_adj_nothin_p = kendalltau(ult_no_thin["ult_coverage_adj"], ult_no_thin["public_score"])
    num("HSixDynBcbRawNoThinTau", dyn_raw_nothin_tau, ".3f")
    num("HSixDynBcbAdjNoThinTau", dyn_adj_nothin_tau, ".3f")
    num("HSixUltBcbRawNoThinTau", ult_raw_nothin_tau, ".3f")
    num("HSixUltBcbAdjNoThinTau", ult_adj_nothin_tau, ".3f")

    # -------------------------------------------------------------------- Project-wide constants
    test_count = pd.read_csv(ANALYSIS / "test_suite_count.csv").iloc[0]
    raw("TestSuiteCollected", f"{int(test_count['collected'])}")

    # ------------------------------------------------- H2 LoRA hyperparameters
    # Read live from the actual training config, not hand-typed, so a future
    # change to the config (e.g. a re-tuned learning rate) can't silently
    # diverge from what the paper reports.
    ft_cfg = yaml.safe_load((ROOT / "configs" / "finetune_qwen1_5b_ult_30ep.yaml").read_text())
    raw("FtLoraR", f"{ft_cfg['lora']['r']}")
    raw("FtLoraAlpha", f"{ft_cfg['lora']['alpha']}")
    num("FtLoraDropout", ft_cfg['lora']['dropout'], "g")
    raw("FtLoraTargetModuleCount", f"{len(ft_cfg['lora']['target_modules'])}")
    lr = ft_cfg['training']['learning_rate']
    lr_mantissa, lr_exp = f"{lr:.0e}".split("e")
    raw("FtLearningRate", f"{int(lr_mantissa)}\\times10^{{{int(lr_exp)}}}")
    num("FtWarmupRatio", ft_cfg['training']['warmup_ratio'], "g")
    raw("FtEpochs", f"{ft_cfg['training']['num_train_epochs']}")
    raw("FtPerDeviceBatch", f"{ft_cfg['training']['per_device_train_batch_size']}")
    raw("FtGradAccum", f"{ft_cfg['training']['gradient_accumulation_steps']}")
    raw("FtEffectiveBatch", f"{ft_cfg['training']['per_device_train_batch_size'] * ft_cfg['training']['gradient_accumulation_steps']}")
    raw("FtMaxLength", f"{ft_cfg['training']['max_length']}")
    raw("FtSeed", f"{ft_cfg['training']['seed']}")
    train_file = ROOT / ft_cfg['data']['train_file']
    n_train = sum(1 for line in train_file.read_text().splitlines() if line.strip())
    raw("FtTrainPairs", f"{n_train}")

    # ------------------------------------------------- Decoding hyperparameters
    # temperature/top_p are the one requested pair across every eval config
    # (grepped across all of configs/*.yaml: no other value ever appears);
    # GPT-5/GPT-5-mini are the one documented exception (scripts/create_batch.py
    # _FIXED_TEMP_MODELS: these two reject a custom value and run at the
    # provider's own fixed default instead).
    decode_cfg = yaml.safe_load(
        (ROOT / "configs" / "claude_sonnet_4_6__dynamic_L1L2__inst1.yaml").read_text()
    )["generation"]
    num("DecodeTemperature", decode_cfg["temperature"], "g")
    num("DecodeTopP", decode_cfg["top_p"], ".1f")
    raw("DecodeK", "1")

    # ------------------------------------------------- Environment / tool versions
    # Read from the actual running interpreter and installed packages (the
    # same environment that runs this very script), not hand-typed: found
    # while writing this block that the project actually pins Python 3.10
    # (pyproject.toml's requires-python, confirmed by the running
    # interpreter), not 3.11 as CLAUDE.md and the supporting report both
    # currently (incorrectly) state, and that `statsmodels` is not an
    # installed dependency at all (Holm-Bonferroni is a hand-written
    # function over numpy, src/Analysis/multiple_comparisons.py).
    import platform
    from importlib import metadata as _metadata
    raw("PyVersion", platform.python_version().rsplit(".", 1)[0])
    for pkg, macro in [
        ("transformers", "TransformersVersion"), ("peft", "PeftVersion"),
        ("torch", "TorchVersion"), ("pytest", "PytestVersion"),
        ("coverage", "CoverageVersion"), ("pandas", "PandasVersion"),
        ("scipy", "ScipyVersion"),
    ]:
        raw(macro, _metadata.version(pkg).split("+")[0])

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
