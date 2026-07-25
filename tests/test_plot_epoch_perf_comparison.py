"""Regression tests for scripts/plot_epoch_perf_comparison.py.

Covers the two bugs it was written to fix (see that module's docstring):
draw-blind plotting stacking 4 points at epoch 30 into a zigzag, and
colouring by instantiation instead of by condition so overlaid conditions
were indistinguishable. Also checks the column-detection candidate lists
against the real epoch_perf_*.csv schema when that data is present
(data/ is gitignored, so it won't exist on a fresh clone -- skipped then,
not failed), and the 2026-07-15 hardening fixes: duplicate-row guard,
missing-epoch-0 warning/--strict, mixed-model refusal, and the >1.0
pass-rate unit-sanity check.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "plot_epoch_perf_comparison.py"
sys.path.insert(0, str(ROOT / "scripts"))

import plot_epoch_perf_comparison as pepc  # noqa: E402

REAL_CSV_DIR = ROOT / "data/results/finetune_rebuild"
REAL_CSVS = sorted(REAL_CSV_DIR.glob("epoch_perf_finetune_*_30ep.csv")) if REAL_CSV_DIR.exists() else []


def test_script_exists_at_expected_path():
    assert SCRIPT.exists(), f"expected {SCRIPT} (same directory as plot_epoch_perf.py)"


# ── synthetic fixtures (hermetic, no dependency on real data) ──────────────

FIELDNAMES = ["model", "epoch", "instantiation", "draw", "n", "baseline_pass"]


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


def _row(epoch, inst, draw, baseline_pass, model="Qwen/Qwen2.5-Coder-1.5B-Instruct", n=150):
    return {"model": model, "epoch": epoch, "instantiation": inst, "draw": draw,
            "n": n, "baseline_pass": baseline_pass}


def _multidraw_condition_csv(path: Path) -> None:
    """Reproduces the exact shape that caused the epoch-30 zigzag: greedy at
    every epoch, plus 3 extra sampling draws at epoch 30 only."""
    rows = []
    for ep in (0, 1, 30):
        for inst, val in ((1, 0.5), (2, 0.1), (3, 0.1)):
            rows.append(_row(ep, inst, "greedy", val))
    # epoch-30-only sampling draws with deliberately different (wrong-if-included) values
    for draw in ("sampling_seed42", "sampling_seed43", "sampling_seed44"):
        for inst, val in ((1, 0.9), (2, 0.9), (3, 0.9)):
            rows.append(_row(30, inst, draw, val))
    _write_csv(path, rows)


# ── condition detection ─────────────────────────────────────────────────────

@pytest.mark.parametrize("filename,expected", [
    ("epoch_perf_finetune_qwen1_5b_inst1_30ep.csv", "inst1"),
    ("epoch_perf_finetune_qwen1_5b_bp_own_30ep.csv", "bp_own"),
    ("epoch_perf_finetune_qwen1_5b_bp_gpt5_30ep.csv", "bp_gpt5"),
    ("epoch_perf_finetune_qwen7b_bp_gpt5_30ep.csv", "bp_gpt5"),
])
def test_condition_from_filename(filename, expected):
    assert pepc._condition_from_filename(Path(filename)) == expected


def test_condition_from_filename_raises_on_unrecognized():
    with pytest.raises(ValueError):
        pepc._condition_from_filename(Path("epoch_perf_finetune_qwen7b_mystery_30ep.csv"))


# ── draw filtering (the zigzag bug) ─────────────────────────────────────────

def test_draw_filter_leaves_one_row_per_epoch_per_instantiation(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _multidraw_condition_csv(csv_path)

    data = pepc.load_condition(csv_path, draw="greedy")

    assert data["epochs"] == [0, 1, 30]
    # seen (inst1) should be 0.5 at every epoch -- the sampling rows (0.9) must
    # never leak in, since that's exactly what caused the old zigzag/fake drop.
    assert data["seen"] == pytest.approx([0.5, 0.5, 0.5])
    assert data["unseen"] == pytest.approx([0.1, 0.1, 0.1])


def test_unfiltered_source_really_does_have_stacked_epoch30_rows(tmp_path):
    """Documents the bug being fixed: without draw filtering, epoch 30 has
    4 rows per instantiation, not 1."""
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _multidraw_condition_csv(csv_path)
    rows = list(csv.DictReader(csv_path.open()))
    ep30_inst1 = [r for r in rows if r["epoch"] == "30" and r["instantiation"] == "1"]
    assert len(ep30_inst1) == 4


def test_missing_draw_raises_clear_error(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _multidraw_condition_csv(csv_path)
    with pytest.raises(ValueError, match="no rows with"):
        pepc.load_condition(csv_path, draw="does_not_exist")


# ── unseen = mean(inst2, inst3) ─────────────────────────────────────────────

def test_unseen_is_mean_of_instantiation_2_and_3(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_bp_gpt5_30ep.csv"
    rows = [
        _row(30, 1, "greedy", 0.54),
        _row(30, 2, "greedy", 0.02),
        _row(30, 3, "greedy", 0.00),
    ]
    _write_csv(csv_path, rows)

    data = pepc.load_condition(csv_path, draw="greedy")
    assert data["seen"] == pytest.approx([0.54])
    assert data["unseen"] == pytest.approx([0.01])  # mean(0.02, 0.00)


# ── gap table ────────────────────────────────────────────────────────────────

def test_gap_table_matches_known_reference_value(tmp_path):
    """qwen1_5b bp_gpt5 reference: seen 54.0%, unseen 1.3%, gap 52.7pp."""
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_bp_gpt5_30ep.csv"
    rows = [
        _row(30, 1, "greedy", 0.5400),
        _row(30, 2, "greedy", 0.0200),
        _row(30, 3, "greedy", 0.0067),
    ]
    _write_csv(csv_path, rows)

    conditions = {"bp_gpt5": pepc.load_condition(csv_path, draw="greedy")}
    table = pepc.gap_table(conditions)

    assert len(table) == 1
    row = table[0]
    assert row["condition"] == "bp_gpt5"
    assert row["epoch"] == 30
    assert row["seen_baseline_pass_pct"] == pytest.approx(54.0, abs=0.1)
    assert row["unseen_baseline_pass_pct"] == pytest.approx(1.3, abs=0.1)
    assert row["gap_pp_baseline_pass"] == pytest.approx(52.7, abs=0.1)


# ── pass-rate column fallback (n_pass/n_total division) ─────────────────────

def test_pass_rate_falls_back_to_n_pass_over_n_total(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    fieldnames = ["model", "epoch", "instantiation", "draw", "n_pass", "n_total"]
    rows = [
        {"model": "m", "epoch": "1", "instantiation": "1", "draw": "greedy", "n_pass": "75", "n_total": "150"},
        {"model": "m", "epoch": "1", "instantiation": "2", "draw": "greedy", "n_pass": "15", "n_total": "150"},
        {"model": "m", "epoch": "1", "instantiation": "3", "draw": "greedy", "n_pass": "15", "n_total": "150"},
    ]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    data = pepc.load_condition(csv_path, draw="greedy")
    assert data["seen"] == pytest.approx([0.5])
    assert data["unseen"] == pytest.approx([0.1])


# ── real-schema integration check (skipped if data/ isn't populated) ────────

@pytest.mark.skipif(not REAL_CSVS, reason="data/results/finetune_rebuild not populated (data/ is gitignored)")
def test_candidate_lists_match_real_csv_schema():
    rows = list(csv.DictReader(REAL_CSVS[0].open()))
    fieldnames = list(rows[0].keys())
    assert pepc._first_present(fieldnames, pepc.PASS_RATE_COLS) is not None, (
        f"none of {pepc.PASS_RATE_COLS} found in real schema {fieldnames}"
    )
    assert pepc._first_present(fieldnames, pepc.INST_COLS) is not None
    assert pepc._first_present(fieldnames, pepc.DRAW_COLS) is not None
    draw_col = pepc._first_present(fieldnames, pepc.DRAW_COLS)
    assert "greedy" in {r[draw_col] for r in rows}, (
        "default --draw \"greedy\" must be a real value in the draw column"
    )


@pytest.mark.skipif(not REAL_CSVS, reason="data/results/finetune_rebuild not populated (data/ is gitignored)")
def test_real_condition_csv_loads_and_has_epoch_zero():
    for csv_path in REAL_CSVS:
        cond = pepc._condition_from_filename(csv_path)
        data = pepc.load_condition(csv_path, draw="greedy")
        assert data["epochs"][0] == 0, f"{csv_path.name} ({cond}) should include epoch 0"
        assert len(data["seen"]) == len(data["epochs"])
        assert len(data["unseen"]) == len(data["epochs"])


# ── hardening fix 1: duplicate-row guard ─────────────────────────────────────
# The --draw filter is the *first* line of defense against the multi-draw
# stacking bug, but only if DRAW_COLS actually contains the real draw-column
# name. These tests target the guard itself, independent of the filter, by
# constructing a duplicate (epoch, instantiation) pair that survives
# filtering (e.g. because the "draw" concept isn't in DRAW_COLS at all).

def test_duplicate_epoch_instantiation_raises_even_with_no_draw_column(tmp_path):
    """A CSV with no draw-like column at all (so --draw filtering is a
    no-op) but two rows for the same (epoch, instantiation) must be
    rejected outright, not silently let the second row win."""
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    fieldnames = ["model", "epoch", "instantiation", "baseline_pass"]
    rows = [
        {"model": "m", "epoch": "30", "instantiation": "1", "baseline_pass": "0.5"},
        {"model": "m", "epoch": "30", "instantiation": "1", "baseline_pass": "0.0"},  # duplicate!
        {"model": "m", "epoch": "30", "instantiation": "2", "baseline_pass": "0.1"},
    ]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    with pytest.raises(ValueError, match="duplicate row") as exc_info:
        pepc.load_condition(csv_path, draw="greedy")

    msg = str(exc_info.value)
    assert str(csv_path) in msg
    assert "epoch=30" in msg
    assert "instantiation=1" in msg
    assert "multi-draw stacking bug" in msg
    assert "draw column: None" in msg  # no DRAW_COLS match in this fixture


def test_duplicate_row_message_names_detected_draw_column(tmp_path):
    """When a draw column IS present, the error should name it (so a
    mis-set --draw value or a genuinely duplicated draw is diagnosable)."""
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    rows = [
        _row(30, 1, "greedy", 0.5),
        _row(30, 1, "greedy", 0.5),  # exact duplicate under the active filter
        _row(30, 2, "greedy", 0.1),
    ]
    _write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="duplicate row") as exc_info:
        pepc.load_condition(csv_path, draw="greedy")
    assert "draw column: 'draw'" in str(exc_info.value)


# ── hardening fix 2: missing epoch 0 -- warn by default, raise with --strict ─

def _no_epoch0_csv(path: Path) -> None:
    rows = [_row(ep, inst, "greedy", 0.5) for ep in (1, 3, 30) for inst in (1, 2, 3)]
    _write_csv(path, rows)


def test_missing_epoch_zero_warns_to_stderr_by_default(tmp_path, capsys):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _no_epoch0_csv(csv_path)

    data = pepc.load_condition(csv_path, draw="greedy")  # strict=False by default

    assert data["epochs"] == [1, 3, 30]  # still loads
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert str(csv_path) in captured.err
    assert "epoch 0" in captured.err


def test_missing_epoch_zero_raises_with_strict(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _no_epoch0_csv(csv_path)

    with pytest.raises(ValueError, match="epoch 0"):
        pepc.load_condition(csv_path, draw="greedy", strict=True)


def test_present_epoch_zero_is_silent(tmp_path, capsys):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    _multidraw_condition_csv(csv_path)  # includes epoch 0

    pepc.load_condition(csv_path, draw="greedy", strict=True)  # must not raise

    captured = capsys.readouterr()
    assert "WARNING" not in captured.err


# ── hardening fix 3: refuse to mix models ────────────────────────────────────

def test_main_refuses_mixed_models(tmp_path):
    csv_1_5b = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    csv_7b = tmp_path / "epoch_perf_finetune_qwen7b_bp_own_30ep.csv"
    _write_csv(csv_1_5b, [
        _row(30, 1, "greedy", 0.5, model="Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        _row(30, 2, "greedy", 0.1, model="Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        _row(30, 3, "greedy", 0.1, model="Qwen/Qwen2.5-Coder-1.5B-Instruct"),
    ])
    _write_csv(csv_7b, [
        _row(30, 1, "greedy", 0.6, model="Qwen/Qwen2.5-Coder-7B-Instruct"),
        _row(30, 2, "greedy", 0.5, model="Qwen/Qwen2.5-Coder-7B-Instruct"),
        _row(30, 3, "greedy", 0.5, model="Qwen/Qwen2.5-Coder-7B-Instruct"),
    ])

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_1_5b), str(csv_7b),
         "--out", str(tmp_path / "out.pdf")],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "Qwen/Qwen2.5-Coder-1.5B-Instruct" in combined
    assert "Qwen/Qwen2.5-Coder-7B-Instruct" in combined
    assert not (tmp_path / "out.pdf").exists(), "must refuse before plotting anything"


def test_main_accepts_single_model_across_conditions(tmp_path):
    """Sanity check that the mixed-model guard doesn't false-positive on
    the normal case: 3 conditions, all the same model."""
    paths = []
    for cond, model in [
        ("inst1", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        ("bp_own", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        ("bp_gpt5", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
    ]:
        p = tmp_path / f"epoch_perf_finetune_qwen1_5b_{cond}_30ep.csv"
        _write_csv(p, [
            _row(0, 1, "greedy", 0.5, model=model),
            _row(0, 2, "greedy", 0.1, model=model),
            _row(0, 3, "greedy", 0.1, model=model),
            _row(30, 1, "greedy", 0.5, model=model),
            _row(30, 2, "greedy", 0.1, model=model),
            _row(30, 3, "greedy", 0.1, model=model),
        ])
        paths.append(p)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), *[str(p) for p in paths],
         "--out", str(tmp_path / "out.pdf")],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "out.pdf").exists()


# ── hardening fix 5: pass-rate unit sanity (>1.0 means percent, not fraction) ─

def test_pass_rate_over_one_raises(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    rows = [
        _row(30, 1, "greedy", 54.0),  # looks like a 0-100 percent, not a 0-1 fraction
        _row(30, 2, "greedy", 0.02),
        _row(30, 3, "greedy", 0.01),
    ]
    _write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="exceeds 1.0"):
        pepc.load_condition(csv_path, draw="greedy")


def test_pass_rate_at_exactly_one_is_fine(tmp_path):
    csv_path = tmp_path / "epoch_perf_finetune_qwen1_5b_inst1_30ep.csv"
    rows = [
        _row(30, 1, "greedy", 1.0),
        _row(30, 2, "greedy", 1.0),
        _row(30, 3, "greedy", 1.0),
    ]
    _write_csv(csv_path, rows)

    data = pepc.load_condition(csv_path, draw="greedy")  # must not raise
    assert data["seen"] == pytest.approx([1.0])


# ── hardening fix 4: colourblind-safe palette ────────────────────────────────

def test_condition_colors_are_the_okabe_ito_values():
    assert pepc.CONDITION_COLORS["inst1"] == "#0072B2"
    assert pepc.CONDITION_COLORS["bp_own"] == "#009E73"
    assert pepc.CONDITION_COLORS["bp_gpt5"] == "#D55E00"
    # the old green/red pairing that was indistinguishable under deuteranopia
    assert pepc.CONDITION_COLORS["inst1"] != "#2ca02c"
    assert pepc.CONDITION_COLORS["bp_gpt5"] != "#d62728"
