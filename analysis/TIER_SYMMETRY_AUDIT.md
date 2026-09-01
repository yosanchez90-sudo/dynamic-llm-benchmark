# Tier-symmetry audit — read-only, 2026-08-11

Correctness audit, not a redesign. Goal: confirm every cross-benchmark
comparison compares like with like, and that any deliberate asymmetry is
deliberate, documented, and consistent. **No code was changed for this
audit.** Every filter quoted below is copied from the actual source, not
inferred from a doc.

## Zero — a background fact in the audit brief is now stale, and it matters

The brief's floor-effect section states "Gemini-Pro: no L4 rows at all."
**That was true when written but is not true now.** Checked directly
against current data:

```
gemini-3.1-pro-preview  Dynamic-L4  n_total=300  n_defined=292
```

Gemini Pro Preview's Dynamic-L4 crawl finished during this same working
session (a daily-quota-limited crawl that started 2026-08-06, completed
2026-08-11 — see `CONVENTIONS.md`'s crawl-incident entries and
`analysis/COMPARISON_A_INTERPRETATION.md`). It is no longer floor-limited
or missing at L4; it is now one of the best-covered models at that tier
(292/300, second only to GPT-5's 361/375). This changes the floor-effect
picture materially — see §5.

## 1. Inventory

Tier filter is quoted verbatim from the source line; "—" means the
analysis doesn't touch a Dynamic-vs-ULT/PLT comparison at all (out of
scope for tier symmetry, included per the brief's "at minimum" list
anyway, so the omission is visible rather than silent).

