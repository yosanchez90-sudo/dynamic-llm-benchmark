"""Unit tests for scripts/submit_epoch_curve_shards.py's per-shard --mem
sizing, added after a flat 16G request (regardless of model size or
condition) OOM-killed 3 of the first 66 shards (all bp_gpt5, the
long-output condition; 2x 1.5B, 1x 7B). See analysis/README_QUARANTINE.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from submit_epoch_curve_shards import CONDITIONS, _mem_for, build_plan  # noqa: E402


def test_mem_for_7b_slow_is_largest():
    values = {
        (is_7b, is_slow): _mem_for(f"finetune_qwen{'7b' if is_7b else '1_5b'}_x", is_slow)
        for is_7b in (False, True) for is_slow in (False, True)
    }
    # Strictly increasing: 1.5B fast < 1.5B slow < 7B fast < 7B slow is not
    # required, but slow must cost more than fast within a size, and 7B
    # must cost more than 1.5B within a speed class.
    def gb(s: str) -> int:
        return int(s.rstrip("G"))

    assert gb(values[(False, False)]) < gb(values[(False, True)]), "1.5B slow must exceed 1.5B fast"
    assert gb(values[(True, False)]) < gb(values[(True, True)]), "7B slow must exceed 7B fast"
    assert gb(values[(False, False)]) < gb(values[(True, False)]), "7B fast must exceed 1.5B fast"
    assert gb(values[(False, True)]) < gb(values[(True, True)]), "7B slow must exceed 1.5B slow"


def test_mem_for_covers_the_three_jobs_that_actually_oomed():
    # jobs 9372594, 9372595 (qwen1_5b_bp_gpt5) and 9372627 (qwen7b_bp_gpt5)
    # all OOM-killed at the old flat 16G. The replacement must request more.
    assert int(_mem_for("finetune_qwen1_5b_bp_gpt5_30ep", True).rstrip("G")) > 16
    assert int(_mem_for("finetune_qwen7b_bp_gpt5_30ep", True).rstrip("G")) > 16


def test_build_plan_gives_every_shard_a_mem_value():
    plan = build_plan()
    assert len(plan) == 66, f"expected 11 shards x {len(CONDITIONS)} conditions = 66, got {len(plan)}"
    for shard in plan:
        assert shard.mem.endswith("G")
        assert int(shard.mem.rstrip("G")) >= 16
