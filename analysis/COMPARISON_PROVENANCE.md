# Comparison A/B generation provenance

Generated: 2026-07-25T16:17:53.310454+00:00
Git commit: ee83bf9

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
