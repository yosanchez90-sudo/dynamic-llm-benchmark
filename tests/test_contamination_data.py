"""Unit tests for src/Contamination/data.py's CSV re-expansion logic, using
a small synthetic epoch_perf-shaped CSV, no dependency on real fine-tuning
results.
"""
from __future__ import annotations

import pytest

from src.Contamination.data import (
    hf_id_to_model_label, load_post_finetune_dynamic, load_pre_post_same_instrument,
)


def _write_csv(path, rows):
    header = "model,epoch,instantiation,n,exec_rate,baseline_pass\n"
    body = "\n".join(f"m,{e},{i},{n},{er},{bp}" for e, i, n, er, bp in rows)
    path.write_text(header + body + "\n")


def _write_csv_with_draw(path, rows):
    """rows: (epoch, instantiation, draw, n, exec_rate, baseline_pass)"""
    header = "model,epoch,instantiation,draw,n,exec_rate,baseline_pass\n"
    body = "\n".join(f"m,{e},{i},{d},{n},{er},{bp}" for e, i, d, n, er, bp in rows)
    path.write_text(header + body + "\n")


def test_hf_id_to_model_label():
    assert hf_id_to_model_label("Qwen/Qwen2.5-Coder-1.5B-Instruct") == "Qwen__Qwen2.5-Coder-1.5B-Instruct"


def test_reconstruction_recovers_exact_counts(tmp_path):
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv(csv_path, [
        (30, 2, 10, 0.6, 0.2),   # 6 exec ones, 2 baseline ones
        (30, 3, 10, 0.4, 0.1),   # 4 exec ones, 1 baseline one
    ])
    df = load_post_finetune_dynamic(csv_path, epoch=30, instantiations=(2, 3))
    assert len(df) == 20
    assert (df["benchmark"] == "dynamic").all()
    assert df["exec_rate"].sum() == 10   # 6 + 4
    assert df["baseline_pass"].sum() == 3  # 2 + 1


def test_default_epoch_is_the_max_present(tmp_path):
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv(csv_path, [
        (1, 2, 10, 0.1, 0.0),
        (30, 2, 10, 0.9, 0.5),
    ])
    df = load_post_finetune_dynamic(csv_path, instantiations=(2,))
    assert df["exec_rate"].mean() == pytest.approx(0.9)


def test_train_instantiation_excluded_by_default(tmp_path):
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv(csv_path, [
        (30, 1, 10, 1.0, 1.0),   # instantiation 1 = train, excluded by default
        (30, 2, 10, 0.0, 0.0),
        (30, 3, 10, 0.0, 0.0),
    ])
    df = load_post_finetune_dynamic(csv_path, epoch=30)  # default instantiations=(2,3)
    assert len(df) == 20
    assert df["exec_rate"].sum() == 0  # instantiation 1's all-1.0 rows must not leak in


def test_multiple_draws_are_not_summed_together(tmp_path):
    # Without draw-filtering, greedy + 3 sampling draws for the same
    # (epoch, instantiation) would get concatenated and double/quadruple
    # counted. This is exactly the correctness bug the new schema needs
    # guarding against.
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv_with_draw(csv_path, [
        (30, 2, "greedy", 10, 1.0, 1.0),
        (30, 2, "sampling_seed42", 10, 0.0, 0.0),
        (30, 2, "sampling_seed43", 10, 0.0, 0.0),
        (30, 3, "greedy", 10, 1.0, 1.0),
    ])
    df = load_post_finetune_dynamic(csv_path, epoch=30, instantiations=(2, 3), draw="greedy")
    assert len(df) == 20  # only the two greedy rows, not all four
    assert df["exec_rate"].sum() == 20


def test_load_pre_post_same_instrument_uses_epoch_zero_as_pre(tmp_path):
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv_with_draw(csv_path, [
        (0, 2, "greedy", 10, 0.5, 0.1),    # pre (baseline, no adapter)
        (0, 3, "greedy", 10, 0.5, 0.1),
        (30, 2, "greedy", 10, 1.0, 0.9),   # post
        (30, 3, "greedy", 10, 1.0, 0.9),
    ])
    pre, post = load_pre_post_same_instrument(csv_path)
    assert pre["exec_rate"].mean() == pytest.approx(0.5)
    assert post["exec_rate"].mean() == pytest.approx(1.0)


def test_load_pre_post_same_instrument_raises_without_baseline_rows(tmp_path):
    csv_path = tmp_path / "epoch_perf.csv"
    _write_csv_with_draw(csv_path, [
        (30, 2, "greedy", 10, 1.0, 0.9),
    ])
    with pytest.raises(ValueError, match="no epoch=0"):
        load_pre_post_same_instrument(csv_path)
