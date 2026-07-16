"""Regression tests for scripts/eval_checkpoints.py's adapter_path /
adapter_weights_hash CSV provenance columns (added 2026-07-16 — see
analysis/reports/inst1_control_verification.md's addendum for why: no
epoch_perf_*.csv row previously recorded which adapter directory produced
it, an outright gap relative to CLAUDE.md's "adapter identity (path +
hash) is part of model identity" rule).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import eval_checkpoints as ec  # noqa: E402


def test_adapter_weights_hash_none_for_no_checkpoint():
    assert ec.adapter_weights_hash(None) is None


def test_adapter_weights_hash_none_when_no_adapter_file(tmp_path):
    empty_dir = tmp_path / "checkpoint-1"
    empty_dir.mkdir()
    assert ec.adapter_weights_hash(empty_dir) is None


def test_adapter_weights_hash_matches_sha256_of_safetensors_file(tmp_path):
    ckpt_dir = tmp_path / "checkpoint-17"
    ckpt_dir.mkdir()
    content = b"not a real safetensors file, just needs deterministic bytes"
    (ckpt_dir / "adapter_model.safetensors").write_bytes(content)

    got = ec.adapter_weights_hash(ckpt_dir)
    assert got == hashlib.sha256(content).hexdigest()


def test_adapter_weights_hash_falls_back_to_bin(tmp_path):
    ckpt_dir = tmp_path / "checkpoint-17"
    ckpt_dir.mkdir()
    content = b"legacy .bin adapter weights"
    (ckpt_dir / "adapter_model.bin").write_bytes(content)

    got = ec.adapter_weights_hash(ckpt_dir)
    assert got == hashlib.sha256(content).hexdigest()


def test_adapter_weights_hash_differs_for_different_content(tmp_path):
    d1 = tmp_path / "checkpoint-17"
    d2 = tmp_path / "checkpoint-34"
    d1.mkdir(); d2.mkdir()
    (d1 / "adapter_model.safetensors").write_bytes(b"epoch 1 weights")
    (d2 / "adapter_model.safetensors").write_bytes(b"epoch 2 weights")

    assert ec.adapter_weights_hash(d1) != ec.adapter_weights_hash(d2)


def test_csv_fieldnames_include_adapter_provenance_columns():
    source = (ROOT / "scripts" / "eval_checkpoints.py").read_text()
    assert '"adapter_path"' in source
    assert '"adapter_weights_hash"' in source
