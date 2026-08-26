"""Coverage matrix for the main study (zero-shot, K=1): model x tier x instantiation.

Scans data/results/dynamic/*.jsonl, dedupes rows by (model_label, tier,
instantiation_id, template_id, instance_seed), and diffs the result against
the spec target: 9 models x L1-L4 x instantiations 1-5, 15 templates x 5
instance seeds = 75 problems/cell.

Missing/partial cells are printed in three lanes:
  RUNNABLE NOW BY US   - API models we hold keys for, plus local Qwen on GPU.
  SUPERVISOR-GATED     - GPT cells (supervisor holds the OpenAI credits).
  DEFERRED             - one-shot and K=5, out of scope for this pass by
                          explicit cut-priority; reported, not chased.

Usage:
    python scripts/coverage_matrix.py [--results-dir data/results/dynamic]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

TIERS = ("L1", "L2", "L3", "L4")
INSTANTIATIONS = ("1", "2", "3", "4", "5")
TEMPLATES_PER_TIER = 15
SEEDS_PER_INSTANTIATION = 5
EXPECTED_PER_CELL = TEMPLATES_PER_TIER * SEEDS_PER_INSTANTIATION  # 75


@dataclass(frozen=True)
class ModelSpec:
    model_label: str
    lane: str  # "RUNNABLE NOW BY US" | "SUPERVISOR-GATED"


# The 9 subjects under test (PROJECT_BRIEF.md Sec 6). model_label values match
# compute_model_label() in src/eval/test_gen_problem.py: model_id with "/" -> "__",
# unchanged for API models (no "/" in their ids).
MODEL_SPECS: list[ModelSpec] = [
    ModelSpec("gpt-5-2025-08-07", "SUPERVISOR-GATED"),
    ModelSpec("gpt-5-mini-2025-08-07", "SUPERVISOR-GATED"),
    ModelSpec("claude-sonnet-4-6", "RUNNABLE NOW BY US"),
    ModelSpec("claude-haiku-4-5-20251001", "RUNNABLE NOW BY US"),
    ModelSpec("gemini-3.1-pro-preview", "RUNNABLE NOW BY US"),   # replaces retired gemini-2.5-pro
    ModelSpec("gemini-3.1-flash-lite", "RUNNABLE NOW BY US"),    # replaces retired gemini-2.5-flash
    ModelSpec("Qwen__Qwen2.5-Coder-32B-Instruct", "RUNNABLE NOW BY US"),
    ModelSpec("Qwen__Qwen2.5-Coder-7B-Instruct", "RUNNABLE NOW BY US"),
    ModelSpec("Qwen__Qwen2.5-Coder-1.5B-Instruct", "RUNNABLE NOW BY US"),
]
KNOWN_LABELS = {m.model_label for m in MODEL_SPECS}

# Single source of truth for "one of the 9 canonical models". Every script
# that computes a cross-model comparison/ranking/reliability figure (Comparison
# A/B, StableMut@K, RQ5) must filter to this before aggregating, or a
# fine-tuned adapter variant (Comparison C artifact) or a future cross-family
# model (RQ5 extension, different model_labels like "deepseek-ai__...") silently
# joins the panel. Confirmed 2026-07-28: analyze_stability.py had no such
# filter, so the two LoRA adapter labels leaked into pairwise Kendall tau once
# their POST Dynamic eval landed, moving the N=4 reliability figure from 0.675
# to 0.701 with no code/data-scope decision behind it.
CANONICAL_MODELS: list[str] = [m.model_label for m in MODEL_SPECS]


def filter_to_canonical(df, label_col: str = "model_label"):
    """Restrict df to the 9 canonical model_labels, dropping anything else
    (fine-tuned adapters, future cross-family models) silently. Callers that
    want to report what was excluded should diff df[label_col].unique() against
    CANONICAL_MODELS themselves (see coverage_matrix.load_coverage's
    unknown_labels for the reporting pattern)."""
    return df[df[label_col].isin(CANONICAL_MODELS)]


def _iter_result_files(results_dir: Path):
    for fp in sorted(results_dir.glob("*.jsonl")):
        if ".bak" in fp.name or "pre_model_label_migration" in fp.name:
            continue
        yield fp


def load_coverage(results_dir: Path):
    """Return (main_cells, deferred_counts, unknown_labels).

    main_cells: {(model_label, tier, instantiation_id) -> set of (template_id, instance_seed)}
        restricted to prompting_condition=zero_shot, K=1.
    deferred_counts: {(prompting_condition, K) -> row count} for anything outside
        zero_shot/K=1 (one-shot and/or K=5), regardless of model.
    unknown_labels: {model_label -> row count} for labels not in KNOWN_LABELS
        (e.g. fine-tuned adapter variants - Comparison C artifacts, not part of
        the main 9-model coverage target).
    """
    main_cells: dict[tuple[str, str, str], set[tuple[str, int]]] = defaultdict(set)
    deferred_counts: dict[tuple[str, int], int] = defaultdict(int)
    unknown_labels: dict[str, int] = defaultdict(int)

    for fp in _iter_result_files(results_dir):
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                label = row.get("model_label")
                pcond = row.get("prompting_condition")
                k = row.get("K")

                if label not in KNOWN_LABELS:
                    unknown_labels[label] += 1
                    continue

                if pcond != "zero_shot" or k != 1:
                    deferred_counts[(pcond, k)] += 1
                    continue

                key = (label, row["tier"], str(row["instantiation_id"]))
                main_cells[key].add((row["template_id"], int(row["instance_seed"])))

    return main_cells, deferred_counts, unknown_labels


def _status(actual: int) -> str:
    if actual == 0:
        return "MISSING"
    if actual < EXPECTED_PER_CELL:
        return "PARTIAL"
    return "COMPLETE"


def print_matrix(results_dir: Path) -> dict:
    main_cells, deferred_counts, unknown_labels = load_coverage(results_dir)

    print(f"Coverage matrix (main study: zero_shot, K=1) — {results_dir}")
    print(f"Target: {len(MODEL_SPECS)} models x {len(TIERS)} tiers x "
          f"{len(INSTANTIATIONS)} instantiations, {EXPECTED_PER_CELL} problems/cell "
          f"({TEMPLATES_PER_TIER} templates x {SEEDS_PER_INSTANTIATION} seeds)\n")

    gap_counts = {"RUNNABLE NOW BY US": 0, "SUPERVISOR-GATED": 0}
    all_gap_rows = {"RUNNABLE NOW BY US": [], "SUPERVISOR-GATED": []}

    for lane in ("RUNNABLE NOW BY US", "SUPERVISOR-GATED"):
        lane_models = [m for m in MODEL_SPECS if m.lane == lane]
        print(f"=== {lane} ===")
        header = f"{'model':<34} {'tier':<5} {'inst':<5} {'actual/expected':<16} {'status':<10}"
        print(header)
        print("-" * len(header))
        lane_has_gap = False
        for model in lane_models:
            for tier in TIERS:
                for inst in INSTANTIATIONS:
                    actual = len(main_cells.get((model.model_label, tier, inst), ()))
                    status = _status(actual)
                    if status == "COMPLETE":
                        continue
                    lane_has_gap = True
                    gap_counts[lane] += 1
                    row = (model.model_label, tier, inst, actual, EXPECTED_PER_CELL, status)
                    all_gap_rows[lane].append(row)
                    print(f"{model.model_label:<34} {tier:<5} {inst:<5} "
                          f"{actual}/{EXPECTED_PER_CELL:<12} {status:<10}")
        if not lane_has_gap:
            print("(no gaps — fully covered)")
        print()

    print("=== DEFERRED (one-shot, K=5) — listed, not chased ===")
    if not deferred_counts:
        print("(none run yet — correctly deferred, nothing to report)")
    else:
        for (pcond, k), count in sorted(deferred_counts.items(), key=lambda x: str(x[0])):
            print(f"  prompting_condition={pcond} K={k}: {count} rows exist")
    print()

    if unknown_labels:
        print("=== Excluded from main matrix (not one of the 9 canonical model_labels) ===")
        for label, count in sorted(unknown_labels.items()):
            print(f"  {label}: {count} rows (fine-tune/Comparison C artifact, or unrecognised label)")
        print()

    total_cells = len(MODEL_SPECS) * len(TIERS) * len(INSTANTIATIONS)
    complete = total_cells - gap_counts["RUNNABLE NOW BY US"] - gap_counts["SUPERVISOR-GATED"]
    print(f"Summary: {complete}/{total_cells} cells complete | "
          f"{gap_counts['RUNNABLE NOW BY US']} gaps RUNNABLE NOW BY US | "
          f"{gap_counts['SUPERVISOR-GATED']} gaps SUPERVISOR-GATED")

    return {
        "gap_rows": all_gap_rows,
        "gap_counts": gap_counts,
        "total_cells": total_cells,
        "complete": complete,
        "deferred_counts": deferred_counts,
        "unknown_labels": unknown_labels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("data/results/dynamic"))
    args = parser.parse_args()
    print_matrix(args.results_dir)


if __name__ == "__main__":
    main()
