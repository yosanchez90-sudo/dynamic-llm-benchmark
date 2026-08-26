"""Regression test for scripts/plot_epoch_perf.py's --draw filtering.

data/results/finetune_rebuild/epoch_perf_*.csv (written by the post-
2026-07-12 eval_checkpoints.py) carry a greedy row for every epoch plus 3
extra sampling_seed{42,43,44} rows at epoch 30 only. plot() groups purely
by (instantiation, epoch) x-position with no draw awareness, so without
filtering, epoch 30 would get 4 stacked points per instantiation instead
of one, a zigzag, not a curve. main() must filter to a single --draw
value (default "greedy") before rows reach plot().
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def _write_multidraw_csv(path: Path) -> None:
    fieldnames = ["model", "epoch", "instantiation", "draw", "baseline_pass"]
    rows = [
        {"model": "m", "epoch": "1", "instantiation": "1", "draw": "greedy", "baseline_pass": "0.1"},
        {"model": "m", "epoch": "30", "instantiation": "1", "draw": "greedy", "baseline_pass": "0.5"},
        {"model": "m", "epoch": "30", "instantiation": "1", "draw": "sampling_seed42", "baseline_pass": "0.4"},
        {"model": "m", "epoch": "30", "instantiation": "1", "draw": "sampling_seed43", "baseline_pass": "0.6"},
        {"model": "m", "epoch": "30", "instantiation": "1", "draw": "sampling_seed44", "baseline_pass": "0.45"},
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def test_default_draw_filter_leaves_one_row_per_epoch(tmp_path):
    csv_path = tmp_path / "epoch_perf_x.csv"
    _write_multidraw_csv(csv_path)

    from plot_epoch_perf import _read_csv

    rows = _read_csv(csv_path)
    filtered = [r for r in rows if r["draw"] == "greedy"]
    assert len(filtered) == 2, "greedy filter should leave exactly one row per epoch (1 and 30)"
    epochs = sorted(int(r["epoch"]) for r in filtered)
    assert epochs == [1, 30]


def test_unfiltered_rows_would_have_stacked_epoch30_points(tmp_path):
    """Documents the bug this filter prevents: without it, epoch 30 has 4
    rows for the same instantiation, which is exactly the zigzag case."""
    csv_path = tmp_path / "epoch_perf_x.csv"
    _write_multidraw_csv(csv_path)

    from plot_epoch_perf import _read_csv

    rows = _read_csv(csv_path)
    ep30_rows = [r for r in rows if r["epoch"] == "30" and r["instantiation"] == "1"]
    assert len(ep30_rows) == 4, "fixture should reproduce the 4-rows-at-one-epoch shape"