| Analysis | Script | Dynamic-side filter (code) | ULT/PLT-side filter | CC-comparable? | Documented where |
|---|---|---|---|---|---|
| **Comparison A**, raw | `scripts/build_comparison_tables.py` L88 | `dynamic[dynamic["tier"] == DYNAMIC_TIER]`, `DYNAMIC_TIER="L4"` (`src/Analysis/comparison.py` L39) | `ult` — no filter needed, ULT/PLT are CC≥8-only by construction | **Yes** | `comparison.py` module docstring L19-21 (explicit rationale: "comparing against ALL Dynamic tiers pooled would conflate benchmark identity with complexity difference"); `COMPARISON_A_INTERPRETATION.md`; generated `COMPARISON_PROVENANCE.md` |
| Comparison A, thin-filtered | same script L138-146 | same `dynamic_l4`, thin cells (n_defined<20) dropped from both sides | same | **Yes** (filter is symmetric — n_defined<20 checked on *both* sides, L133-141) | same |
| Comparison A, definition-matched (coverage-adjusted) | same script L106-113 | same `dynamic_l4`, zero-filled variant | same, zero-filled | **Yes** | same |
| **Comparison B**, paired/matched-CC/Wilcoxon | same script L149-154 | *(no Dynamic side — ULT vs PLT only)* | `load_cc_bands("ult")` / `load_cc_bands("plt")`, both from `subsample_manifest.json` tag=core_400 (`matched_cc_table`, `comparison.py` L232-257) | **Yes**, and bands applied identically on both sides (`band_lookup_ult`, `band_lookup_plt`) | `comparison.py` module docstring L23-27 |
| **Comparison C**, seen-ULT/unseen-ULT/PLT | `scripts/analyze_comparison_c.py` L57-69 | *(no Dynamic side for these 3 arms)* | full core_400 rows, tagged seen/unseen via `comparison_c_seen_manifest.json` | N/A (not Dynamic-vs-X) | script docstring L6-8 |
| Comparison C, `dynamic_l4` arm (primary control) | same script L76 | `np.where(df["tier"]=="L4", "dynamic_l4", ...)`, `instantiation_id ∈ {1,2,3}` | vs. seen/unseen-ULT and PLT (CC≥8) | **Yes** | script docstring L9-11; labelled `"control": "dynamic_l4"` in every output row |
| Comparison C, `dynamic_l1l3` arm (robustness control) | same script L76 | same `np.where`, else-branch = L1-L3 pooled | same | **No, by design** | **DELIBERATE** — script docstring L12 names it "headroom control" explicitly; `did_table` output tags every row `"control": "dynamic_l1l3"`, never merged with the L4 rows |
| **RQ5 canonical**, Dynamic↔ULT | `scripts/analyze_rq5.py` L75, L116 | `_mut(d)` where `d = dynamic[dynamic["model_label"]==label]` — **no tier filter, all tiers pooled** | `ult` — CC≥8 only | **No** | Pair itself is labelled `"Dynamic(pooled) <-> ULT"` (L116); module docstring L4-5 says "pooled Mut@K across all landed tiers"; `RQ5_ANALYSIS_PLAN.md` pre-registers pooling as primary |
| RQ5 cross-family, Dynamic↔ULT | `scripts/analyze_rq5_cross_family.py` L116, L176 | same pooled `_mut(d)` | same | **No** | Pair labelled `"Dynamic(pooled) <-> ULT [...]"` (L176-177); script docstring L9-13 explains this deliberately mirrors the canonical script's convention |
| RQ5, Dynamic↔BigCodeBench | `analyze_rq5.py` L119/122, `analyze_rq5_cross_family.py` L184/197 | same pooled `_mut(d)` | BigCodeBench Pass@1 — not CC-tiered at all | **N/A** — BigCodeBench has no CC-band to match against, so "pooled vs L4" isn't a symmetry question here the way Dynamic-vs-ULT is | Pair labelled `"Dynamic(pooled) <-> public"` regardless |
| ULT↔BigCodeBench | same scripts | *(no Dynamic side)* | ULT Mut@K vs Pass@1 | N/A | — |
| RQ5, coverage-adjusted variants of all of the above | both RQ5 scripts, `dynamic_coverage_adj` = `dynamic_mutk_pooled * dynamic_bp_pooled` | same pooled basis | same | **No** (inherits the raw pair's asymmetry — it's the same pooled score, just re-weighted) | Same disclosure as the raw pair; **not separately re-stated** at the coverage-adjusted row specifically (see §3) |
| **RQ5 diagnostics**, tier-matched vs pooled vs per-tier | `scripts/analyze_rq5_diagnostics.py` L107-109, L157-169 | Computes **both**: `d` (pooled) and `d[d["tier"]==tier_label]` for L1/L2/L3/L4, side by side in one table | `ult`, unfiltered | Table row labelled explicitly per tier, including an `L4` row that **is** CC-comparable | **Yes, this is the disclosure point** — table's own "Dynamic side" column names which reading is which; `## 1. Tier-matched (L4-only) vs pooled vs per-tier` heading |
| **H3** (tier gradient) | `scripts/analyze_h3_tier_gradient.py` | Dynamic-only (L1-L4 gradient within Dynamic) | *(script never references `ult`/`plt` — confirmed via grep, zero matches)* | **N/A — out of scope**, H3 never compares against ULT/PLT | — |
| **StableMut@K** / pairwise Kendall τ | `scripts/analyze_stability.py`, `src/Analysis/stability.py` | Dynamic-only, `--results-dir` defaults to `data/results/dynamic` | *(never touches ULT/PLT — confirmed via grep, zero matches)* | **N/A — out of scope** | — |
| Ranking matrix, Table 1 (per-metric scores) | `scripts/build_ranking_matrix.py` L106-113 | Computes **both** `dynamic_pooled` (`tier_filter=None`) and `dynamic_L4` (`tier_filter="L4"`) as separate named views | `ult_core400` | **Yes** — both views shown as separate lettered columns (a) Dyn pooled, (b) Dyn L4, (c) ULT | Table 1 header itself: "(a) Dynamic pooled, (b) Dynamic L4, (c) ULT core_400" (L265) |
| Ranking matrix, Table 2 (cross-benchmark rank agreement — "the single most informative number in the file" per `RQ5_INTERPRETATION.md`) | same script L158 | `("Dynamic<->ULT", "dynamic_pooled", "ult_core400")` — **pooled only, L4 not included in this table** | `ult_core400` | **No** | Caption line: "Dynamic side uses pooled (matching this project's established RQ5 primary convention)" (L300) — **present in the generated .md, absent from the standalone figure, see §3** |
| Ranking matrix, Table 3 (noise floor) | same script L203-230 | `dynamic_pooled` only | *(Dynamic-only statistic, no ULT side)* | N/A | Section header: "Table 3: noise floor (canonical scope, Dynamic pooled)" (L322) |
| Ranking matrix, Table 4 (reliability) | same script | Dynamic-only, per-instantiation | *(no ULT side — this is StableMut@K reused)* | N/A — out of scope | — |
| **Figure**: `rq5_correlation.png` | `scripts/plot_rq5_correlation.py` L64-65 | `dynamic_mutk_pooled` | `ult_mutk` | **No** | X-axis label itself: `"Dynamic Mut@K (pooled, all tiers)"` — disclosed **in the figure**, not just the surrounding doc |
| **Figure**: `rq5_cross_family_correlation.png` (4 panels) | `scripts/plot_rq5_cross_family_correlation.py` L70-88 | `dynamic_mutk_pooled` throughout | `ult_mutk` / `public_score` | **No** | Axis label `"Dynamic Mut@K"` + panel subtitle always says `"Dynamic(pooled) <-> ..."` explicitly |
| **Figure**: `ranking_matrix_heatmap.pdf/.png` | `scripts/plot_ranking_matrix_heatmap.py` L32-33, L106-111 | Visualises Table 2 (pooled-only, see above) | — | **No** | **NOT disclosed in the figure** — see §3, defect #1 |
| **Figure**: `noise_floor_by_tier.png` | `scripts/plot_noise_floor.py` | Dynamic-only, explicit per-tier + pooled bars (`TIERS + ["pooled"]`, L47-48) | *(no ULT side)* | N/A — out of scope | Bar labels are the tier names themselves |
| **Figure**: `collapse_vs_survival.png` | `scripts/plot_collapse_vs_survival.py` L56-57 | `dynamic_mutk_pooled` | `public_score` (BigCodeBench) | N/A (BigCodeBench, not ULT/PLT) | X-axis label: `"Dynamic (pooled)"` |
| **Figure**: `comparison_c_onset_curve.png` | `scripts/plot_comparison_c_onset_curve.py` L40 | `dynamic_l1l2` control arm (L1/L2 only — note: **not** L1-L3, a narrower slice than the DiD table's `dynamic_l1l3`, see note below table) | seen-ULT / unseen-ULT | **No, by design** (same "control," not comparator, framing as Comparison C's DiD table) | Legend label itself: `"Dynamic L1/L2 (control)"` |

