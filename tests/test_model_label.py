"""Unit tests for src/eval/test_gen_problem.py:compute_model_label, the
single source of truth for model_label, used both to name output files
(test_gen_runner.py, scripts/process_batch.py) and to stamp the TestGenRecord
field of the same name, so the two must always agree.
"""
from __future__ import annotations

from src.eval.test_gen_problem import TestGenRecord, compute_model_label


def test_base_model_no_adapter():
    assert compute_model_label("Qwen/Qwen2.5-Coder-7B-Instruct") == "Qwen__Qwen2.5-Coder-7B-Instruct"


def test_adapter_path_appends_ft_tag_from_parent_dir_name():
    label = compute_model_label(
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        adapter_path="data/finetune/qwen7b_lora_inst1/adapter_final",
    )
    assert label == "Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_inst1"


def test_adapter_path_uses_immediate_parent_even_for_checkpoint_dirs():
    # eval_checkpoints.py hot-swaps per-checkpoint adapters like
    # .../qwen7b_lora_bp_own_30ep/checkpoint-320. The experiment name is
    # still the parent, not "checkpoint-320" itself.
    label = compute_model_label(
        "Qwen/Qwen2.5-Coder-7B-Instruct",
        adapter_path="data/finetune/qwen7b_lora_bp_own_30ep/checkpoint-320",
    )
    assert label == "Qwen__Qwen2.5-Coder-7B-Instruct__ft_qwen7b_lora_bp_own_30ep"


def test_no_adapter_path_is_falsy_safe():
    assert compute_model_label("org/model", adapter_path=None) == "org__model"
    assert compute_model_label("org/model", adapter_path="") == "org__model"


def test_test_gen_record_new_fields_default_to_empty_or_none():
    r = TestGenRecord(
        model="m", instantiation_id="1", template_id="t", instance_seed=1,
        tier="L1", K=1, prompting_condition="zero_shot", benchmark="dynamic",
        exec_rate=1.0, statement_coverage=None, branch_coverage=None,
        mutation_score=None, mutants_total=0, mutants_killed=0,
        mutants_dropped_for_import_failure=0, generation_latency_seconds=0.0,
    )
    assert r.model_label == ""
    assert r.adapter_path is None
    assert r.adapter_hash is None
