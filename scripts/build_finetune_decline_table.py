"""Build the held-out execution-rate decline table (epoch 0 vs epoch 30) from
the corrected data/results/finetune_rebuild/epoch_perf_*.csv files.

Companion to scripts/build_finetune_endpoint_table.py, same source files,
different metric and question. That script reports baseline_pass_rate
(seen vs fresh, epoch 30 only) -- whether the generated suite is correct.
This one reports exec_rate (whether the generated suite runs at all,
independent of correctness) on the held-out split specifically, tracked
from epoch 0 to epoch 30, to separate a genuine held-out capability cost
from the memorisation signal baseline_pass_rate alone cannot distinguish.

seen   = instantiation 1 (the LoRA training split)
unseen = mean(instantiation 2, instantiation 3) per draw, then mean+-SD of
         that across the 3 R=3 sampling replicates -- same convention as
         build_finetune_endpoint_table.py.

Usage:
    python scripts/build_finetune_decline_table.py

Writes: analysis/finetune_decline_table.csv
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
OUT = ROOT / "analysis/finetune_decline_table.csv"
PROVENANCE_OUT = ROOT / "analysis/finetune_decline_table_PROVENANCE.md"
EPOCHS = (0, 30)
SAMPLING_DRAWS = ["sampling_seed42", "sampling_seed43", "sampling_seed44"]
CONDITIONS = ("bp_gpt5", "bp_own", "inst1")


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


def load_unseen_exec_rate(path: Path, epoch: int) -> tuple[str, float, list[float] | None]:
    """Sampling replicates (sampling_seed{42,43,44}) are recorded at epoch 30
    only, same convention as build_finetune_endpoint_table.py -- epoch 0
    (the untrained base checkpoint) has greedy only, so `sampling` is None
    there rather than raising on a requirement that never applied."""
    rows = list(csv.DictReader(path.open()))
    ep_rows = [r for r in rows if int(r["epoch"]) == epoch]
    if not ep_rows:
        raise ValueError(f"{path}: no epoch {epoch} rows")
    model = rows[0]["model"]
    by_inst_draw: dict[int, dict[str, float]] = {}
    for r in ep_rows:
        inst = int(r["instantiation"])
        by_inst_draw.setdefault(inst, {})[r["draw"]] = float(r["exec_rate"])
    for inst in (2, 3):
        if "greedy" not in by_inst_draw.get(inst, {}):
            raise KeyError(f"{path}: epoch {epoch} instantiation {inst} missing greedy draw")
    greedy = statistics.mean(by_inst_draw[i]["greedy"] for i in (2, 3)) * 100
    have_sampling = all(d in by_inst_draw[i] for i in (2, 3) for d in SAMPLING_DRAWS)
    sampling = (
        [statistics.mean(by_inst_draw[i][d] for i in (2, 3)) * 100 for d in SAMPLING_DRAWS]
        if have_sampling else None
    )
    return model, greedy, sampling


def decline_row(path: Path) -> dict:
    condition = _condition_from_name(path.stem)
    model = None
    greedy_by_epoch: dict[int, float] = {}
    sampling_by_epoch: dict[int, list[float] | None] = {}
    for epoch in EPOCHS:
        model, greedy, sampling = load_unseen_exec_rate(path, epoch)
        greedy_by_epoch[epoch] = greedy
        sampling_by_epoch[epoch] = sampling
    model_label = _model_shortname(model)
    e0, e30 = EPOCHS
    e30_sampling = sampling_by_epoch[e30]
    return {
        "model": model_label,
        "condition": condition,
        # Held-out (unseen inst2/3) exec_rate: does the generated suite run
        # at all, independent of correctness -- distinct from
        # build_finetune_endpoint_table.py's baseline_pass_rate.
        "exec_rate_unseen_epoch0_greedy_pct": round(greedy_by_epoch[e0], 1),
        "exec_rate_unseen_epoch30_greedy_pct": round(greedy_by_epoch[e30], 1),
        "exec_rate_unseen_decline_pp_greedy": round(greedy_by_epoch[e0] - greedy_by_epoch[e30], 1),
        "exec_rate_unseen_epoch30_sampling_mean_pct": round(statistics.mean(e30_sampling), 1),
        "exec_rate_unseen_epoch30_sampling_sd_pct": round(statistics.stdev(e30_sampling), 1),
    }


def main() -> None:
    all_rows = [decline_row(Path(fp)) for fp in sorted(glob.glob(str(ROOT / SRC_GLOB)))]

    order_cond = {"inst1": 0, "bp_own": 1, "bp_gpt5": 2}
    all_rows.sort(key=lambda r: (r["model"], order_cond[r["condition"]]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(all_rows[0].keys())
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    header = "  ".join(f"{h:>14s}" if h not in ("model", "condition") else f"{h:10s}" for h in fieldnames)
    table_lines = [header]
    for r in all_rows:
        table_lines.append("  ".join(
            f"{r[h]:10}" if h in ("model", "condition") else f"{r[h]:>14}"
            for h in fieldnames
        ))
        print("  ".join(str(r[h]) for h in fieldnames))

    provenance = f"""# Held-out execution-rate decline table (epoch 0 vs epoch 30) — raw table

{stamp_block("scripts/build_finetune_decline_table.py")}
Companion to `analysis/finetune_endpoint_table.csv` (baseline_pass_rate,
seen vs fresh, epoch 30 only). This table tracks `exec_rate`, whether
the generated suite runs at all, independent of correctness, on the
held-out (unseen inst2/3) split from epoch 0 to epoch 30, per condition.

Source glob: {SRC_GLOB}

## Decline table

{chr(10).join(table_lines)}
"""
    PROVENANCE_OUT.write_text(provenance)
    print(f"\nWritten: {OUT.relative_to(ROOT)}, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
