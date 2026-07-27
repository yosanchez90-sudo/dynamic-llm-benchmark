# RQ5 cross-family extension — candidate proposal (STOP GATE, not yet approved)

Per `analysis/RQ5_ANALYSIS_PLAN.md` Part 2 follow-up. The supervisor's actual
ask: the n=3 BigCodeBench correlation is all-Qwen (a within-family size
sweep, `analysis/RQ5_INTERPRETATION.md`'s "read this as size-scaling, not
cross-benchmark validity"). Breaking that confound needs models from
OTHER families with (a) a published, snapshot-verifiable BigCodeBench
number and (b) weights that fit this project's GPU partitions.

**Nothing in this document has been run. This is the proposal step; Part 2
item 7 explicitly requires approval before any submission.**

## Candidate table

| Model | Family | Size | Complete-split Pass@1 | Hard-split Pass@1 | Eval date | Current HF commit (captured 2026-07-27) |
|---|---|---|---|---|---|---|
| DeepSeek-Coder-6.7B-Instruct | DeepSeek | 6.7B | 43.8 | — (not checked, likely present) | 2023-10-28 | `e5d64ad...` |
| CodeLlama-13b-Instruct-hf | Meta/Llama | 13B | 31.7 | — (not checked) | 2023-08-25 | `7457954...` |
| StarCoder2-15B-Instruct-v0.1 | BigCode | 15B | 45.1 | — (not checked) | 2024-04-30 | `ffb8dd9...` |
| DeepSeek-Coder-33B-Instruct | DeepSeek | 33B | 51.1 | — (not checked) | 2023-10-28 | `61dc97b...` |
| *(optional 5th)* Mistral-7B-Instruct-v0.3 | Mistral | 7B | 27.3 | — (not checked) | 2024-05-22 | `c170c70...` |

Spans **3 distinct families** (DeepSeek, Meta/Llama, BigCode; +Mistral if
the 5th is included) and a **6.7B-33B size range**. DeepSeek appears twice
deliberately (6.7B and 33B) — a second within-family size pair from a
DIFFERENT family than Qwen lets us check whether the n=3-type
"perfect-but-confounded" pattern is Qwen-specific or a general property of
within-family sweeps, which is itself informative.

Hard-split scores weren't re-checked individually in this pass (time
budget) — Part 2 item 6 named Complete-split as adequate for candidate
selection; Hard-split would be pulled from `bigcode/bigcodebench-hard-results`
the same way as the Qwen numbers, before finalizing the harvest table if
these candidates are approved.

**Snapshot verification status**: current `main`-branch commit hash
captured directly via HTTP HEAD request just now (shown above) for each
repo. Full commit-history verification (no weight-changing commit since
each model's BigCodeBench eval date, the same check done for the 3 Qwen
sizes in `analysis/RQ5_LEADERBOARD_HARVEST.md`) is **not yet done** for
these four — proposed as the first step after approval, before pinning a
config, so a stale/mismatched revision is never silently used.

## VRAM / partition mapping

| Model | bf16 weight size (approx.) | Partition | GRES |
|---|---|---|---|
| DeepSeek-Coder-6.7B-Instruct | ~13.4 GB | k2-gpu-a100mig | `gpu:3g.40gb:1` |
| CodeLlama-13b-Instruct-hf | ~26 GB | k2-gpu-a100mig | `gpu:3g.40gb:1` |
| StarCoder2-15B-Instruct-v0.1 | ~30 GB | k2-gpu-a100mig | `gpu:3g.40gb:1` (tight — prefer full A100 if the MIG slice OOMs, same fragmentation risk as Stage 3a/3b) |
| DeepSeek-Coder-33B-Instruct | ~66 GB | k2-gpu-a100 | `gpu:a100:1` (full card required) |

Current queue snapshot (informational only, re-check before actual
submission): k2-gpu-a100mig — 1 node (gpu114), shared, moderately busy;
k2-gpu-a100 — 3 nodes, **366 jobs queued**; k2-gpu-h100 — 1 node, **259
jobs queued**. The 33B candidate's full-A100 requirement means a
potentially long queue wait, independent of the ~2h compute cost itself —
worth knowing before committing to include it.

## Network / download feasibility

Confirmed directly: the login node has outbound access to huggingface.co
(a live HTTP HEAD request just now returned a normal 307 redirect with
resolved commit hash, no timeout or block). Kelvin2's documented
restriction (`CLAUDE.md`: "Kelvin2 compute nodes drop outbound TCP
silently") applies to **compute nodes**, not the login node — matches how
the existing Qwen models were presumably cached originally. Downloads would
run via `huggingface-cli download` (or `snapshot_download`) **from the
login node**, writing into `HF_HOME=/mnt/scratch2/users/$USER/.huggingface`,
before any SLURM job runs (compute nodes then load with
`HF_HUB_OFFLINE=1`/`local_files_only=True` as usual). Total download size
for all 4 candidates: ~13.4+26+30+66 ≈ **135 GB** — well within scratch's
"no quota" allowance, but real bandwidth/time (not compute) to actually
transfer; not attempted in this pass, held for approval alongside the GPU
submission itself.

## Cost estimate (Part 2 item 7)

Measured throughput from this project's own historical runs, same size
class: Qwen 7B averaged **6.53s/problem generation** (full 300-problem
Dynamic run, all 4 tiers); Qwen 32B averaged **20.31s/problem generation**.
Adding this project's own measured scoring overhead (Stage 3a: scoring adds
~35% on top of generation time) gives ~8.8s/problem total for a 7B-class
model and ~27.4s/problem for a 32B-class model. Interpolating for the
13-16B range:

| Model | Rate (est., incl. scoring) | Dynamic (300 problems, 1 instantiation, L1-L4) | ULT core_400 (400 problems) |
|---|---|---|---|
| DeepSeek-Coder-6.7B-Instruct | ~8.8s/problem | ~0.73h | ~0.97h |
| CodeLlama-13b-Instruct-hf | ~16s/problem | ~1.33h | ~1.77h |
| StarCoder2-15B-Instruct-v0.1 | ~16s/problem | ~1.33h | ~1.77h |
| DeepSeek-Coder-33B-Instruct | ~27.4s/problem | ~2.28h | ~3.04h |
| **Total (Dynamic only)** | | **~5.7h** | |
| **Total (Dynamic + ULT)** | | | **~13.2h combined, across 4 independent jobs (each individually 1-5h, none near the 12h per-submission threshold)** |

No API spend (all local GPU models). Well under both the $5 and 12h/
submission STOP thresholds on a per-job basis; flagging the ~13.2h
aggregate for transparency since it's an aggregate across jobs, not
because any single submission approaches the threshold.

**Your call before I submit anything:**
1. Which candidates — all 4 (+ optional Mistral-7B, 5 total), or a subset?
2. Dynamic only (cheaper, directly answers the Dynamic↔ULT n=7 question
   with more cross-family points) or Dynamic + ULT (fuller picture, lets
   the new models also feed the BigCodeBench correlation, ~2.3x the cost)?
3. OK to spend the download bandwidth/time (~135 GB for all 4) from the
   login node before any GPU job?
