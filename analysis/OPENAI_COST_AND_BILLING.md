# OpenAI GPT-5 / GPT-5-mini — cost, billing, and submission readiness

Written 2026-08-05, self-fund prep pass. **No batch was submitted and no
money was spent producing this document** — every number below comes from
(a) the three already-prepared, unsubmitted `batch_input_*.jsonl` files on
disk, (b) real logged usage from GPT-5/-mini's inst1 runs, and (c) OpenAI's
live public pricing/docs pages, fetched directly (curl) and cross-checked
against a second, independent fetch — not fetched once and trusted, and not
recalled from training data. See `analysis/SUPERVISOR_HANDOFF_20260714.md`,
`analysis/SUPERVISOR_HANDOFF_ULT_PLT_20260713.md`, and
`analysis/SUPERVISOR_HANDOFF_SUBMIT_ALL.md` for the original (now partially
superseded — see §1 below) handoff docs this reconciles against.

## 1. What's actually still needed — reconciled against the coverage matrix

Three batch input files, all still unsubmitted, all still on disk, all still
matching the live gap enumeration:

| Batch | File | Requests | Covers |
|---|---|---|---|
| Backfill | `data/batches/batch_input_20260714T131617.jsonl` | 2,400 | Missing gpt-5/gpt-5-mini cells: instantiations 2-5 × L1-L4, zero-shot, K=1 |
| Retry | `data/batches/batch_input_20260714T131346.jsonl` | 7 | 6× gpt-5 transient 503s + 1× gpt-5-mini reclassified `invalid_prompt`, from the original L3/L4 inst1 batch (`analysis/EXCLUSIONS.md`) |
| ULT/PLT `core_400` | `data/batches/batch_input_20260713T124543.jsonl` | 1,600 | gpt-5/gpt-5-mini's half of Comparison A/B, both benchmarks, all `tier="L4"` |
| **Total** | | **4,007** | |

