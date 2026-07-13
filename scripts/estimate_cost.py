"""Pre-spend cost/wall-clock estimate for closing the main-study coverage gaps.

Reuses coverage_matrix.py's gap enumeration, then prices each gap cell:
  - API models (Claude Sonnet/Haiku, Gemini Pro/Flash, GPT-5, GPT-5-mini):
    USD cost via src/pricing.py, at Batch API rates where a batch pathway
    exists (OpenAI only in this codebase today — see ASSUMPTIONS below).
  - Local Qwen (1.5B/7B/32B): GPU-hours, from measured per-tier generation
    latency, scaled to tiers with no local data yet.

ASSUMPTIONS (read before trusting the numbers):

1. Input tokens/problem are estimated per-tier from GPT-5/GPT-5-mini's real
   logged `runtime_info.input_tokens` (L1=150, L2=165, L3=190, L4=232 as of
   the data on disk when this was last run). This is a fair cross-provider
   proxy because src/data/test_gen.py builds one identical message list per
   problem, reused for every model/provider — the prompt tokenizes to a
   similar count everywhere modulo tokenizer differences (~10-15%).

2. Output tokens/problem for GPT-5 and GPT-5-mini use each model's OWN real
   logged `runtime_info.output_tokens` average per tier. These are reasoning
   models — logged output_tokens includes hidden reasoning tokens (a sampled
   row showed 3300 output_tokens billed against a ~700-token visible test
   file), so this is the correct number for THEIR cost, but must not be
   reused as a proxy for non-reasoning models.

3. Output tokens/problem for Claude Sonnet/Haiku and Gemini Pro/Flash (no
   logged usage exists for them yet) are estimated from the VISIBLE response
   text length (chars / 4) pooled across every existing non-reasoning-visible
   generation on disk (GPT-5's and GPT-5-mini's visible `extracted_test_file`
   text, plus all three Qwen sizes) — i.e. "how many characters of pytest
   code did a model actually write for a problem at this tier", independent
   of any one model's reasoning-token overhead. This is a real assumption,
   not measured data for these four models specifically; treat the resulting
   dollar figures as an estimate, not a quote.

4. Batch discount: OpenAI's Batch API bills at 50% of the real-time rates in
   src/pricing.py's PRICING table (see that file's docstring) — applied here
   for gpt-5*/gpt-5-mini*. Anthropic and Gemini also offer batch APIs with
   similar discounts, but src/models/anthropic_model.py and
   src/models/gemini_model.py only implement real-time calls in this
   codebase (no batch submission path exists for them, unlike
   scripts/create_batch.py for OpenAI) — so Claude/Gemini costs below are
   real-time rates. Building batch support for them would roughly halve
   their cost but is out of scope unless separately approved.

5. Qwen GPU-hours: measured avg generation_latency_seconds/problem from
   existing L1/L2 runs (all three sizes have this), scaled to L3/L4 by the
   same tier-to-tier output-length growth ratio used for assumption 3 (L3/L4
   problems produce longer test suites -> longer generation, roughly
   proportionally). A 1.6x wall-clock multiplier is applied on top to
   account for mutation-scoring time riding in the same SLURM allocation
   (derived from the L1+L2 1.5B pilot: ~13.2s/problem measured end-to-end
   including scoring vs ~8.2s/problem pure generation_latency_seconds).

Usage:
    python scripts/estimate_cost.py
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_matrix import load_coverage, MODEL_SPECS, TIERS, INSTANTIATIONS, EXPECTED_PER_CELL  # noqa: E402
from src.pricing import PRICING  # noqa: E402

CHARS_PER_TOKEN = 4.0
OPENAI_BATCH_DISCOUNT = 0.5
SCORING_OVERHEAD_MULTIPLIER = 1.6  # wall-clock, not GPU-compute — see ASSUMPTIONS 5

RESULTS_DIR = ROOT / "data" / "results" / "dynamic"

OPENAI_LABELS = {"gpt-5-2025-08-07", "gpt-5-mini-2025-08-07"}
QWEN_LABELS = {
    "Qwen__Qwen2.5-Coder-1.5B-Instruct",
    "Qwen__Qwen2.5-Coder-7B-Instruct",
    "Qwen__Qwen2.5-Coder-32B-Instruct",
}


def _load_raw_rows():
    rows = []
    for fp in glob.glob(str(RESULTS_DIR / "*.jsonl")):
        if ".bak" in fp or "pre_model_label_migration" in fp or "__ft_" in fp:
            continue
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("prompting_condition") == "zero_shot" and d.get("K") == 1:
                    rows.append(d)
    return rows


def _tier_input_tokens(rows) -> dict[str, float]:
    by_tier = defaultdict(list)
    for d in rows:
        ri = d.get("runtime_info") or {}
        if ri.get("input_tokens") is not None:
            by_tier[d["tier"]].append(ri["input_tokens"])
    return {t: sum(v) / len(v) for t, v in by_tier.items() if v}


def _openai_output_tokens(rows) -> dict[str, dict[str, float]]:
    by_model_tier = defaultdict(lambda: defaultdict(list))
    for d in rows:
        if d["model_label"] not in OPENAI_LABELS:
            continue
        ri = d.get("runtime_info") or {}
        if ri.get("output_tokens") is not None:
            by_model_tier[d["model_label"]][d["tier"]].append(ri["output_tokens"])
    return {m: {t: sum(v) / len(v) for t, v in tiers.items() if v}
            for m, tiers in by_model_tier.items()}


def _pooled_visible_output_tokens(rows) -> dict[str, float]:
    by_tier = defaultdict(list)
    for d in rows:
        text = d.get("extracted_test_file") or d.get("response") or ""
        by_tier[d["tier"]].append(len(text))
    return {t: (sum(v) / len(v)) / CHARS_PER_TOKEN for t, v in by_tier.items() if v}


def _qwen_latency(rows) -> dict[str, dict[str, float]]:
    by_model_tier = defaultdict(lambda: defaultdict(list))
    for d in rows:
        if d["model_label"] not in QWEN_LABELS:
            continue
        by_model_tier[d["model_label"]][d["tier"]].append(d.get("generation_latency_seconds", 0.0))
    return {m: {t: sum(v) / len(v) for t, v in tiers.items() if v}
            for m, tiers in by_model_tier.items()}


def main() -> None:
    rows = _load_raw_rows()
    input_tok = _tier_input_tokens(rows)
    openai_out = _openai_output_tokens(rows)
    pooled_out = _pooled_visible_output_tokens(rows)
    qwen_lat = _qwen_latency(rows)

    # Tier-to-tier growth ratio (relative to L1), from the pooled visible-text
    # proxy — used to project Qwen L3/L4 latency where no local data exists yet.
    l1_pooled = pooled_out.get("L1", 1.0)
    tier_ratio = {t: pooled_out.get(t, l1_pooled) / l1_pooled for t in TIERS}

    main_cells, _, _ = load_coverage(RESULTS_DIR)

    print("=== Cost/wall-clock estimate for RUNNABLE-NOW-BY-US + SUPERVISOR-GATED gaps ===")
    print("(see this script's module docstring for every estimation assumption)\n")

    print(f"Empirical input tokens/problem by tier (GPT-5/-mini real usage): "
          f"{ {t: round(v) for t, v in input_tok.items()} }")
    print(f"Pooled visible-output-token proxy by tier (cross-model, chars/{CHARS_PER_TOKEN:.0f}): "
          f"{ {t: round(v) for t, v in pooled_out.items()} }\n")

    grand_total_usd = 0.0
    grand_total_gpu_hours = 0.0

    for model in MODEL_SPECS:
        gap_problems_by_tier = defaultdict(int)
        for tier in TIERS:
            for inst in INSTANTIATIONS:
                actual = len(main_cells.get((model.model_label, tier, inst), ()))
                missing = EXPECTED_PER_CELL - actual
                if missing > 0:
                    gap_problems_by_tier[tier] += missing
        total_missing = sum(gap_problems_by_tier.values())
        if total_missing == 0:
            continue

        if model.model_label in QWEN_LABELS:
            lat = qwen_lat.get(model.model_label, {})
            l1_lat = lat.get("L1")
            total_seconds = 0.0
            detail = []
            for tier, n in gap_problems_by_tier.items():
                tier_lat = lat.get(tier)
                if tier_lat is None and l1_lat is not None:
                    tier_lat = l1_lat * tier_ratio[tier]  # projected, no local data at this tier
                    detail.append(f"{tier}:{n}problems@~{tier_lat:.1f}s(projected)")
                elif tier_lat is not None:
                    detail.append(f"{tier}:{n}problems@{tier_lat:.1f}s(measured)")
                else:
                    tier_lat = 0.0
                total_seconds += n * tier_lat
            gpu_hours = (total_seconds * SCORING_OVERHEAD_MULTIPLIER) / 3600
            grand_total_gpu_hours += gpu_hours
            print(f"{model.model_label:<34} {total_missing:4d} problems  "
                  f"~{gpu_hours:.1f} GPU-hours  [{', '.join(detail)}]")
            continue

        # API model: USD cost.
        rate = PRICING.get(model.model_label)
        if rate is None:
            print(f"{model.model_label:<34} {total_missing:4d} problems  "
                  f"UNPRICED (not in src/pricing.py PRICING table)")
            continue
        in_rate, out_rate = rate
        is_openai = model.model_label in OPENAI_LABELS
        discount = OPENAI_BATCH_DISCOUNT if is_openai else 1.0
        rate_note = "batch, 50% off" if is_openai else "real-time (no batch path built)"

        cost = 0.0
        for tier, n in gap_problems_by_tier.items():
            it = input_tok.get(tier, 0)
            if is_openai:
                ot = openai_out.get(model.model_label, {}).get(tier, pooled_out.get(tier, 0))
            else:
                ot = pooled_out.get(tier, 0)
            cost += n * (it * in_rate + ot * out_rate) / 1_000_000 * discount
        grand_total_usd += cost
        print(f"{model.model_label:<34} {total_missing:4d} problems  "
              f"${cost:.2f}  ({rate_note})")

    print()
    print(f"TOTAL projected spend (Claude + Gemini + GPT, GPT at batch rate): ${grand_total_usd:.2f}")
    print(f"TOTAL projected local GPU time (Qwen 1.5B/7B/32B, incl. {SCORING_OVERHEAD_MULTIPLIER}x "
          f"scoring-overhead multiplier): {grand_total_gpu_hours:.1f} GPU-hours")


if __name__ == "__main__":
    main()
