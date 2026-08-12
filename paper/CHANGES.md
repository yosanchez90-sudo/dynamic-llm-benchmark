# Hygiene sweep: what changed and why

One-page summary of the conversational-artifact sweep (commit `3bf90d8`,
`chore(hygiene): sweep conversational artifacts from analysis docs and
code`), run as part of this write-up phase's Phase 4 verification pass.

## What it did

Scanned every file under `src/`, `scripts/`, `tests/`, `template_corpus/`
(comments and docstrings), every `analysis/*.md` document,
`PROJECT_BRIEF.md`, `CLAUDE.md`, `README.md`, and `docs/*.md` for
direct-address and first-person narration left over from how these
documents were originally drafted: phrases like "the user", "per your
instruction/decision/framing", "I found/checked/flagged", and "this
session". Each was rewritten into impersonal technical rationale that
preserves every fact and every piece of reasoning -- nothing was deleted
or summarised away, only re-addressed. "This session" became "this pass"
throughout, which is the term these same documents already used natively
in most other places; the two were never meant to mean different things,
just written inconsistently over time.

13 files changed: 12 `analysis/*.md` documents and one code comment
(`template_corpus/templates/_smoke/validate.py`, an inline rationale for
why only `TypeError` is treated as a validation failure). No file's
factual content, verdict, or recommendation changed -- every edit is a
substitution of address, not of substance.

## What it did not touch, and why

- **Git history.** Commit messages and diffs from before this sweep are
  left exactly as written. The instruction governing this sweep was
  explicit: rewrite going forward, do not rewrite the record of what
  already happened.
- **Every `Claude`/`assistant` string in the codebase.** Checked
  individually, not assumed: every remaining instance is a legitimate
  technical reference -- the Claude Sonnet/Haiku models this study
  evaluates, or the standard LLM chat-API `"role": "assistant"` field
  used throughout `src/models/`, `src/data/test_gen.py`, and the
  fine-tuning data-prep scripts. None of these refer to an AI assistant
  helping write the code, so none needed rewriting.

## Verification (all three required before commit, per the sweep's own
## governing instruction)

| Check | Result |
|---|---|
| Full test suite | 152 passed, 0 failed |
| Full asset pipeline (`scripts/build_thesis_assets.py`, all 20 steps) | All `OK`; output differs from the pre-sweep committed state only in each file's own `Git commit: <hash>` provenance stamp, never in a computed value |
| Citation gate (`scripts/check_doc_citations.py`) | PASS -- 414 match, 0 mismatch, 0 hand-typed, both before and after |

The pipeline-regeneration stamp churn itself (17 files, `Git commit:`
line only) was reverted rather than committed, to keep the sweep commit
isolated to its actual content per the same governing instruction --
re-running `scripts/build_thesis_assets.py` any time will refresh those
stamps to the current `HEAD` on its own.