**Re-verified 2026-08-05 against `scripts/coverage_matrix.py`'s live gap
count** (`scripts/estimate_cost.py`'s own gap enumeration, run fresh today):
gpt-5 is missing exactly **1,206** problems across L1-L4/inst2-5 (300 + 300 +
301 + 305) and gpt-5-mini exactly **1,201** (300 + 300 + 300 + 301) —
1,206 + 1,201 = 2,407 = 2,400 (backfill) + 7 (retry), **exactly matching**
the two prepared files' combined size. **Nothing has landed and nothing has
drifted in scope since these batches were prepared on 2026-07-13/14** — the
gap today is byte-for-byte the same shape it was three weeks ago. (This is
also useful context for Part 2's corpus-drift check: the *count* of what's
missing hasn't moved at all; §5 there still needs to check prompt *content*
hasn't moved either.)

## 2. A pricing bug was found and fixed — this changes the total

`src/pricing.py`'s `PRICING` table had `gpt-5-2025-08-07` at
`(2.50, 15.00)` USD/1M tokens and `gpt-5-mini-2025-08-07` at
`(0.75, 4.50)`, both commented `"GPT-5.4 (project alias)"`. **These are
wrong.** Verified directly, myself, today (not just via the research
sub-agent, since this feeds a real dollar figure and a code change):

- `curl -sL https://developers.openai.com/api/docs/pricing` — the page's own
  embedded pricing-table JSON lists `"gpt-5"` and `"gpt-5.4"` as two
  **different, separately-priced** rows: `gpt-5` standard =
  `$1.25 / $0.125 cached / $10.00`; `gpt-5.4` standard =
  `$2.50 / $0.25 cached / $15.00` — exactly the numbers that were sitting in
  `src/pricing.py` under the `gpt-5-2025-08-07` key.
- `curl -sL https://developers.openai.com/api/docs/models/gpt-5` — this
  snapshot's **own model page** directly names `gpt-5-2025-08-07` and shows,
  in its own pricing widget: Input `$1.25`, Cached input `$0.125`, Output
  `$10.00` — the `gpt-5` family rate, not `gpt-5.4`'s.
- Same check for `gpt-5-mini-2025-08-07` on
  `https://developers.openai.com/api/docs/models/gpt-5-mini`: `$0.25` /
  `$0.025` / `$2.00`.
- Batch API price on both model pages, and independently on the pricing
  page's second embedded table, confirmed at exactly 50% of the above on
  both input and output, matching the Batch guide's and Help Center FAQ's
  stated "50% lower cost" language
  (`https://developers.openai.com/api/docs/guides/batch`,
  `https://help.openai.com/en/articles/9197833-batch-api-faq`).

So this project's actual pinned snapshot (`gpt-5-2025-08-07`, the only
string ever sent as `model` in any request this project makes — grepped,
`"gpt-5.4"` is never sent as a literal model ID anywhere in the codebase)
bills at the **cheaper** `gpt-5` family rate, not the pricier `gpt-5.4` rate
someone mislabeled it with. `src/pricing.py` is fixed (this pass) to
`gpt-5-2025-08-07: (1.25, 10.00)` / `gpt-5-mini-2025-08-07: (0.25, 2.00)`,
with the dead, never-used `"gpt-5.4"` / `"gpt-5.4-mini"` alias keys removed
rather than also fixed in place, since keeping a demonstrably-wrong alias
around only invites the same mix-up again.

**This does not just affect the pending estimate.** Every already-landed
GPT-5/-mini row's `cost_usd` field (`scripts/process_batch.py:211`, via
`compute_cost()`) was computed at ingestion time using the old, wrong table
— so every historical `cost_usd` on disk for these two models is
overstated by roughly 1.5-2x relative to what was actually billed. This is
a bookkeeping/provenance note, not a scientific-validity issue (no scored
metric depends on `cost_usd`), and it is **not corrected retroactively** in
the stored rows — `cost_usd` is a logged-at-the-time field, and
silently rewriting historical log values would itself be the kind of
undisclosed correction this project's provenance culture avoids. Flagging
here as the disclosure; `scripts/estimate_cost.py`'s "prefer real logged
`cost_usd` over a token proxy" logic (correct in general — real billed
dollars beat any proxy) is therefore **not used** for the fresh estimate
below; it's recomputed directly from token counts and the corrected table
instead, exactly what would happen automatically for any *future* row now
that the table itself is fixed.

## 3. Cost estimate — exact input tokens, real output-token band, corrected pricing

**Input tokens**: counted **exactly** via `tiktoken`, `o200k_base` encoding
(tiktoken's own `encoding_for_model()` mapping for `gpt-5`/`gpt-5-mini`,
confirmed directly, not assumed), applying OpenAI's standard chat-format
token-counting formula (3 tokens overhead/message + role/content token
counts + 3 for reply priming) directly against every request body in the
three real `batch_input_*.jsonl` files — not a proxy, not an average pulled
from a different benchmark's rows.

