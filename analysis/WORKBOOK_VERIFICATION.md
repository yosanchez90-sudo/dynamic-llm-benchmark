# Workbook verification — `docs/Research_questions.xlsx` vs the repo

Phase 1 of the hypothesis-reconciliation pass, 2026-08-12. Read-only: this
document reports discrepancies, it does not fix them (see §5 for what's
queued for Phase 2/3, pending sign-off).

**Method**: `scripts/build_thesis_assets.py` was run end-to-end first
(Phase 0 — see the separate summary at the end of this session's reply for
what changed), so every number below is checked against **live,
just-regenerated** output, not a stale on-disk snapshot. `docs/
Approved_Hypotheses.md` is treated as governing for hypothesis *wording*;
the repo (`analysis/*.md`, `analysis/*.csv`) is treated as governing for
*numbers*, per your framing — the workbook is a map, not ground truth.

## 0. Headline

**The workbook's hypothesis wording is faithful to `docs/
Approved_Hypotheses.md`** (checked clause-by-clause, §1 below) and **the
large majority of its cited numbers are correct against live data** —
Comparison A, Comparison B, H2's entire DiD table, H3's headline
significance counts, and H6 clause 2's entire four-number cross-family
table all match exactly. But **two of the specific figures you flagged as
likely to have moved have in fact moved**, and the workbook still carries
the old values:

1. **H5's stability headline is stale and the gap is not small.** The
   workbook states mean pairwise Kendall τ (N=4) = **0.667**, with 6 of 6
   pairs individually significant at raw p<0.05. Live data (regenerated
   this session, reflecting Gemini Pro Preview's Dynamic-L4 crawl
   completing 2026-08-11) gives **τ = 0.583**, with only **3 of 6** pairs
   raw-significant. This doesn't change the qualitative verdict (still
   THRESHOLD NOT MET, now by a wider margin), but the point estimate and
   the "6 of 6" evidentiary claim are both currently wrong on disk.
2. **The RQ5 decomposition row's "conditional Mut@K alone = 0.333" is
   stale.** The live Kendall τ for that exact reading (pooled Dynamic vs
   ULT, n=9, the pre-registered primary) is **0.278**. 0.333 was the
   correct Kendall τ as of the 2026-08-07 snapshot; it has since drifted
   down. (It is also, confusingly, now the value of the *Spearman* ρ for
   that same pair — coincidence, not a mislabeling; the full trail is in
   §2.)

Both are downstream of the same root cause: **Gemini Pro Preview's
Dynamic-L4 crawl completed 2026-08-11**, after the numbers currently
baked into the workbook (and into several hand-written `analysis/*.md`
docs — this isn't a workbook-only problem, see §3) were computed. Neither
finding overturns a verdict, but both are "material" in the sense your
brief used the word — flagging per instruction 5 before touching anything
in Phase 2.

## 1. Hypothesis wording — Hypotheses sheet vs `docs/Approved_Hypotheses.md`

| # | Approved wording (verbatim, condensed here for the table) | Workbook's condensed wording | Verdict |
|---|---|---|---|
| H1 Test 1 | "Mutation scores produced by 8 LLMs on the dynamic benchmark will be lower than the scores on the static benchmarks, after controlling for cyclomatic complexity." Test: "paired comparison, Wilcoxon signed-rank across model–problem pairs." | Matches, condensed faithfully. | AGREES |
| H1 Test 2 | "Comparison between ULT vs PLT. Observational contamination signal: same models, decontaminated vs leaked equivalents. Having Mutation score as the main metric." | Matches. | AGREES |
| H2 | "...its mutation-score on the static benchmark will be larger than on the dynamic benchmark (even after applying changes)." Test: "validate differences on mutation scores (pre vs. post fine-tuning), considering (static vs. dynamic)." | Workbook renders this as a **gain** comparison ("its mutation-score **gain**... will exceed its gain..."). | AGREES, with a note — the approved sentence alone is ambiguous between "raw post-fine-tune score" and "gain," but the Test clause ("pre vs. post... static vs. dynamic") only makes sense as a gain/DiD comparison, so the workbook's reading is the correct disambiguation, not an addition to the approved text. Worth stating explicitly as an interpretive step when this hypothesis is written up, per your governance framing. |
| H3 | "Mean mutation score will keep decreasing (or stay the same) from L1 to L4... it will never go back up." Test: Spearman ρ, per model and pooled. | Near-verbatim. | AGREES |
| H4 | "The gap... will be larger at L1–L2 than at L3–L4." Test: tier×benchmark interaction, regression, LLM as random effect. | Verbatim. | AGREES |
| H5 | "...Kendall's τ... will exceed 0.7..." Test: pairwise Kendall's τ across instantiations. | Verbatim. | AGREES |
| H6 | Single approved sentence, two clauses (positive-but-imperfect; weaker-than-static). Test: Pearson r + Spearman ρ, **no Fisher z**. | Split into "H6 clause 1" / "H6 clause 2" rows. | AGREES — this is a faithful decomposition of one approved sentence into its two testable clauses, exactly what your task 8 asks the analysis to treat clause 2 as. The workbook is also correct that the approved wording requires no Fisher z-test (confirmed: `docs/Approved_Hypotheses.md` line 18 says only "Pearson r and Spearman ρ"). |

No hypothesis's approved *meaning* has been altered in the workbook. The
H2 "gain" reading is the only place an interpretive step was taken beyond
the literal sentence, and it's the correct one given the Test clause.

## 2. Quantitative claims — full verification table

"Verdict" is AGREES / DISAGREES / NOT FOUND against the **live**,
just-regenerated repo value. Where I flag DISAGREES I give both numbers
and the reason for the gap, not just the mismatch.

| Claim | Workbook value | Live repo value | Source (regenerated this session) | Verdict |
|---|---|---|---|---|
| H1 Test 1 (Comparison A raw) | n=8, effect_r=-0.167, p=0.7422 | n=8, effect_r=-0.167, p=0.7422 | `COMPARISON_PROVENANCE.md` | AGREES |
| H1 Test 1 robustness (thin-filtered) | n=6, effect_r=-1.000, p=0.0312 | n=6, effect_r=-1.000, p=0.0312 | same | AGREES |
| H1 Test 1 robustness (definition-matched) | n=8, effect_r=-0.833, p=0.0391 | n=8, effect_r=-0.833, p=0.0391 | same | AGREES |
| H1 Test 2 (Comparison B) | n=9, raw p=0.0391, thin p=0.0312, def-matched p=0.0078, PLT>ULT all 3 | n=9, raw p=0.0391, thin p=0.0312, def-matched p=0.0078, PLT>ULT all 3 | same | AGREES |
| H2 raw gain: seen-ULT | +99.1pp, CI [97.3, 100.0] | gain=0.991071, CI [0.973214, 1.000000] | `COMPARISON_C_PROVENANCE.md` "Four-level gradient" | AGREES |
| H2 raw gain: Dynamic-L1-L3 control | +8.7pp, CI [5.6, 12.0] | gain=0.087407, CI [0.056296, 0.120000] | same | AGREES |
| H2 raw gain: Dynamic-L4 | exactly 0.0pp | gain=0.000000, CI [0,0] | same | AGREES |
| H2 PLT DiD "after control" | +13.8pp, CI [7.7, 20.1] | did=0.137593, CI [0.077130, 0.201211] | `COMPARISON_C_PROVENANCE.md` "Robustness DiD (vs Dynamic-L1-L3)" | AGREES — this is the L1-L3-control DiD reading specifically, not the L4-control DiD (which equals the raw gain, since L4's own control_delta=0); worth being explicit about which control this is when writing it up, since the file reports both. |
| H2 PRE Mut@K undefined, seen-ULT | 111 of 112 | n_total=112, n_mut_defined=1 (pre) → 111 undefined | `COMPARISON_C_PROVENANCE.md` "Mut@K" table | AGREES |
| H2 verbatim-match rate | 100% (112/112) | 112/112 (100.0%) | `COMPARISON_C_INTERPRETATION.md` | AGREES |
| H3 all-tier significance | 9/9 models, Holm-corrected | 9/9, raw p=0.0001 all, Holm-adjusted all significant | `H3_TIER_GRADIENT_PROVENANCE.md` (fresh, regenerated this run) | AGREES |
| H3 L2-L4 significance | 8/8 computable | 8/8 computable, Holm-adjusted all significant | same | AGREES |
| H4 verdict | DROPPED, untestable, supervisor sign-off 2026-08-05 | Same, `PROJECT_BRIEF.md` §3.1 | `PROJECT_BRIEF.md`, `H4_DESIGN_MEMO.md` | AGREES |
| **H5 mean pairwise τ, N=4 headline** | **0.667** | **0.583** | `STABILITY.md` (fresh — "N=4 ... mean pairwise tau: 0.583") | **DISAGREES — stale, see §0/§3** |
| H5 all-pairs mean τ | 0.619 (per OPEN_ITEMS.md, not directly in workbook) | 0.569 | `STABILITY.md` | DISAGREES — same staleness, flagged for completeness even though not a literal workbook cell |
| **H5 "6 of 6 N=4 pairs raw-significant"** | **6/6** | **3/6** (pairs 1-2, 1-3, 2-4 only) | `STABILITY.md` Holm-Bonferroni section | **DISAGREES — stale, see §0/§3** |
| H5 "1 of 6 survives Holm (pair 1-2)" | 1/6, Holm p=0.0015 | 1/6, Holm p=0.001455 | `STABILITY.md` | AGREES — the one part of the H5 evidentiary claim that's still accurate; the Holm-survivor *count* happens to be robust to this data landing even though the raw-significant count and the mean aren't. |
| H5 StableMut@K SD "0.003–0.007 for most models" | 0.003-0.007 | Actual spread 0.00057 (Gemini Pro Preview) to 0.042 (Qwen 1.5B); the 7 non-outlier models span ~0.0013-0.0039 | `STABILITY.md` | ROUGH AGREEMENT, not exact — close enough not to flag as a defect on its own, but Gemini Pro Preview's SD is now unusually *low* (0.00057), below the stated band, which is itself a symptom of the same crawl-completion event; mentioned for completeness. |
| H6 clause 1: Dynamic↔BigCodeBench, cross-family n=7, raw τ | 0.429 (not significant) | 0.428571, perm p=0.241276 | `RQ5_CROSS_FAMILY_PROVENANCE.md` (fresh) | AGREES |
| H6 clause 1: same, coverage-adjusted | 0.905, p=0.0034, survives Holm | 0.904762, raw perm p=0.003400, Holm-adjusted p=0.033997 (<0.05) | same | AGREES — note the workbook's "p=0.0034" is the *raw* permutation p, and "survives Holm" is a separate, correctly-stated fact about the *Holm-adjusted* p=0.034; worth not conflating the two numbers when this is written up, even though neither is wrong. |
| **Decomposition (Results row 11): baseline_pass_rate alone** | **0.889** | **0.889** | `RQ5_DIAGNOSTICS.md` §3b, fresh | AGREES |
| **Decomposition: conditional Mut@K alone** | **0.333** | **0.278** (Kendall τ). 0.333 is that same row's *Spearman* ρ, and was the correct Kendall τ as of the 2026-08-07 snapshot. | `RQ5_DIAGNOSTICS.md` §3b + `RQ5_PROVENANCE.md`, both fresh | **DISAGREES — stale, see §0/§3** |
| **Decomposition: coverage-adjusted combined** | **0.944** | **0.944** | `RQ5_DIAGNOSTICS.md` §3b, fresh | AGREES |
| H6 clause 2: Dynamic↔BCB vs ULT↔BCB, coverage-adj | 0.905 vs 0.714 | 0.904762 vs 0.714286 | `RQ5_CROSS_FAMILY_PROVENANCE.md`, fresh | AGREES |
| H6 clause 2: same, raw Mut@K | 0.429 vs 0.238 | 0.428571 vs 0.238095 | same | AGREES |
| Per-tier Mut@K spread (H4 row, Hypotheses G4): L1 | 0.017 | 0.017 (range 0.983-1.000) | `RQ5_DIAGNOSTICS.md` §2, fresh | AGREES |
| Per-tier spread: L4 | 0.371 | 0.378 (range 0.541-0.919) | same | DISAGREES — small (0.007), likely the same Gemini-crawl-completion drift (Gemini Pro Preview's L4 min/max shifted as its n_defined grew from 38→292); not urgent but worth a refresh before citing in the write-up. |
| Per-tier spread: ULT | 0.494 | 0.494 (range 0.407-0.901) | same | AGREES |
| baseline_pass_rate range (Glossary B16) | 2.0% (Qwen 1.5B/ULT) to 96.3% (GPT-5/Dynamic-L4) | 0.020000 / 0.962667 | `comparison_a_coverage.csv`, fresh | AGREES |
| n_models: Comparison A (raw/thin/Comparison B) | 8 / 6 / 9 | 8 / 6 / 9 | `COMPARISON_PROVENANCE.md` | AGREES |
| n_problems, Comparison C (seen/unseen/PLT/L1-L3/L4) | 112 / 288 / 400 / ~675 / 225 | 112 / 288 / 400 / 675 / 225 | `COMPARISON_C_PROVENANCE.md` | AGREES |
| Model substitution note (Sheet2 F6) | GPT-5/-mini not GPT-5.4; Gemini 3.1 Pro Preview/Flash-Lite not 2.5 | Same, dated 2026-07-14 | `PROJECT_BRIEF.md` §11 | AGREES |
| Kendall τ at n=3, "best possible p is 0.167" (Glossary B29) | 0.167 (one-sided) | Consistent — this project's own n=3 permutation p's land at 0.331-0.341 (two-sided), matching 2×(1/6) | `RQ5_PROVENANCE.md` canonical n=3 rows | AGREES — general statistical fact, not a repo-specific number, correctly stated |

**`RANKING_MATRIX.md` finished regenerating after the rest of this table
was drafted — confirmed, not just predicted**: Table 2 now reads
`conditional Mut@K | τ=0.278 ρ=0.333` for Dynamic↔ULT (line 154) — exactly
the live value above, independently computed a third time by a third
script. Its Table 4 (reliability) also now reads **0.583** for conditional
Mut@K's N=4 mean pairwise τ (line 180) — the same number `STABILITY.md`
gives directly. This matters beyond confirming §2: `RQ5_INTERPRETATION.md`
cites this exact Table 4 figure as "0.667" in its own "why conditional
Mut@K specifically behaves this way" reasoning (point 2, reliability) — so
the staleness in §0/§3 isn't confined to the two workbook cells already
flagged, it also undercuts one leg of that document's own three-part
argument. Not re-verified independently: the exact per-model StableMut@K
figures beyond the SD band above (no reason to doubt them, just not
individually cross-checked).

## 3. Root cause of the two material disagreements

Both stale figures (H5's stability mean, the RQ5 decomposition's
"conditional Mut@K alone" figure) are symptoms of the same event: **Gemini
3.1 Pro Preview's Dynamic-L4 crawl finished 2026-08-11**, growing its
Dynamic-L4 sample from 38 rows (all in instantiation 1, per the
2026-08-07 snapshot every current hand-written doc was written against)
to 292 rows spread across more instantiations. That changes two things
that ripple into exactly these two numbers:

- Gemini Pro Preview's per-instantiation model-level pooled Mut@K, which
  feeds every pairwise Kendall τ in `STABILITY.md` — hence H5's mean and
  raw-significant count moving.
- Gemini Pro Preview's contribution to the pooled Dynamic↔ULT correlation
  in `RQ5_PROVENANCE.md`/`RQ5_DIAGNOSTICS.md` — hence the conditional
  Mut@K Kendall τ moving from 0.333 to 0.278.

**This is not a workbook-authoring problem** — it's a data-landing
staleness problem that the workbook inherited from the hand-written repo
docs it was built from. `analysis/RQ5_INTERPRETATION.md` itself cites
"τ=0.333" as the pre-registered primary's Kendall τ in well over a dozen
places (its own headline table, the ranking-matrix summary, the
disattenuation section, the Holm-Bonferroni section...), all dated
2026-08-07. `analysis/OPEN_ITEMS.md`'s sanitizer-sensitivity and
data-landing entries make the same claim. None of these have been
refreshed since the crawl completed four days later. **The workbook is a
faithful mirror of what the repo's own hand-written docs currently say —
the repo's own hand-written docs are what's now stale**, confirmed
directly against this session's live Phase 0 rebuild.

## 4. Internal consistency — within the workbook

Checked every figure that appears on more than one sheet:

- H1 Test 1/2, H2, H3, H6 clause 1/2 figures: **consistent** between the
  Hypotheses sheet and the Results sheet everywhere they're both quoted.
- H5's figures are **consistently wrong in the same way** on both sheets
  (Hypotheses E7 and Results E8/F8/G8 both say 0.667 / 6-of-6) — internally
  consistent with each other, just both stale against the same live data
  gap identified above.
- One minor, non-numeric inconsistency: Sheet2's F6 cell explicitly notes
  "The spec's own RQ4.2 text still names the old models and needs
  correcting," but Sheet2's own N7 cell (Objective O6's description, a
  few rows below) still contains that exact uncorrected text ("GPT-5.4...
  Gemini 2.5 Pro / Gemini 2.5 Flash"). The workbook has correctly
  *diagnosed* this staleness in one cell without yet fixing the cell it's
  describing — worth closing in the same edit pass as the numeric fixes
  in Phase 3, not a numeric error, just an unclosed loop.

## 5. Reverse check — what the workbook omits or would let a reader miss

Material findings that exist in the repo but that a reader relying only
on the workbook would not learn:

1. **The sanitizer-repair sensitivity of the coverage-adjusted
   correlation.** `RQ5_SANITIZER_SENSITIVITY.md` (fresh, this session):
   the coverage-adjusted Dynamic↔ULT τ=0.944 the workbook cites (correctly)
   drops to **τ=0.889** if mechanically-repaired rows are excluded
   entirely — still significant (perm p=0.0003), but the workbook presents
   0.944 as if it were the only reading. Given 0.889 is itself one of the
   numbers your own audit brief flagged as worth checking, and it only
   exists as a *robustness* variant of the 0.944 figure the workbook
   already reports, this is worth a one-line caveat wherever 0.944 is
   quoted going forward.
2. **Two of the 7 cross-family BigCodeBench correlation points are
   individually thin-cell** (CodeLlama-13B: ULT n_defined=8; Mistral-7B:
   Dynamic n_defined=5, ULT n_defined=1 — both below this project's own
   n_defined<20 thinness threshold). This travels with every citation of
   the cross-family n=7 correlation elsewhere in `analysis/`
   (`METRICS_AND_FINDINGS_EXPLAINED.md`), but the workbook's H6 rows
   (which are exactly the rows citing that n=7 correlation) don't mention
   it. Relevant directly to task 8's request for CIs at n=7 — the CIs
   themselves are wide partly because of this.
3. **StarCoder2's non-identical prompt delivery and 2 models' chat-template
   date drift** (cross-family limitations, `RQ5_INTERPRETATION.md`) — same
   category as #2, a caveat that belongs with any citation of the n=7/n=13
   cross-family figures the workbook already reports.
4. **The `analysis/TIER_SYMMETRY_AUDIT.md` figure defect** (delivered
   earlier this session, uncommitted pending your review): the
   `ranking_matrix_heatmap.pdf` figure has no "(pooled)" disclosure,
   unlike every other RQ5 figure. Not a hypothesis-verification finding
   per se, but relevant if that figure is the one used to illustrate H6 in
   the write-up.
5. **`ULT_DATA_QUALITY_AUDIT.md`'s findings about the published ULT/PLT
   artifact itself** (8.4% ground-truth pass rate, self-reported-CC
   unreliability, a metric-definition contradiction between the paper's
   prose and its own code) are not referenced anywhere in the workbook.
   `OPEN_ITEMS.md` already scopes these as "not blocking for internal
   dissertation use... supervisor review still required before any
   external use" — the workbook doesn't need to carry this to be correct,
   but a reader using only the workbook to understand ULT/PLT as a
   benchmark would miss it.

**Nothing found in the reverse direction that the workbook
*misrepresents*** in the sense of asserting something the repo
contradicts outright, beyond the two staleness items in §0/§2 — every
other workbook claim checked is either accurate or a defensible,
correctly-flagged interpretive choice.

## Addendum (2026-08-12, during Phase 3): a second stale-model-name cell found

While generating `docs/RESEARCH_QUESTIONS.md` (Phase 3, task 10), a second
instance of the same stale-model-name issue flagged in §4 (Sheet2 N7) was
found in **Sheet2 C8** (RQ4.4's own research-question description),
missed by the original consistency pass since I had only checked N7 at
the time: "Compare the three frontier-tier slots (GPT-5.4, Claude Sonnet
4.6, Gemini 2.5 Pro)... GPT-5.4 mini, Claude Haiku 4.5, Gemini 2.5 Flash."
Same category, same root cause (both are RQ4-family cells never updated
after the 2026-07-14 model substitution recorded in `PROJECT_BRIEF.md`
§11), fixed alongside N7 as part of Phase 3's workbook edits. Noted here
so this file's own record of what was found stays complete, not just
what was found first.

## 6. What this means for Phase 2

Per your instruction 5: **reporting before proceeding**, since two figures
disagree materially (§0). Neither disagreement changes a hypothesis's
qualitative verdict — H5 is THRESHOLD NOT MET either way (0.667 or 0.583,
both below 0.7), and the RQ5 decomposition's qualitative story ("baseline
pass rate explains nearly all of the coverage-adjusted agreement, mutation
quality alone does not cross-benchmark-agree") is if anything *more* true
at τ=0.278 than at 0.333, not less. But the exact numbers need refreshing
before Phase 2 builds on them (task 7's Holm-Bonferroni recompute doesn't
touch either of these two figures directly, so it can proceed
independently; task 8's H6 clause 2 table is unaffected, since every
number in it already checked out in §2; task 9's H3 monotonicity check
draws on `RQ5_PROVENANCE.md`'s fresh per-tier columns, already live).

Recommend: proceed to Phase 2 using the **live** numbers throughout (the
ones in the "Live repo value" column above, not the workbook's), and
include refreshing `STABILITY_INTERPRETATION.md`'s and
`RQ5_INTERPRETATION.md`'s own stale citations (§3) as part of Phase 3's
reference-artifact update, since they're the actual source of the
workbook's staleness, not just the workbook itself. Waiting for your
go-ahead before touching anything.
