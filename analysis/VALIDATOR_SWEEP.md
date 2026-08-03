# Validator sweep — every check/audit/validate script in the repo

Prompted by two already-fixed bugs of the same shape (`validate.py`'s
stale path silently validating zero templates; `validate_cc.py`'s
hardcoded `"Total: 60, Failed: 0"`, both fixed commit `2d5fc9d`,
2026-07-13) — this is a full audit of every validation-class script in
the repo for the same failure family: hardcoded pass counts, silently-
skipped loops, empty populations read as success, and library fallbacks
that approximate instead of raising. 13 scripts examined in full; two new
issues found and fixed (below); one already-known issue's still-live code
path also fixed; a shared guard module added to prevent recurrence.

## Method

Every script under the repo (excluding `.venv`) named `validate*`,
`check_*`, `audit_*`, `verify_*`, or `*sweep*`, plus `residual_scan.py`
(same class by function, different name). 13 in-repo scripts qualify;
everything else matching those patterns lives under `.venv/` (third-party
libraries) and is out of scope.

## Findings

| # | Script | Pattern found | Status |
|---|---|---|---|
| 1 | `template_corpus/templates/_smoke/validate.py` | Hardcoded/silent-skip: stale `TEMPLATES_ROOT` made every tier directory fail `.exists()`, so the loop silently validated 0 templates while still printing as if it had run. | **Already fixed**, commit `2d5fc9d` (2026-07-13). |
| 2 | `template_corpus/templates/_smoke/validate_cc.py` | Hardcoded total: printed literal `"Total: 60, Failed: 0"` regardless of what actually ran. | **Already fixed**, commit `2d5fc9d`. |
| 3 | `template_corpus/templates/_smoke/mutation_sweep.py` | Not a bug in its own logic — but its narrow scope (60 Dynamic templates only, ONE hardcoded seed=42 per template, checked against a band the author set from a single spot-check measurement) was being cited/relied on more broadly than it can support. Full explanation: `analysis/MUTANT_COUNT_SPEC_AUDIT.md`. | **Disclosed**, not a code fix — the script does exactly what it's designed to do; the gap was in how its result was described downstream (see #9). |
| 4 | `template_corpus/templates/_smoke/diversity_v2.py` | Library-fallback: silently substituted a 4-gram Jaccard approximation for real BLEU-4 whenever `sacrebleu` wasn't importable (it was never a declared dependency until commit `d16f122`, 2026-07-14) — only a `print()` line, not an exception or a persisted output field, distinguished which metric had run. Every diversity run before that commit used the approximation. | **Fixed 2026-08-03**: `sacrebleu` import now goes through `validation_helpers.require_library()`, which raises `ImportError` instead of falling back; the `_bleu4_fallback()` function and `HAVE_SACREBLEU` flag are removed entirely. |
| 5 | `template_corpus/templates/_smoke/residual_scan.py` | Same latent shape as #1 (a `tier.exists()` / non-empty-glob guard could silently skip a tier with zero templates scanned, printing a clean "0 warnings" that would be indistinguishable from a genuine clean run) — **not currently triggered**: all 4 tier directories are fully populated (15 templates each). | **Hardened 2026-08-03**: added `validation_helpers.assert_checked(n_templates_scanned, ...)` so a future empty-tier regression fails loudly instead of silently. |
| 6 | `template_corpus/templates/_smoke/test_grammar.py` | None — genuine unit tests with real run-and-compare assertions, correct exit code. Separately, this file is also the subject of a pytest-collection bug (§ elsewhere) unrelated to its own validation logic. | Clean. |
| 7 | `scripts/archive_diversity_audit.py` | Hardcoded totals in generated prose: `main()` correctly *computes* real per-tier CSVs from `diversity_v2.json`/`mutation_density.json`, but the human-readable `README.md` it also writes hardcoded every pass/fail number as literal text (`"60/60 pass"`, `"0/60 templates flagged"`, `"L1 7.7, L2 13.4..."`) instead of reading them from the data it had just loaded. Confirmed this is very likely the literal origin of the "60/60 templates land inside their declared per-template stability band" sentence that propagated into other write-ups — currently correct by coincidence (manually transcribed from a real 2026-07-14 run), not by verification; would silently go stale on any future corpus/template/mutator change. | **Fixed 2026-08-03** (bug #9, error ledger): README prose now computed from the loaded JSON on every run, `validate.py`/`validate_cc.py` are re-invoked fresh and their real stdout parsed (`_run_validator()`) instead of asserting numbers from an unrelated SLURM job, and `assert_checked()` guards both loaded JSON populations. A scope note about `mutation_sweep.py`'s single-seed/Dynamic-only coverage (finding #3) is now printed directly into the generated README so the "60/60" claim can't be read as covering ULT/PLT or the multi-seed eval population. |
| 8 | `scripts/audit_result_integrity.py` | None found. Computes real parse-error/duplicate-key/content-conflict counts directly from JSONL files; prints `"(no duplicate triples)"` only when the computed list is actually empty; reports `Files: {len(...)}` so an empty directory would show as `Files: 0`, not be disguised as success. | Clean. |
| 9 | `scripts/audit_unseen_ult_vs_plt.py` | None found — a positive counter-example. Its `_mean()`/`_mannwhitney_u()` helpers (from `scripts/build_comparison_c_seen_manifest.py`) explicitly filter `None`s and return `None` (not a fabricated number) on empty input; rate computations would raise `ZeroDivisionError` (a loud crash) rather than silently reporting a misleading rate on an empty population. | Clean — cite as the right pattern. |
| 10 | `scripts/check_gpu.py` | None — trivial hardware check, no aggregation, explicit `sys.exit(1)` with an `"ERROR: no CUDA"` message on failure. | Clean / not applicable. |
| 11 | `scripts/check_ult_ground_truth_baseline.py` | None found, with a design note: `n_checked`/`n_all_pass` are incremented from real per-record subprocess execution; percentages computed as `100*n_all_pass/n_checked`, which would raise `ZeroDivisionError` (loud crash, correct failure mode) rather than a misleading "0/0" success if the checked population were ever empty — just lacks an explicit `assert n_checked > 0` the way item 12 has. | Clean (implicit guard via crash, not an explicit assertion). |
| 12 | `scripts/verify_finetune_readiness.py` | None — a second positive counter-example. Contains `assert checked > 0, "no overlap between training set and PRE eval file -- can't verify anything"` — the author explicitly anticipated the empty-population failure mode and guarded against it directly. | Clean — cite as the right pattern; this is exactly what `validation_helpers.assert_checked()` generalises. |
| 13 | `scripts/verify_ult_adapter.py` | None — a diagnostic/inspection script (loads an adapter, runs one generation, prints the result) with no pass/fail aggregation to falsely claim success about. | Clean / not applicable. |

## What this adds up to

Of 13 validator-class scripts: **2 already-fixed bugs** (found before this
sweep), **1 still-live bug newly found and fixed** (#7 — error ledger bug
#9), **1 already-known bug's still-live code path fixed** (#4's fallback
logic, previously "fixed" only in the sense that the real dependency was
added, but the silent-approximation escape hatch itself was left in
place), **1 latent-but-not-yet-triggered risk hardened pre-emptively**
(#5), **1 scope/disclosure gap** rather than a code bug (#3), and **7
genuinely clean scripts, two of which are worth citing as the correct
pattern** (#9, #12 — explicit empty-population guards, one via a raised
exception, one via a direct assertion). No new hardcoded-total or
silently-skipped-loop bugs were found beyond what's listed above.

## The shared guard added

`template_corpus/templates/_smoke/validation_helpers.py`, two functions:

- **`assert_checked(n, what)`** — raises `AssertionError` if `n == 0`.
  Call immediately after a validation population's size is known, before
  printing or trusting any pass/fail count derived from it. Applied to
  `archive_diversity_audit.py` (#7) and `residual_scan.py` (#5) in this
  pass; proposed (not yet applied, since they're currently clean) for
  `validate.py`/`validate_cc.py`/`mutation_sweep.py` as defence-in-depth
  should their own population-discovery logic ever regress.
- **`require_library(module_name, purpose)`** — imports `module_name` or
  raises `ImportError` with an explicit message, instead of the
  `try/except ImportError: HAVE_X = False` pattern that enables a silent
  fallback. Applied to `diversity_v2.py`'s `sacrebleu` import (#4).

CLAUDE.md's "Hard rules" now states this as a standing rule ("library
fallbacks must raise, not approximate"), so future validator/metric code
in this project has a documented default to follow rather than
re-deriving the same fix a third time.