**Output tokens**: no real output exists yet for any of these 4,007
requests (that's the entire reason to run them), so, per the pre-registered
approach, this uses GPT-5/-mini's own real measured `runtime_info.output_tokens`
from their existing inst1 rows, broken out **per tier** (for the Dynamic
backfill/retry batches) or **as the L4-equivalent** (for ULT/PLT, whose
CC≥8 problems occupy the same band as Dynamic's L4 — consistent with the
H4/RQ3 closure's finding that L4 is the CC band closest to ULT/PLT, §4 of
`analysis/H4_DESIGN_MEMO.md`). Reported as a **p25 / mean / p75 band**
(not just a mean) over n=70-75 real rows per (model, tier) cell, so the
"high" estimate reflects real observed variance, not a hand-picked margin:

| Model | Tier | n (real) | p25 out tok | mean out tok | p75 out tok |
|---|---|---|---|---|---|
| gpt-5-2025-08-07 | L1 | 75 | 3,215 | 4,083 | 4,669 |
| gpt-5-2025-08-07 | L2 | 75 | 2,446 | 2,938 | 3,420 |
| gpt-5-2025-08-07 | L3 | 74 | 2,910 | 3,804 | 4,029 |
| gpt-5-2025-08-07 | L4 | 70 | 3,842 | 5,299 | 6,303 |
| gpt-5-mini-2025-08-07 | L1 | 75 | 1,994 | 2,446 | 2,783 |
| gpt-5-mini-2025-08-07 | L2 | 75 | 1,800 | 2,109 | 2,349 |
| gpt-5-mini-2025-08-07 | L3 | 75 | 1,840 | 2,305 | 2,577 |
| gpt-5-mini-2025-08-07 | L4 | 74 | 2,499 | 3,102 | 3,561 |

All well inside the requests' own `max_completion_tokens` ceiling
(16,384 / 8,192), so none of this band is capped/truncated.

**Priced at the corrected current Batch API rate** (gpt-5: $0.625 in /
$5.00 out per 1M; gpt-5-mini: $0.125 / $1.00 per 1M):

| Batch | Model | n | Exact input tokens (total) | Cost, low (p25 out) | Cost, mid (mean out) | Cost, high (p75 out) |
|---|---|---|---|---|---|---|
| Backfill | gpt-5 | 1,200 | 222,834 | $18.76 | $24.32 | $27.77 |
| Backfill | gpt-5-mini | 1,200 | 222,834 | $2.47 | $3.02 | $3.41 |
| Retry | gpt-5 | 6 | 1,418 | $0.11 | $0.15 | $0.18 |
| Retry | gpt-5-mini | 1 | 229 | ~$0.00 | ~$0.00 | ~$0.00 |
| ULT/PLT | gpt-5 | 800 | 398,602 | $15.62 | $21.44 | $25.46 |
| ULT/PLT | gpt-5-mini | 800 | 398,602 | $2.05 | $2.53 | $2.90 |
| **TOTAL** | | **4,007** | **1,244,519** | **$39.01** | **$51.47** | **$59.72** |

**Headline: ~$51 mid-estimate, plausible range $39-$60.** This is
meaningfully *lower* than the ~$81 figure in
`analysis/SUPERVISOR_HANDOFF_SUBMIT_ALL.md` — almost entirely because of
the §2 pricing-table bug (the old figure used the wrong, pricier `gpt-5.4`
rate), with a small additional correction from ULT/PLT's real input tokens
running noticeably higher than assumed (measured mean 498 tokens/request,
not the 231 carried over from Dynamic-L4 in the original ULT/PLT handoff —
that doc's own input-token figure was itself a reused Dynamic-L4 proxy,
not ULT/PLT's own data, since no ULT/PLT GPT-5 data has ever been
generated; input tokens are cheap enough relative to output that this
correction is <$0.15 of the total either way).
**Recommendation: budget for $60, expect to pay closer to $50.**

## 4. Billing mechanics — what to do before submitting (verified against OpenAI's own docs, not assumed)

Sources: `https://help.openai.com/en/articles/8264778-what-is-prepaid-billing`,
`https://help.openai.com/en/articles/10910291-api-organization-verification`,
`https://developers.openai.com/api/docs/guides/rate-limits`.

1. **Create/use an OpenAI account and generate an API key** if you're
   self-funding this rather than using the supervisor's key
   (`platform.openai.com` → API keys).
2. **Add prepaid credit.** New accounts are prepaid by default. Minimum
   purchase is **$5**, default top-up suggestion is **$10**. Given the
   $39-$60 estimate above, **top up at least $65-70** to leave headroom —
   under-funding mid-batch is worse than over-funding (see point 6).
3. **Organization verification is required for `gpt-5`-class models.**
   OpenAI's generic verification flow (government ID + live selfie,
   one verified account per person) is documented at the Help Center URL
   above; the *specific* trigger for gpt-5 access is corroborated by a real
   API error string reported third-party
   (`github.com/openai/codex#1982`): *"Your organization must be verified
   to use the model 'gpt-5'... it can take up to 15 minutes for access to
   propagate."* **Do this well before you intend to submit** — 15 minutes
   is the propagation delay *after* verification completes, not the
   verification process itself, which can take longer. A $0 or trivially
   cheap real-time test call (not a batch) to `gpt-5-mini` first is a
   reasonable way to confirm access has actually propagated before
   queuing the full batch.
