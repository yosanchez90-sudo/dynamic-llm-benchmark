# OpenAI GPT-5 / GPT-5-mini batch submission — pre-flight GO/NO-GO

Written 2026-08-05. **No batch was submitted and no money was spent
producing this document.** This is the Part 2 pre-flight check called for
after `analysis/OPENAI_COST_AND_BILLING.md` (Part 1's cost/billing
investigation) — read that first for the cost figures this references.

## Checklist

### 1. Corpus-drift check — CLEAN, no drift detected

Two independent lines of evidence, both clean:

**(a) Nothing touched.** No L1-L4 template `.py` file and no
`data/raw/ult_plt/subsample_manifest.json` has an mtime newer than the
oldest prepared batch file (`batch_input_20260713T124543.jsonl`, 2026-07-13).
`git log --since=2026-07-13` on these paths shows only smoke-test/validation
helper commits (`template_corpus/templates/_smoke/*`, unrelated to actual
templates) and one commit (`415a4ac`) that force-added
`subsample_manifest.json` to git tracking with **zero content changes**
(19,718 insertions, 0 deletions — a pure add of an already-existing,
already-generated file, not an edit).

**(b) Byte-for-byte reconstruction, sampled across every batch.** Rebuilt
prompts directly from the current corpus/manifest (bypassing mutant
generation, which is irrelevant to prompt content and expensive enough on
ULT/PLT's real-world functions that running it at full scale on the login
node would itself violate CLAUDE.md's SLURM-only compute rule) and diffed
against the exact `messages` array stored in each prepared batch request:

| Batch | Sampled | Result |
|---|---|---|
| Backfill (2,400 req) | 160 (5 per each of 32 config×tier groups) | 100% byte-identical |
| Retry (7 req) | 7 (all of them) | 100% byte-identical |
| ULT/PLT core_400 (1,600 req) | 20 (5 per each of 4 benchmark×model groups) | 100% byte-identical |

**Conclusion: no drift. Safe to proceed on this check.**

### 2. Anti-double-pay — CLEAN, zero duplicates

Cross-checked every one of the 4,007 requests' natural key
(`model_id, benchmark, instantiation_id, template_id, instance_seed, tier,
K, prompting_condition`) against all 593 already-landed GPT-5/-mini rows on
disk (294 gpt-5 + 299 gpt-5-mini, across `data/results/{dynamic,ult,plt}/`).
**0 of 4,007 requests would duplicate an already-scored cell.** This is
also structurally expected — these are exactly the cells
`scripts/coverage_matrix.py` reports as missing — but was verified directly
against real landed rows rather than only trusted transitively.

### 3. Ingestion readiness — CONFIRMED

- **Tier-aware resume-matcher fix**: doesn't apply to the batch path at
  all, by construction, not merely "covered." `_find_resume_file` /
  `_tier_signature` (the fix CLAUDE.md documents) are called only from
  `test_gen_runner.py::run_test_gen_experiment`, the live/interactive eval
  path — grepped, `process_batch.py` never calls either. Each batch (or
  future chunk) gets a uniquely-timestamped output filename keyed on its
  own state file's `created_at`
  (`process_batch.py:236-239`), so there is no glob/resume-file-lookup step
  on the batch path for the tier-signature collision bug to affect.
- **Error-shape handling (400/500/503-with-body)**: already implemented
  and exercised, `process_batch.py:138-148`. The code's own comment states
  the three failure shapes explicitly (top-level `error`, empty response
  body, populated body with an OpenAI error object instead of `choices`)
  and a failing row is logged and `continue`d past — it does not abort the
  batch and does not fabricate a fake successful record.
- **Dry-run reconstruction**: 100% pass across all three prepared state
  files (2,400 + 7 + 1,600 = 4,007 requests). For every request: required
  metadata fields present and non-null, 1:1 coverage between the input
  JSONL's `custom_id`s and the state file's request metadata (no orphans
  either direction), no duplicate `custom_id`s, and `compute_model_label()`
  + output-path construction succeed without exception for every single
  request, resolving to 14 distinct, non-colliding `(output_dir, filename)`
  targets total across the three batches.

### 4. Snapshot liveness — CONFIRMED

Both `gpt-5-2025-08-07` (`developers.openai.com/api/docs/models/gpt-5`) and
`gpt-5-mini-2025-08-07` (`developers.openai.com/api/docs/models/gpt-5-mini`)
have live, current, directly-fetched model pages as of 2026-08-05, each
naming the exact pinned snapshot string this project uses, each shown as
the family's current/default snapshot with an active (non-deprecated)
pricing table. No indication either has been retired or superseded.

## 5. Final cost figure (from Part 1, restated here)

**Mid-estimate ~$51, plausible range $39-$60**, at corrected current Batch
API pricing — see `analysis/OPENAI_COST_AND_BILLING.md` §3 for the full
per-batch breakdown and methodology (exact `tiktoken` input counts, p25/
mean/p75 output-token band from real inst1 usage). This is lower than the
~$81 previously circulated, primarily because `src/pricing.py` had gpt-5/
-mini mislabeled at a pricier sibling model's rate (fixed this pass).
**Recommendation: fund at least $65-70 to leave headroom above the high
estimate.**

## 6. Setup still required before submission (none of this has been done)

From `analysis/OPENAI_COST_AND_BILLING.md` §4-5, restated as the action list:

1. Prepaid credit top-up ($65-70 recommended; $5 minimum, $10 default
   per OpenAI's own prepaid-billing docs).
2. Organization verification for `gpt-5`-class model access (government ID
   + selfie flow; allow well over the documented "~15 min propagation" for
   the verification itself to complete, not just propagate).
3. Confirm `OPENAI_API_KEY` is set and picked up.
4. **Chunking**: plan for splitting the two gpt-5 batches (backfill,
   ULT/PLT) into ~14 and ~9 sub-batches respectively under the conservative
   (reserved-capacity) reading of the Tier-1 batch queue limit — genuinely
   unresolved which of two readings (input-only vs. input+reserved-output)
   OpenAI applies; see §5 of the cost doc. gpt-5-mini needs only 3 and 2
   chunks respectively, well within its higher (5M) limit either way. This
   chunking has **not been built** in this pass (no submission happens in
   this pass) — the boundaries are specified and ready to apply.
5. `create_batch.py` is ready: default (no flag) writes files only; pass
   `--submit` to actually upload and submit, once everything above is done.

## GO / NO-GO

**Every pre-flight check in this document passed clean.** Nothing found in
Parts 1 or 2 blocks submission on technical or data-integrity grounds — no
corpus drift, no double-pay risk, ingestion path verified end-to-end,
snapshots confirmed live, cost is bounded and (once the pricing-table bug
fix lands) noticeably cheaper than previously thought.

**The remaining gate is not technical — it's the one the user set
explicitly: credits must be topped up and explicit go-ahead given before
anything is submitted.**

**STOP HERE.** No batch has been submitted, no file has been uploaded to
OpenAI, and no money has been spent at any point in this pass. Submission
requires: (1) the setup steps in §6 above, then (2) either
`python scripts/create_batch.py <configs> --submit` (uploads and submits
for real — the explicit opt-in, safe-by-default as of this pass) or the
manual upload/create flow in `SUPERVISOR_HANDOFF_SUBMIT_ALL.md` — only
after the user's explicit go-ahead.
