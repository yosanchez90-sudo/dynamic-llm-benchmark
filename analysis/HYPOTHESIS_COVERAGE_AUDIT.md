# Hypothesis coverage audit — the approved six, and only the approved six

**Rewritten 2026-08-12** as part of the hypothesis-reconciliation pass
(`analysis/WORKBOOK_VERIFICATION.md`, `analysis/HYPOTHESIS_DEVIATIONS.md`).
Earlier versions of this file predate `docs/Approved_Hypotheses.md`
entering the repo and used an inferred, incorrect H1-H6 mapping (treating
H1 as a single test, not knowing H1 carries two). That version is
superseded, not preserved inline below — see git history if the
investigative narrative from 2026-08-04/05 is needed.

**Governing document for hypothesis identity and wording**:
`docs/Approved_Hypotheses.md` — exactly six hypotheses, H1 carries two
tests, H5 covers the whole of RQ4. A later expanded draft (H4a, H4b,
separate RQ4.2-4.4 hypotheses) was never submitted or approved; recorded
as "drafted, not submitted, not pursued" in `PROJECT_BRIEF.md` §11, not
tracked here.

For each approved hypothesis/test: (i) implemented, (ii) run against
current data, (iii) written interpretation, (iv) **final verdict** — one
of SUPPORTED / NOT SUPPORTED / THRESHOLD NOT MET / DROPPED-UNTESTABLE /
MIXED, since none may be left ambiguous. Full
reasoning, verbatim approved wording, and paper-ready sentences for every
row: `analysis/HYPOTHESIS_DEVIATIONS.md`. This file's job is narrower —
confirm the pipeline (code exists, ran, is interpreted) and state the
verdict, not re-derive it.

## H1 Test 1 (RQ1) — paired Wilcoxon, Dynamic-L4 vs ULT, model level

- (i) Implemented: yes — `src/Analysis/comparison.py::paired_wilcoxon`,
  invoked by `scripts/build_comparison_tables.py`.
- (ii) Run: yes — `analysis/COMPARISON_PROVENANCE.md`, n=8/9 canonical
  models (Qwen 1.5B floor-excluded).
- (iii) Interpreted: yes — `analysis/COMPARISON_A_INTERPRETATION.md`.
- (iv) **Verdict: NOT SUPPORTED.** effect_r=-0.167, p=0.7422 (raw/
  pre-registered). The rank-biserial effect size — the statistic the
  approved test actually specifies — runs opposite to the predicted
  direction (Dynamic-L4 favored), even though the raw column means run
  the predicted way. See `HYPOTHESIS_DEVIATIONS.md` for the full
  reconciliation of that tension.

## H1 Test 2 (RQ1) — ULT vs PLT, CC-band matched

- (i) Implemented: yes — Comparison B, same module, invoked by the same
  script. **Corrected 2026-08-12**: previously treated in this file and
  `COMPARISON_A_INTERPRETATION.md` as an unofficial exploratory check,
  outside PROJECT_BRIEF's hypothesis set. `docs/Approved_Hypotheses.md`
  names it verbatim as H1's own second test — that framing was wrong and
  is fixed throughout `analysis/` as of this pass.
- (ii) Run: yes — `analysis/COMPARISON_PROVENANCE.md`, n=9 (full
  canonical roster).
- (iii) Interpreted: yes — `analysis/COMPARISON_A_INTERPRETATION.md`'s
  "Contrast with Comparison B / H1 Test 2" and "Multiple-comparisons
  correction for RQ1" sections (rewritten 2026-08-12).
- (iv) **Verdict: MIXED.** PLT scores higher than ULT — the
  contamination-consistent direction — on all three conditionings, but
  whether this is "significant" depends on which conditioning and
  correction is quoted: at the raw/pre-registered-primary conditioning,
  Holm-Bonferroni within RQ1's two-test family moves p from 0.0391 to
  0.0782 (does not survive); at the definition-matched co-primary
  conditioning, both H1 tests survive (0.0078→0.0156). Report the
  direction as the robust claim; report significance only with its
  conditioning stated.

## H2 (RQ1) — difference-in-differences, 2×3 design

- (i) Implemented: yes — `src/Contamination/did.py::compute_did`,
  invoked by `scripts/analyze_comparison_c.py`.
- (ii) Run: yes — `analysis/COMPARISON_C_PROVENANCE.md`.
- (iii) Interpreted: yes — `analysis/COMPARISON_C_INTERPRETATION.md`,
  the most thoroughly investigated result in the project.
