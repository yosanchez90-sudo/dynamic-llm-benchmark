# Citation allowlist

Suppresses specific `scripts/check_doc_citations.py` findings that are
legitimate, not stale citations. Companion mechanism to the inline
`<!-- cite:historical -->` / `<!-- cite:external -->` markers (see that
script's module docstring) — use this file when an inline marker would be
awkward (a value buried in dense prose, or a value the checker can't
verify for a structural reason rather than genuine staleness).

Matched on file (basename) + line (±3 tolerance, survives small nearby
edits) + kind + value (same tolerance the checker itself uses). If an
entry stops matching after a larger edit, the finding reappears — re-add
or update the entry rather than assuming it's still covered.

**Category key** (recorded per-entry in the reason column, per the
2026-08-12 reconciliation pass that classified every finding at the time
this table was created):
- **historical** — a deliberately-cited superseded value inside a
  correction history, movement table, or "was X, now Y" construction.
- **verified-current** — a live, correct fact the checker cannot confirm
  because of a structural extraction gap (documented per-entry), not
  because the document is wrong. Re-verify the underlying number directly
  if this entry is ever questioned, rather than trusting the allowlist
  entry itself as proof.
- **definitional** — an illustrative example in a glossary/notation
  table, not a claim about any specific real result.

| file | line | kind | value | reason |
|---|---|---|---|---|
| COMPARISON_A_INTERPRETATION.md | 14 | n_models | 5 | historical — "growing this comparison from n_models=5 to n_models=8" |
| COMPARISON_A_INTERPRETATION.md | 81 | n_models | 5 | historical — same "grew from 5 to 8" construction |
| RQ5_INTERPRETATION.md | 93 | kendall_tau | 0.143 | historical — "2026-08-07 from the original tau=0.143" |
| RQ5_INTERPRETATION.md | 136 | spearman_rho | 0.35 | historical — inside the explicitly-labelled "2026-08-07 reading (historical)" paragraph |
| RQ5_INTERPRETATION.md | 137 | kendall_tau | 0.143 | historical — "originally reported was Kendall tau=0.143" |
| RQ5_INTERPRETATION.md | 154 | pp | 3.5 | verified-current — recomputed directly from rq5_model_ranking.csv (dynamic_mutk_pooled range across the 8 non-Qwen-1.5B models = 3.52pp); the "pp" reference corpus only tags Comparison C's DiD gain/did columns, not RQ5's score-spread prose |
| RQ5_INTERPRETATION.md | 155 | pp | 4.4 | historical — "corrected 2026-08-12 from a stale 4.4pp" |
| RQ5_INTERPRETATION.md | 156 | pp | 14.5 | verified-current — recomputed directly from rq5_model_ranking.csv (ult_mutk range across the same 8 models = 14.51pp); same pp-scope gap as the entry above |
| RQ5_INTERPRETATION.md | 207 | kendall_tau | 0.143 | historical — inside the "2026-08-07 reading (historical)" paragraph for Diagnosis (a) |
| RQ5_INTERPRETATION.md | 218 | kendall_tau | 0.0 | historical — same paragraph, the pre-2026-08-12 tier-matched reading |
| RQ5_INTERPRETATION.md | 220 | kendall_tau | -0.2 | historical — "the negative tau=-0.200 the earlier n=5 reading showed" |
| RQ5_INTERPRETATION.md | 292 | n_models | 5 | historical — "no longer just an n_models=5 lead" |
| RQ5_INTERPRETATION.md | 320 | kendall_tau | 0.143 | historical — full movement chain "tau=0.143->0.333->0.278", 0.143 is the oldest link |
| RQ5_INTERPRETATION.md | 411 | n_models | 13 | verified-current — RQ5_CROSS_FAMILY_PROVENANCE.md's own canonical+cross-family scope is n=13; the checker doesn't map bare "n" table columns to n_models by design (see COLUMN_KIND_MAP comment), so this can never auto-verify |
| RQ5_INTERPRETATION.md | 732 | n_models | 13 | verified-current — same n=13 cross-family scope, same structural gap as above |
| RQ5_INTERPRETATION.md | 733 | n_models | 11 | historical — "was n_models=11/7", the pre-2026-08-07 cross-family scope |
| STABILITY_INTERPRETATION.md | 98 | n_models | 5 | historical — describes the pre-2026-08-07 inst5-pair composition ("jump from n_models=5 (Qwen x3 + ...") |
| STABILITY_INTERPRETATION.md | 228 | kendall_tau | 0.569 | verified-current — STABILITY.md's own "All-pairs mean pairwise tau (incl. instantiation 5): 0.569" line; the checker's kendall_tau prose pattern requires "kendall tau" or literal "tau" adjacent to "kendall", not bare "tau" alone, so this specific phrasing can't auto-verify |
| H3_INTERPRETATION.md | 87 | spearman_rho | -0.387 | verified-current — H3_TIER_GRADIENT_PROVENANCE.md's live all-tier pooled rho is -0.38680577952650025, which rounds to -0.387; the checker's nearest reference match is a different (per-model) row's rho, a coincidentally-close false lead, not the real source |
| H3_INTERPRETATION.md | 88 | spearman_rho | -0.392 | historical — "corrected 2026-08-12 from a stale rho=-0.392/n=6,547" |
| H3_INTERPRETATION.md | 90 | spearman_rho | -0.351 | verified-current — H3_TIER_GRADIENT_PROVENANCE.md's live L2-L4 pooled rho is -0.3506948706611829, which rounds to -0.351; same false-lead issue as line 87 |
| H3_INTERPRETATION.md | 91 | spearman_rho | -0.361 | historical — "corrected from rho=-0.361/n=4,925" |
| HYPOTHESIS_DEVIATIONS.md | 235 | pp | 0.5 | verified-current — GPT-5's L1->L2 rebound, 0.985487->0.990774 = +0.5287pp, rounds to 0.5pp; H3's per-tier score deltas were never in scope for the "pp" reference corpus (that's DiD gain columns only) |
| HYPOTHESIS_DEVIATIONS.md | 235 | pp | 0.8 | verified-current — GPT-5-mini's L1->L2 rebound, 0.982875->0.990388 = +0.7513pp, rounds to 0.8pp; same scope gap as above |
| OPEN_ITEMS.md | 43 | kendall_tau | 0.569 | verified-current — same bare-"tau" phrasing gap as STABILITY_INTERPRETATION.md:228 |
| OPEN_ITEMS.md | 54 | n_models | 5 | historical — "grew this from n_models=5 to n_models=9" |
| OPEN_ITEMS.md | 79 | n_models | 5 | historical — "grew from n_models=5 to n_models=8" |
| OPEN_ITEMS.md | 80 | kendall_tau | 0.143 | historical — "tau 0.143->0.333", already annotated in the same sentence as superseded by the 2026-08-12 correction to 0.278 |
| METRICS_AND_FINDINGS_EXPLAINED.md | 542 | n_defined | 112 | definitional — notation-glossary illustrative example ("n_defined=112 of n_problems=400"), not a claim about a specific real result |
| METRICS_AND_FINDINGS_EXPLAINED.md | 654 | n_models | 1 | verified-current — Comparison C is a single fine-tuned model by design; the n_models reference corpus is built only from cross-model comparison tables, so a single-model count is structurally out of its scope |
| METRICS_AND_FINDINGS_EXPLAINED.md | 824 | n_models | 5 | historical — "which grew Comparison A from n_models=5 to n_models=8" |
| METRICS_AND_FINDINGS_EXPLAINED.md | 969 | n_models | 1 | verified-current — same single-fine-tuned-model case as line 654 |
| METRICS_AND_FINDINGS_EXPLAINED.md | 993 | kendall_tau | 0.143 | historical — "2026-08-07 from tau=0.143 to tau=0.333", already updated in the same sentence to name the 2026-08-12 tau=0.278 correction |
| METRICS_AND_FINDINGS_EXPLAINED.md | 1035 | n_models | 13 | verified-current — same cross-family n=13 structural gap as RQ5_INTERPRETATION.md:411 |
| METRICS_AND_FINDINGS_EXPLAINED.md | 1084 | kendall_tau | 0.143 | historical — findings-ledger table row describing a specific, dated, past-tense diagnostic finding ("was found to ... flip its sign") |
| METRICS_AND_FINDINGS_EXPLAINED.md | 1084 | kendall_tau | -0.2 | historical — same findings-ledger table row |
| METRICS_AND_FINDINGS_EXPLAINED.md | 1084 | n_models | 5 | historical — same findings-ledger table row, the n=5-scope diagnostic reading it describes |