**Note on the onset-curve figure's `dynamic_l1l2` vs the DiD table's `dynamic_l1l3`**: these are two different Dynamic slices used for two different Comparison C artifacts (the onset-curve figure tracks epoch-by-epoch training dynamics using whatever tier-tagged files were generated for that purpose; the DiD table's headroom control pools L1-L3). Both are internally self-labelled at the point of use (figure legend and DiD table's `control` column respectively), so neither is undisclosed — but the two different Dynamic-control definitions living side-by-side under similar names (`dynamic_l1l2` / `dynamic_l1l3`) is worth a reader's attention. Flagged in §6 as a minor disclose-in-paper item, not a defect.

## 2. Classification

| # | Analysis | Class | Rationale |
|---|---|---|---|
| 1 | Comparison A (all 3 conditionings) | **(a) SYMMETRIC** | `DYNAMIC_TIER="L4"` applied consistently, explicit rationale in code |
| 2 | Comparison B (paired, matched-CC) | **(a) SYMMETRIC** | No Dynamic side; CC-bands applied identically to both ULT and PLT |
| 3 | Comparison C, `dynamic_l4` arm | **(a) SYMMETRIC** | CC-matched by construction, used as the *primary* DiD control |
| 4 | Comparison C, `dynamic_l1l3` arm | **(b) DELIBERATE ASYMMETRY** | Named "headroom control" in the docstring; reported as a clearly-separate, clearly-labelled robustness row, never conflated with the L4 primary |
| 5 | **RQ5 canonical, Dynamic↔ULT (pooled)** | **(b) DELIBERATE ASYMMETRY — pre-registered, but with an incomplete disclosure trail** | Pre-registered as pooled (`RQ5_ANALYSIS_PLAN.md`); RQ5_DIAGNOSTICS.md itself names tier composition as a candidate explanation and shows the L4-only version's rank statistic collapses to exactly τ=0.000 (not even a sign flip — a total loss of signal, `RQ5_DIAGNOSTICS.md` sec 1). **Disclosed at most, not all, points of use** — see §3 for exactly which ones are missing it. |
| 6 | RQ5 cross-family, Dynamic↔ULT | **(b) DELIBERATE ASYMMETRY**, same as #5 | Same pooled convention, same partial disclosure trail (inherits #5's gaps) |
| 7 | RQ5, Dynamic↔BigCodeBench / ULT↔BigCodeBench | **(a) SYMMETRIC in the relevant sense** | BigCodeBench has no CC restriction to mismatch against — pooling Dynamic here isn't comparing a hard-only benchmark against a mixed one, it's comparing a mixed benchmark against an *unrestricted* one. Still labelled "(pooled)" everywhere it appears, so no disclosure gap either way. |
| 8 | RQ5 diagnostics (tier-matched vs pooled vs per-tier) | **(a) SYMMETRIC / self-disclosing by construction** | The whole point of this table is showing all readings side by side |
| 9 | H3, StableMut@K | **N/A — out of scope** | Neither ever loads ULT/PLT data (confirmed: zero grep hits for `ult`/`plt` in either script) |
| 10 | Ranking matrix Table 1 | **(a) SYMMETRIC** | Both pooled and L4 views computed and shown as separate lettered columns |
| 11 | Ranking matrix Table 2 | **(b) DELIBERATE ASYMMETRY** | Same pooled convention as #5; disclosed in the generated .md's caption text |
| 12 | `rq5_correlation.png`, `rq5_cross_family_correlation.png`, `collapse_vs_survival.png` | **(b) DELIBERATE ASYMMETRY, disclosed in-figure** | Axis labels/titles state "(pooled)" directly, not just in surrounding prose |
| 13 | `ranking_matrix_heatmap.pdf/.png` | **(c) UNDOCUMENTED ASYMMETRY** | See §3, defect #1 — the figure visualises the same pooled Table 2 data as #11 but the figure itself carries none of that table's disclosure |