- (iv) **Verdict: SUPPORTED.** seen-ULT +99.1pp (CI [97.3,100.0]), 100%
  verbatim reproduction; Dynamic-L1-L3 control +8.7pp (CI [5.6,12.0]);
  Dynamic-L4 exactly 0.0pp (floor-limited). `baseline_pass_rate`, not
  literal mutation score, is the primary outcome — PRE Mut@K is undefined
  for 111 of 112 seen-ULT problems (disclosed, not silent). H2 reports no
  p-value by design (effect sizes + CIs); contributes nothing to RQ1's
  Holm-Bonferroni family.

## H2-supplementary (RQ1) — post-hoc, not part of the approved six

Not one of the six pre-registered hypotheses; recorded here for the same
coverage discipline this file applies to the approved set, not because it
carries the same evidentiary weight. Tracked separately in
`docs/Research_questions.xlsx`'s `Hypotheses`/`Results` sheets and
`PROJECT_BRIEF.md` §3.1, both marked post-hoc.

- (i) Implemented: yes — `scripts/build_finetune_endpoint_table.py`
  (`baseline_pass_rate`, seen vs fresh) and
  `scripts/build_finetune_decline_table.py` (`exec_rate` held-out
  trajectory, epoch 0 vs 30).
- (ii) Run: yes — `analysis/finetune_endpoint_table.csv`,
  `analysis/finetune_decline_table.csv`, both from
  `data/results/finetune_rebuild/epoch_perf_*.csv` (the corrected,
  post-`no_repeat_ngram_size`-fix set — see `analysis/README_QUARANTINE.md`
  for why the un-prefixed `analysis/epoch_perf_finetune_*.csv` files are a
  different, intentionally-preserved contaminated set, not a duplicate).
- (iii) Interpreted: yes — `analysis/FINETUNE_ENDPOINT_PROVENANCE.md`.
- (iv) **Verdict: SUPPLEMENTARY (POST-HOC).** Two Qwen models (1.5B, 7B),
  each fine-tuned three ways on dynamic-benchmark instantiation 1: on
  their own prior generations (self-contamination), on GPT-5's
  generations on the same instantiation (cross-model contamination), and
  on instantiation 1's reference outputs filtered only by whether they
  execute, not whether they are correct (non-leaked control). Both leaked
  conditions show a seen-vs-fresh `baseline_pass_rate` gap at both sizes
  (self: 8.7pp / 4.7pp; cross-model: 52.7pp / 68.0pp); the non-leaked
  control shows none (2.3pp / -2.3pp, noise). The cross-model conditions
  additionally show a held-out `exec_rate` decline by epoch 30 (1.5B:
  92.7%→63.3%; 7B: 99.7%→85.3%) that the self-contamination conditions do
  not, so part of the cross-model gap reflects a general capability cost
  specific to training on another model's outputs, not memorisation
  alone. No control-relative gain is computed (unlike Comparison C); each
  condition's seen/fresh/gap is reported directly.

## H3 (RQ2) — Spearman ρ, tier index vs mutation score

- (i) Implemented: yes — `scripts/analyze_h3_tier_gradient.py`,
  pre-registered in `analysis/H3_ANALYSIS_PLAN.md` before being run.
- (ii) Run: yes — `analysis/H3_TIER_GRADIENT_PROVENANCE.md`, n=9
  canonical models.
- (iii) Interpreted: yes — `analysis/H3_INTERPRETATION.md`, including a
  new (2026-08-12) section closing the approved wording's literal "never
  goes back up" clause.
- (iv) **Verdict: SUPPORTED.** 9/9 models significant, Holm-corrected in
  both the all-tier and L2-L4 (ceiling-robustness) families — the
  cleanest, least-contested result in the project. Disclosed nuance, not
  a change to this verdict: Spearman ρ tests a monotone trend, and the
  approved wording's stronger literal clause holds exactly for 7/9
  models; GPT-5 and GPT-5-mini each show one sub-1pp rebound at L1→L2,
  both already at ≥98% mutation score at that tier (near-ceiling noise).

## H4 (RQ3) — tier×benchmark interaction, mixed-effects regression

- (i) Implemented: no, deliberately — `statsmodels` was never added as a
  dependency.
- (ii) Run: n/a.
- (iii) Interpreted: yes — `analysis/H4_DESIGN_MEMO.md` records the
  options considered and the decision.
- (iv) **Verdict: DROPPED-UNTESTABLE.** Approved by the supervisor
  2026-08-05. ULT/PLT contain no CC<8 (L1-L2-equivalent) problems by the
  source dataset's own filter, so no static-benchmark score exists at low
  complexity to form the predicted gap with — the interaction term cannot
  be estimated when one side of the interaction has zero variance in the
  tier variable. RQ3 is answered narratively via H3's tier gradient plus
  this structural finding itself.

## H5 (RQ4, all) — pairwise Kendall's τ across instantiations

- (i) Implemented: yes — `src/Analysis/stability.py`, invoked by
  `scripts/analyze_stability.py`.
