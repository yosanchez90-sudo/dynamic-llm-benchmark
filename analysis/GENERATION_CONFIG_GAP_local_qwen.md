# Unlogged inherited generation params — local Qwen models (all runs to date)

Found during a pre-spend audit (2026-07-14) prompted by the earlier
`no_repeat_ngram_size` collapse (`analysis/README_QUARANTINE.md`) — checking
whether the same *class* of bug (an unlogged default silently inherited
from somewhere outside this project's YAML configs) was present anywhere
else before spending more on the API-model backfill.

## What was found

`src/models/local.py`'s `generate()` passed `max_new_tokens`, `do_sample`,
`temperature`, `top_p` to `model.generate()`, but never set
`repetition_penalty` or `top_k`. HuggingFace's `generate()` resolves any
unset parameter from the checkpoint's own bundled `generation_config.json`
— which for every Qwen2.5-Coder checkpoint used in this project sets:

| Checkpoint | `repetition_penalty` | `top_k` |
|---|---|---|
| Qwen2.5-Coder-1.5B-Instruct | 1.1 | 20 |
| Qwen2.5-Coder-7B-Instruct | 1.1 | 20 |
| Qwen2.5-Coder-32B-Instruct | 1.05 | 20 |

Neither value was ever logged in any result row's `generation_config`
field, and neither is part of this project's documented methodology
(`PROJECT_BRIEF.md` 5.4 only pins temperature and max output tokens).

## This is NOT the no_repeat_ngram_size bug

Important distinction, checked explicitly: none of the cached
`generation_config.json` files contain a `no_repeat_ngram_size` key at
all, and `src/models/local.py` never set one. The specific setting that
fabricated the epoch-curve collapse was never present in this file. This
is a *different* instance of the same failure class (unlogged inherited
default), not a recurrence of the same bug.

## Is existing data affected / does it need to be discarded?

No evidence of corruption, and no action needed on existing files:

- These values (1.1/1.05, 20) come from the checkpoint files themselves,
  which have not changed since first downloaded (pinned by revision SHA in
  every config) — so the *same* repetition_penalty/top_k has been in effect
  identically across every local Qwen run this project has ever done,
  from the June pilot through today's L1/L2 x inst1-3 baseline and today's
  L3/L4 + inst4-5 backfill. There is no before/after split the way the
  ngram bug had (healthy vs. contaminated files) — it's been constant.
- exec_rate distributions across all existing Qwen results, checked per
  model x tier as part of this audit:

  | Model | L1 | L2 | L3 | L4 |
  |---|---|---|---|---|
  | 1.5B | 0.931 | 0.912 | 0.752 | 0.584 |
  | 7B | 0.997 | 0.997 | 0.989 | 1.000 |
  | 32B | 1.000 | 1.000 | (no L3/L4 data yet) | |

  1.5B degrades gradually by tier (93%→58%), which is consistent with a
  small model genuinely struggling more on harder problems (L4 =
  compositional, nested branches+loops) — not a collapse pattern. If
  `repetition_penalty` were corrupting output the way `no_repeat_ngram_size`
  did, it should degrade all three sizes comparably, not leave 7B and 32B
  at ~99-100% while only the smallest model drops on the hardest tier. No
  sudden cliff anywhere (contrast with the ngram bug's near-0% collapse).
- The values themselves (repetition_penalty 1.05-1.1, top_k 20) are mild,
  standard sampling settings, not the kind of aggressive constraint
  (no_repeat_ngram_size=4 over the full prompt+response) that fabricated
  the earlier collapse.

## What changed

`src/models/local.py` now explicitly reads `self.model.generation_config`
for `repetition_penalty`/`top_k`, passes them explicitly to `generate()`
(pinning the value in code rather than leaving it implicitly dependent on
whatever happens to be cached in `HF_HOME`), and logs both values plus
`repetition_penalty_source`/`top_k_source: "checkpoint_generation_config"`
into every record's `generation_config` field going forward. This is a
**logging and pinning fix, not a behavior change** — the actual sampling
behavior is unchanged from every prior run.

Rows written before this fix (all Qwen local data collected before
2026-07-14) simply don't have `repetition_penalty`/`top_k` keys in their
`generation_config` — treat their absence as "1.1 (or 1.05 for 32B) / 20,
undocumented" per the table above, not as missing/unknown.