**Direct answer to the question the brief anticipated**: RQ5's pooled-Dynamic-vs-ULT lands in **(b)**, not (c) — it is genuinely pre-registered and the tier-composition caveat is genuinely documented in multiple places (`RQ5_DIAGNOSTICS.md`, `RQ5_INTERPRETATION.md`'s "Start here" and "Diagnosis" sections, the pair-naming convention used everywhere in code). It is **not** disclosed at *every* point the pooled number is quoted — the ranking-matrix heatmap figure is a genuine, real gap, and one supervisor-facing document's opening sentence omits it too (§3/§4).

## 3. The reverse check

**Searched for**: any place a Dynamic pooled figure is compared/correlated/ranked/plotted against ULT/PLT without the tier mismatch stated in the same table/figure caption.

**Found, in order of how standalone/extractable the artifact is (most risk first):**

1. **`analysis/figures/ranking_matrix_heatmap.pdf` / `.png` — undisclosed, the clearest defect.** `scripts/plot_ranking_matrix_heatmap.py`'s column labels are `PAIR_LABELS = ["Dynamic\n↔ ULT", "Dynamic\n↔ BigCodeBench", "ULT\n↔ BigCodeBench"]` (L32-33) and the figure's only title text is `"Ranking matrix: cross-benchmark rank agreement by metric"` plus a Holm-Bonferroni significance-marker legend (L106-111). **Nowhere in the figure itself** — not the title, not the axis labels, not a caption — does it state that the "Dynamic ↔ ULT" column is the pooled reading. The companion `analysis/ranking_matrix_heatmap_PROVENANCE.md` is a two-line stub (source CSV + script name) that doesn't restate it either. A reader who encounters this figure on its own (e.g. pasted into a dissertation chapter with its own caption written later, or reviewed by someone who saw the figure before the surrounding prose) has no way to know from the artifact alone. **This is exactly the "reverse error" the brief asked me to look for**, and it's real — every *other* figure checked (`rq5_correlation.png`, `rq5_cross_family_correlation.png`, `collapse_vs_survival.png`, `comparison_c_onset_curve.png`) states "(pooled)" or the specific tier directly in an axis label or legend entry; this is the one that doesn't.

