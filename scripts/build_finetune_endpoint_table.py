"""Build the Phase-M final endpoint table (epoch 30, n_problems=150) from the corrected
data/results/finetune_rebuild/epoch_perf_*.csv files.

Reports, per (model, condition, split), the greedy baseline_pass rate and the
mean +- SD across the 3 R=3 sampling replicates (sampling_seed{42,43,44}) --
the two draw types were deliberately kept apart everywhere else in this
pipeline (see scripts/plot_epoch_perf_comparison.py, scripts/plot_epoch_perf.py
docstrings: "the sampling draws are a separate endpoint-table concern"). This
script is that concern.

seen   = instantiation 1 (the LoRA training split)
unseen = mean(instantiation 2, instantiation 3) per draw, then mean+-SD of
         that across the 3 sampling draws (consistent with how
         plot_epoch_perf_comparison.py's gap_table() treats "unseen" as a
         single per-draw series, just extended across draws instead of
         epochs).

Usage:
    python scripts/build_finetune_endpoint_table.py

Writes: analysis/finetune_endpoint_table.csv
"""
from __future__ import annotations

import csv
import glob
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.Analysis.provenance import stamp_block  # noqa: E402

SRC_GLOB = "data/results/finetune_rebuild/epoch_perf_*.csv"
OUT = ROOT / "analysis/finetune_endpoint_table.csv"
PROVENANCE_OUT = ROOT / "analysis/finetune_endpoint_table_PROVENANCE.md"
FINAL_EPOCH = 30
SAMPLING_DRAWS = ["sampling_seed42", "sampling_seed43", "sampling_seed44"]

CONDITIONS = ("bp_gpt5", "bp_own", "inst1")  # more specific first, matches plot_epoch_perf_comparison.py


def _condition_from_name(name: str) -> str:
    for cond in CONDITIONS:
        if cond in name:
            return cond
    raise ValueError(f"cannot determine condition from filename: {name}")


def _model_shortname(model_id: str) -> str:
    last = model_id.split("/")[-1]
    for size in ("1.5B", "7B", "32B", "72B"):
        if size in last:
            return f"Qwen {size}"
    return last


def load_epoch30(path: Path) -> tuple[str, dict[int, dict[str, float]]]:
    rows = list(csv.DictReader(path.open()))
    ep30 = [r for r in rows if int(r["epoch"]) == FINAL_EPOCH]
    if not ep30:
        raise ValueError(f"{path}: no epoch {FINAL_EPOCH} rows")
    model = rows[0]["model"]
    by_inst_draw: dict[int, dict[str, float]] = {}
    for r in ep30:
        inst = int(r["instantiation"])
        by_inst_draw.setdefault(inst, {})[r["draw"]] = float(r["baseline_pass"])
        n = r["n"]
    for inst in (1, 2, 3):
        if inst not in by_inst_draw:
            raise KeyError(f"{path}: epoch {FINAL_EPOCH} missing instantiation {inst}")
        missing = ({"greedy", *SAMPLING_DRAWS} - by_inst_draw[inst].keys())
        if missing:
            raise KeyError(f"{path}: instantiation {inst} missing draws {missing}")
    return model, by_inst_draw, n


def endpoint_rows(path: Path) -> list[dict]:
    condition = _condition_from_name(path.stem)
    model, by_inst_draw, n = load_epoch30(path)
    model_label = _model_shortname(model)

    seen_greedy = by_inst_draw[1]["greedy"] * 100
    seen_sampling = [by_inst_draw[1][d] * 100 for d in SAMPLING_DRAWS]

    unseen_greedy = statistics.mean(by_inst_draw[i]["greedy"] for i in (2, 3)) * 100
    unseen_sampling = [
        statistics.mean(by_inst_draw[i][d] for i in (2, 3)) * 100 for d in SAMPLING_DRAWS
    ]

    rows = []
    for split, greedy_pct, sampling_vals in (
        ("seen (inst1)", seen_greedy, seen_sampling),
        ("unseen (mean inst2/3)", unseen_greedy, unseen_sampling),
    ):
        rows.append({
            "model": model_label,
            "condition": condition,
            "epoch": FINAL_EPOCH,
            "n": n,
            "split": split,
            # Column names spell out the metric explicitly (baseline_pass, not
            # exec_rate) -- these are percentages of `baseline_pass` == True
            # (src/eval/test_gen_scorer.py's ScoreResult.baseline_passed),
            # i.e. the suite passes against the ORIGINAL function, not the
            # Exec@K collection-only gate. Flagged 2026-07-26: the ambiguous
            # prior names ("greedy_pct" etc.) read as if they could be either.
            "baseline_pass_greedy_pct": round(greedy_pct, 1),
            "baseline_pass_sampling_mean_pct": round(statistics.mean(sampling_vals), 1),
            "baseline_pass_sampling_sd_pct": round(statistics.stdev(sampling_vals), 1),
            "n_sampling_draws": len(sampling_vals),
        })
    gap_greedy = seen_greedy - unseen_greedy
    gap_sampling = statistics.mean(seen_sampling) - statistics.mean(unseen_sampling)
    for r in rows:
        r["baseline_pass_gap_pp_greedy"] = round(gap_greedy, 1)
        r["baseline_pass_gap_pp_sampling_mean"] = round(gap_sampling, 1)
    return rows


def main() -> None:
    all_rows = []
    for fp in sorted(glob.glob(str(ROOT / SRC_GLOB))):
        all_rows.extend(endpoint_rows(Path(fp)))

    order_cond = {"inst1": 0, "bp_own": 1, "bp_gpt5": 2}
    order_split = {"seen (inst1)": 0, "unseen (mean inst2/3)": 1}
    all_rows.sort(key=lambda r: (r["model"], order_cond[r["condition"]], order_split[r["split"]]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(all_rows[0].keys())
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"{'model':10s} {'condition':9s} {'split':22s} {'bp_greedy%':>10s} {'bp_samp.mean%':>13s} {'bp_samp.SD':>10s} {'gap(greedy)':>12s} {'gap(samp.)':>11s}")
    for r in all_rows:
        print(f"{r['model']:10s} {r['condition']:9s} {r['split']:22s} {r['baseline_pass_greedy_pct']:10.1f} "
              f"{r['baseline_pass_sampling_mean_pct']:13.1f} {r['baseline_pass_sampling_sd_pct']:10.1f} "
              f"{r['baseline_pass_gap_pp_greedy']:12.1f} {r['baseline_pass_gap_pp_sampling_mean']:11.1f}")

    header = "  ".join(f"{h:>12s}" if h not in ("model", "condition", "split") else f"{h:22s}" for h in fieldnames)
    table_lines = [header]
    for r in all_rows:
        table_lines.append("  ".join(
            f"{r[h]:22}" if h in ("model", "condition", "split") else f"{r[h]:>12}"
            for h in fieldnames
        ))
    provenance = f"""# Fine-tune endpoint table (epoch 30, n_problems=150) — raw table

{stamp_block("scripts/build_finetune_endpoint_table.py")}
This is the regenerable raw-table companion to the hand-written
`analysis/FINETUNE_ENDPOINT_PROVENANCE.md` (methodology/interpretation,
not touched by this script) -- re-run this script freely after new
data lands in `data/results/finetune_rebuild/`.

Source glob: {SRC_GLOB}

## Endpoint table

{chr(10).join(table_lines)}
"""
    PROVENANCE_OUT.write_text(provenance)
    print(f"\nWritten: {OUT.relative_to(ROOT)}, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