4. **Confirm your usage tier.** A brand-new account starts on the Free
   tier, which explicitly does **not support `gpt-5` or `gpt-5-mini` at
   all** (both models' own rate-limit tables show `colSpan="3"` "Not
   supported" for Free — verified directly on both model pages). Tier 1
   unlocks automatically once $5 has been paid in (see point 2) — no
   separate application needed for Tier 1 specifically.
5. **Set `OPENAI_API_KEY`** in this project's `.env` (or your shell
   environment) — same mechanism every prior GPT batch in this project has
   used, no code changes needed for a different key.
6. **Understand what happens if the balance runs low mid-batch.** OpenAI's
   Batch FAQ states unambiguously that on expiry or cancellation, "any
   already completed work" is charged and the rest is dropped — so a
   batch does **not** silently fail-open into unpaid inference. **However,
   I could not find an official OpenAI page stating explicitly whether
   charging happens incrementally as sub-requests complete, at full-batch
   completion, or via a hold placed at submission** — this is disclosed as
   unverified rather than guessed. The practically safe conclusion either
   way: fund comfortably above the high estimate ($60) before submitting,
   and don't submit again immediately if a batch partially fails on an
   underfunded balance without first checking the account balance and
   what actually got billed.

## 5. Tier/queue limits and a chunking plan

Confirmed directly (both model pages, Tier 1 row): **gpt-5 batch queue
limit = 1,500,000 tokens; gpt-5-mini = 5,000,000 tokens** (Tier 1, i.e. the
tier a $5+ prepaid account is on). Independently corroborated by an OpenAI
staff forum post (`community.openai.com/t/increased-gpt-5-and-gpt-5-mini-rate-limits/1357840`)
announcing these exact figures.

**Unresolved, disclosed rather than assumed**: I could not find an OpenAI
doc that states precisely what counts toward this limit — total *enqueued
input* tokens, or *reserved capacity* (input + each request's
`max_completion_tokens`, since actual output isn't knowable at submission
time). The two prepared batches use `max_completion_tokens` of 16,384
(gpt-5) / 8,192 (gpt-5-mini) — large ceilings sized for hidden
reasoning-token overhead — so the two interpretations diverge hugely in
practice:

| Interpretation | gpt-5 tokens (all 3 batches combined, 2,006 reqs) | vs. 1,500,000 limit |
|---|---|---|
| Input-only (exact, tiktoken) | 622,854 | 42% — fits in one submission |
| Input + reserved `max_completion_tokens` | ~33.2M | **22x over** — needs chunking |

Given a wrong guess here risks a failed/rejected mid-flight submission (the
worse failure mode, per §4 point 6) versus the only cost of the conservative
assumption being "more, smaller files" (free, mechanical), **plan under the
conservative (reserved-capacity) interpretation**:

- **Backfill** (1,200 gpt-5 reqs, all `max_completion_tokens=16384`): chunk
  into **14 sub-batches** of ~90 requests each (`1,500,000 / (186 mean input
  + 16,384 cap) ≈ 90 requests/chunk`).
- **Backfill** (1,200 gpt-5-mini reqs, `max_completion_tokens=8192`): chunk
  into **3 sub-batches** of ~400-600 requests each (`5,000,000 / 8,378 ≈
  597/chunk`).
- **Retry** (6 gpt-5 + 1 gpt-5-mini): trivially fits in one chunk under
  either interpretation, no split needed.
- **ULT/PLT** (800 gpt-5 reqs): **9 sub-batches** of ~90.
- **ULT/PLT** (800 gpt-5-mini reqs): **2 sub-batches** of ~400-600.