2. **A now-removed dated meeting-summary document's opening framing sentence.** `analysis/RQ5_SUPERVISOR_SUMMARY_20260729.md` (removed 2026-09-02, repository-audience cleanup) read, L17: *"We compared our Dynamic benchmark against ULT (a static benchmark) across 7 models..."* — no "(pooled)" anywhere in this sentence, and it was the document's first substantive claim, plausibly read standalone or shown to someone else without the rest of the project's context. The pooled/L4 distinction was never stated anywhere in that document (checked in full before removal). **Separately** — not part of this audit, flagged only because it was noticed along the way — that document's own numbers (n_models=7 throughout) were already stale at audit time; the 2026-08-07/08 data landing had moved RQ5 canonical to n=9. **Both issues are now moot**: the document no longer exists in the repo to be read standalone or resurfaced. Recorded here, quoted verbatim, so this audit's own finding stays verifiable without the source file.

3. **Coverage-adjusted variants generally** (RQ5 canonical and cross-family): the coverage-adjusted pair (`dynamic_coverage_adj`) is derived from the *same* pooled `dynamic_mutk_pooled` basis as the raw pair, so it inherits the identical tier-composition question. Every place this figure is quoted (`RANKING_MATRIX.md` Table 2, `RQ5_DIAGNOSTICS.md` sec 3b, `RQ5_INTERPRETATION.md`) is inside a document that already establishes the pooled convention earlier on the same page — no standalone-figure or standalone-table instance of the coverage-adjusted number was found lacking disclosure. Not a defect, but worth confirming explicitly since coverage-adjusted numbers are the ones this project's write-up leans on hardest (τ=0.944).

**CC-band machinery check**: `load_cc_bands`/`matched_cc_table` (the CC8-9/10-11/12-15/16+ band system from `subsample_manifest.json`) is used in exactly one place — `build_comparison_tables.py`'s Comparison B matched-CC table — and is applied identically to both ULT and PLT (`band_lookup_ult`, `band_lookup_plt`, `comparison.py` L232-257). Confirmed via `grep -rl "load_cc_bands\|matched_cc"` across `scripts/` and `src/`: no other script imports this machinery. **Dynamic never uses CC-bands at all** (it has its own discrete L1-L4 tier system) — so there is no comparison anywhere mixing "bands on one side, raw tiers on the other." Clean.

## 4. Vocabulary audit

**"Dynamic" denotes at least three populations in this project's own usage**, confirmed by the inventory above: `dynamic_pooled` (all tiers), `dynamic_l4` / `dynamic_L4` (CC-matched), `dynamic_l1l3` / `dynamic_l1l2` (control/headroom, two slightly different slices used in two different Comparison C artifacts — see the inventory note).