- (ii) Run: yes — `analysis/STABILITY.md`, N=4 headline scope (2 of 9
  canonical models, both Gemini, capped below the approved N=5).
- (iii) Interpreted: yes — `analysis/STABILITY_INTERPRETATION.md` (note:
  this file's own headline number, 0.667, is stale as of this pass — see
  "Open item" below).
- (iv) **Verdict: THRESHOLD NOT MET.** Mean pairwise τ = **0.583** at the
  N=4 headline scope (live, this pass's rebuild — corrected from a
  stale 0.667, `analysis/WORKBOOK_VERIFICATION.md`), below the approved
  0.7 criterion. Only 1 of 6 N=4-scope pairs individually exceeds 0.7,
  and it is the only one to survive Holm-Bonferroni correction within the
  family. Score-level reliability is separately strong (StableMut@K SD
  0.001-0.004 for most models) and not in question — it is specifically
  rank-level agreement across re-instantiations that falls short.

## H6 clause 1 (RQ5) — positive but imperfect correlation with proxy Pass@1

- (i) Implemented: yes — `src/Analysis/correlation.py::compute_correlations`,
  invoked by `scripts/analyze_rq5.py` / `analyze_rq5_cross_family.py`.
- (ii) Run: yes — `analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`, n=3
  canonical / n=7 cross-family.
- (iii) Interpreted: yes — `analysis/RQ5_INTERPRETATION.md`.
- (iv) **Verdict: MIXED.** Positive under every metric and scope; the
  cross-family n=7 raw conditional Mut@K reading (τ=0.429, not
  significant) is imperfect as predicted, but the coverage-adjusted
  reading (τ=0.905, Holm-adjusted p=0.034) is close enough to perfect
  rank agreement to fall in this project's own pre-registered "redundant"
  zone rather than the "validity-supporting" one.

## H6 clause 2 (RQ5) — dynamic-proxy correlation weaker than static-proxy?

- (i) Implemented: yes — same machinery as clause 1; no new code needed,
  clause 2 is a direct comparison of two already-computed correlations.
- (ii) Run: yes — same source, `analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`.
- (iii) Interpreted: yes — **new 2026-08-12**, `analysis/
  RQ5_INTERPRETATION.md`'s "H6 clause 2 — reported result" section (this
  was previously computable but never written up; closed this pass).
- (iv) **Verdict: NOT SUPPORTED.** Dynamic↔BigCodeBench is the stronger
  (or tied) correlation in all 12 scope×metric×statistic combinations
  tested (Pearson/Spearman/Kendall × raw/coverage-adjusted × n=3
  canonical/n=7 cross-family) — never weaker than ULT↔BigCodeBench.
  Direction is opposite to the prediction; defensible as a favourable
  finding, not a failed one.

## Multiple-comparisons correction — status by family, updated 2026-08-12

- **RQ1 (H1 Test 1 + H1 Test 2): real, now-corrected exposure.** Previously
  treated as a size-one family (a no-op) because H1 Test 2 was
  misclassified as unofficial. Now a genuine two-test family — see H1
  Test 2's verdict above and `COMPARISON_A_INTERPRETATION.md` for the
  full per-conditioning table. H2 contributes no p-value.
- **RQ2 (H3): one family (9 models), all-tier and L2-L4 sub-families,
  Holm-corrected, 9/9 and 8/8 survive.** No exposure concern — every
  member is significant at the permutation floor.
- **RQ3 (H4): n/a — not built, nothing to correct.**
- **RQ4 (H5): real, current exposure, unchanged in kind by this pass.**
  6 (N=4 set) + 10 (all-pairs) pairwise Kendall τ tests, each corrected
  within its own family. Live numbers (`STABILITY.md`, this pass):
  3/6 and 4/10 raw-significant, 1/6 and 2/10 survive Holm.
- **RQ5 (H6): the largest real exposure, unchanged in kind by this pass.**
  Up to 12 headline correlation tests (`RQ5_CROSS_FAMILY_PROVENANCE.md`'s
  Holm-Bonferroni section), 4/12 raw-significant, 3/12 survive Holm.

## Open item carried into Phase 4

`analysis/STABILITY_INTERPRETATION.md` (hand-written) still cites the
stale τ=0.667 stability figure <!-- cite:historical -->, and `analysis/RQ5_INTERPRETATION.md`
still cites τ=0.333 in the dozen-plus places it appeared before this
pass (both superseded by this pass's live rebuild — τ=0.583 and τ=0.278
respectively). This pass added a new, fully-live H6 clause 2 section to
`RQ5_INTERPRETATION.md` but did not sweep the file's pre-existing prose
citations of 0.333. Flagged as a recommended follow-up, not completed in
this pass — see the Phase 4 readiness report for scope reasoning.