Splitting is a mechanical `jsonl` line-slice (custom_ids don't need to
change; each chunk gets its own `create_batch.py`-style state file with a
distinct timestamp) — **not built in this pass** (no submission happens in
this pass at all), but the chunk boundaries above are ready to apply
directly if the first real submission attempt (after the user's go-ahead)
confirms the conservative interpretation was necessary. If OpenAI accepts
a larger single submission than planned, chunks can simply be coalesced —
losing nothing by having over-split.

**`process_batch.py` already ingests multiple output files per model
cleanly — confirmed by reading the code, no change needed.** Every scored
record is written via `append_jsonl()` (`src/logging_utils.py:8-18`),
which "never overwrites, each call adds one line," and the output filename
is built from *that state file's own* `created_at` timestamp
(`process_batch.py:236-239`) — so N chunks, each with a distinct state-file
timestamp, land in N distinct, non-colliding `*_batch_<timestamp>.jsonl`
files per model/benchmark/instantiation, which `src/Analysis/loader.py`
already reads and dedups by natural key at analysis time.

## 6. Account-agnostic check — confirmed directly

Every request line across all three prepared files contains only
`custom_id`, `method`, `url`, and `body` (itself only `model`, `messages`,
`max_completion_tokens`) — grepped for anything resembling an org ID,
API key, username, or absolute path (`org-*`, `sk-*`, `/users/*`,
`/home/*`): **zero matches**. The files are exactly as portable as
`SUPERVISOR_HANDOFF_SUBMIT_ALL.md` already claimed — any valid OpenAI API
key with `gpt-5-2025-08-07`/`gpt-5-mini-2025-08-07` access can submit them
unmodified.

**What submission actually needs** (mechanically): an `OPENAI_API_KEY`
picked up by `openai.OpenAI()` (env var or `.env`), then per file: upload
via `client.files.create(file=..., purpose="batch")`, then
`client.batches.create(input_file_id=..., endpoint="/v1/chat/completions",
completion_window="24h")`, writing the returned `batch_id` back into the
matching state file. Polling/scoring is already handled by
`scripts/process_batch.py <state_file>`.

**`create_batch.py` already had almost this exact submit path built in —
but its default was backwards and dangerous.** Before this pass, running
`python scripts/create_batch.py <configs>` **with no flags submitted and
spent money by default**; `--no-submit` was the opt-*out*. Fixed this pass:
the flag is now `--submit` (explicit opt-**in**, default off) — a bare
invocation now only ever writes the JSONL/state files, never uploads or
charges anything, matching the "no spend by default" posture this whole
pass is operating under. Updated everywhere `--no-submit` was referenced
(`scripts/slurm/run_create_batch_core400.slurm`, the four
`configs/gpt_5*__{ult,plt}__core400.yaml` header comments) to match; the
two `SUPERVISOR_HANDOFF_*.md` docs' historical `--no-submit` mentions are
left as-is (they're a record of what was actually run at the time, not
live instructions to re-execute).

## 7. Summary for Part 2 / the GO/NO-GO gate

- Scope: confirmed unchanged since 2026-07-13/14, reconciled against a live
  coverage-matrix run today.
- Cost: **$39-$60, mid-estimate ~$51** at corrected current batch pricing —
  materially cheaper than the $81 figure previously circulated, because
  that figure used a stale/mislabeled price for gpt-5/-mini (fixed in
  `src/pricing.py` this pass).
- Billing setup: 6-item checklist above (credit top-up ≥$65-70, org
  verification, confirm Tier 1 access) — none of this has been done in this
  pass, all of it needs doing before any real submission.
- Queue limits: fits easily under an input-only reading; needs a
  ~14/3/9/2-way chunk split under the conservative reserved-capacity
  reading. Plan for the conservative case; the first real chunk's
  acceptance will confirm which interpretation is correct.
- Submission mechanics: account-agnostic, confirmed; `create_batch.py`
  now defaults safe, `--submit` is the explicit spend action.
- **Nothing in this document authorizes a submission.** Part 2 (pre-flight
  verification) and the final GO/NO-GO checklist still need to run before
  that decision point, and per the user's explicit instruction this pass
  stops there regardless: no batch is submitted and no money is spent
  until the user has topped up credits and given an explicit go-ahead.