**Where the project already disambiguates well** (no action needed):
- Every CSV column name already carries an explicit suffix: `dynamic_l4`, `dynamic_mutk_pooled`, `dynamic_mutk_L1..L4`, `dynamic_coverage_adj` (checked every `analysis/*.csv` header containing "dynamic" — none is a bare, unqualified `dynamic` column).
- Every figure axis label/legend checked except one (`ranking_matrix_heatmap`) states the qualifier directly.
- Every generated `.md` table (RQ5_PROVENANCE.md, RANKING_MATRIX.md, RQ5_DIAGNOSTICS.md, RQ5_CROSS_FAMILY_PROVENANCE.md, COMPARISON_PROVENANCE.md) either uses a self-labelled pair name (`"Dynamic(pooled) <-> ULT"`) or a column header naming the exact tier.

**Where it doesn't** (the concrete list requested):
1. `analysis/figures/ranking_matrix_heatmap.pdf` / `.png` and its `_PROVENANCE.md` stub — no qualifier anywhere in the artifact (§3, defect #1).
2. A now-removed dated meeting-summary document's opening sentence lacked the qualifier — see §3 finding #2 above for the quoted record. Moot: the document was removed 2026-09-02.
3. Flowing prose throughout `RQ5_INTERPRETATION.md`, `METRICS_AND_FINDINGS_EXPLAINED.md`, and `COMPARISON_A_INTERPRETATION.md` uses bare "Dynamic" as shorthand *after* establishing scope in an earlier heading/table on the same page — this is standard, low-risk writing practice for a document read top-to-bottom, not listed as items needing individual fixes (there are dozens of such sentences; enumerating each would be noise, not signal). Flagged as a class, not itemised.

**Proposed naming convention** (documentation/labelling only — no code identifiers renamed, per the brief's instruction):
- **Dynamic-pooled** — all four tiers, all landed instantiations. Use for anything currently written as bare "Dynamic" in a *table header, CSV column, or figure caption* (prose already using it as an established shorthand is lower priority).
- **Dynamic-L4** — the CC≥8-matched slice used for Comparison A and RQ5's L4-only diagnostic row. Already the dominant convention in code (`dynamic_l4`); just needs to be the prose term too, replacing bare "Dynamic-L4" is already fine, no change needed there.
- **Dynamic-L1-L3** (or **Dynamic-L1-L2** where that specific narrower slice is meant, per Comparison C's onset-curve figure) — the non-CC-matched control/headroom arm. Recommend picking **one** of L1-L3 or L1-L2 as Comparison C's standard "control" slice and noting explicitly why the other exists, rather than leaving two similarly-named but different slices both live (see inventory note under Comparison C).

**Where this convention would need applying** (structural artifacts only, per the above):
- `scripts/plot_ranking_matrix_heatmap.py` — `PAIR_LABELS` list and `fig.suptitle` (defect #1, fix recommended in §6).
- Any *future* table header or figure caption that pairs Dynamic against ULT/PLT/BigCodeBench should default to writing "Dynamic-pooled" or "Dynamic-L4" explicitly rather than bare "Dynamic," matching what nearly every existing artifact already does.

## 5. Floor-effect cross-check

| Model | Dynamic-L4 n_total | Dynamic-L4 n_defined | Status | Disclosed where |
|---|---|---|---|---|
| Qwen 2.5-Coder-1.5B-Instruct | 375 | **0** | Genuine floor effect — cannot clear the CC≥8 baseline gate at all | `COMPARISON_A_INTERPRETATION.md` item list; `COMPARISON_PROVENANCE.md`'s missing-models line; `METRICS_AND_FINDINGS_EXPLAINED.md` §3 table |
| Qwen 2.5-Coder-7B-Instruct | 375 | **1** | Thin, not zero — excluded by the n_defined<20 thin-cell filter, included in the raw/unfiltered reading | `COMPARISON_PROVENANCE.md`'s thin-cell audit section; `METRICS_AND_FINDINGS_EXPLAINED.md` §3 |
| **Gemini 3.1 Pro Preview** | 300 | **292** | **Not floor-limited — the brief's stated assumption is stale.** Crawl completed 2026-08-11 (this pass). Now one of the best-covered models at L4, second only to GPT-5. | Not yet reflected in `analysis/METRICS_AND_FINDINGS_EXPLAINED.md`'s Gemini-Pro-L4 section as "fully resolved" (that section was last updated mid-crawl, describing a 38/300 partial state) — **needs a follow-up update, flagged in §6** |

**Where a CC-matched comparison is symmetric in form but empty/thin on one side**: Comparison A's raw/unfiltered reading includes Qwen 7B despite n_defined=1 (a single baseline-passing problem driving that model's entire L4 mean) — this is already disclosed via the thin-cell audit (`COMPARISON_PROVENANCE.md` reports both the 8-model unfiltered and 6-model thick-only readings side by side, explicitly naming Qwen 32B and Qwen 7B as the two excluded from the thick reading). Qwen 1.5B is excluded from Comparison A entirely (not zero-filled) — also disclosed. **No comparison was found reporting a CC-matched result as if it were equally well-powered across all models without also surfacing this n_defined breakdown** — the discipline here is consistently good across every artifact checked.

## 6. Prioritised defect list

**Must fix before the write-up:**

1. **`plot_ranking_matrix_heatmap.py`'s figure has no tier-scope disclosure at all.** Recommend adding "(pooled)" to the `PAIR_LABELS` Dynamic entries and/or a one-line caption/footnote on the figure itself, so it carries its own disclosure independent of the surrounding document. This is a text/label change to a plotting script, not a data or methodology change — outside this audit's read-only scope without explicit sign-off, but it's the one item unambiguous enough to flag as a direct recommendation.
2. **`METRICS_AND_FINDINGS_EXPLAINED.md`'s Gemini-Pro-L4 section is now stale in the *other* direction** — it was already updated once (2026-08-10) to describe a 38/300 partial crawl state; the crawl has since fully completed (292/300, this pass, after that section was last touched). Not a tier-symmetry defect per se, but directly relevant to §5 and worth a follow-up pass so the floor-effect story in that doc matches current reality.

**Disclose in the paper, don't change the pipeline:**

3. **RQ5's pre-registered primary (pooled Dynamic vs ULT) should report the L4-only reading alongside it as a named robustness row wherever the primary number is the headline** — the diagnostics already compute this (`RQ5_DIAGNOSTICS.md` sec 1: pooled τ=0.333 vs L4-only τ=0.000, not even the same sign of *magnitude*, functionally zero information at L4). This is a **recommendation only**, since a pre-registered primary metric is not altered outside the pre-registration process — not applied here. The mechanical change would be small (the L4-only row already exists in `RQ5_DIAGNOSTICS.md`'s own table; it would need surfacing next to the primary number itself, e.g. in `RANKING_MATRIX.md` Table 2 and its heatmap, rather than only in the separate diagnostics doc).
4. ~~A now-removed dated meeting-summary document's opening sentence didn't state "(pooled)"~~ — moot, the document was removed 2026-09-02 (repository-audience cleanup); see §3 finding #2 for the record.
5. Comparison C's two differently-scoped "Dynamic control" slices (`dynamic_l1l3` in the DiD table vs `dynamic_l1l2` in the onset-curve figure) are each internally well-labelled but sit close enough in name to invite confusion on a first read; worth one sentence in the write-up clarifying they're deliberately different artifacts serving different purposes, not an inconsistency.

**Confirmed clean, no action needed:**
- Comparison A/B's tier/CC-band handling (fully symmetric, explicitly documented in code).
- Comparison C's `dynamic_l4` primary control (CC-matched) and `dynamic_l1l3` robustness control (explicitly named, never conflated).
- CC-band machinery (used only for Comparison B, applied identically to both sides, never mixed with raw Dynamic tiers).
- H3 and StableMut@K (out of scope — never touch ULT/PLT).
- Every CSV column name in `analysis/*.csv` referencing Dynamic.
- All figures except the ranking-matrix heatmap.
