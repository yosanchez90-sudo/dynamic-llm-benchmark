# Comparison A/B generation provenance

Generated: 2026-07-27T21:46:52.688875+00:00
Git commit: 76c663b

Sources: data/results/dynamic/*.jsonl (tier=L4 only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — 5/9 models
Missing (no scorable data on one or both sides — NOT zero-filled, simply
absent from comparison_a_paired.csv): ['Qwen__Qwen2.5-Coder-1.5B-Instruct', 'gemini-3.1-pro-preview', 'gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07']

## Comparison B (ULT vs PLT) — 7/9 models
Missing: ['gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07']

Pairing unit and CC-band methodology: see src/Analysis/comparison.py's
module docstring.

## Dedup-fix status (src/Analysis/loader.py, fixed 2026-07-25)

load_records() dedupes on (model_label, benchmark, instantiation_id,
template_id, instance_seed, tier, K, prompting_condition), keeping the
newest row by timestamp -- see that module's docstring for why. Comparison A
filters to tier=L4 only, and the ~559 duplicate rows found in the
2026-07-26 audit (scripts/audit_result_integrity.py) are entirely
L1/L2/L3-tier stale-retry rows -- none are L4, so Comparison A is unaffected
regardless of whether this table predates or postdates the loader fix.
Comparison B reads data/results/ult|plt/ directly, which the same audit
found have zero duplicate keys. Both tables here are correct independent of
generation order relative to the loader fix.
