"""Regression test: local generation must not silently inherit
repetition_penalty/top_k from the checkpoint's generation_config.json
without resolving and logging them — the same failure class as the
no_repeat_ngram_size collapse (analysis/README_QUARANTINE.md), just via a
different unlogged default."""
from unittest.mock import MagicMock

import torch

from src.models.base import GenerationConfig
from src.models.local import LocalModel


def _make_model(repetition_penalty=1.1, top_k=20) -> LocalModel:
    model = LocalModel.__new__(LocalModel)  # skip __init__ (no real HF load)
    model.model_id = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    model.revision = "deadbeef"
    model.adapter_path = None
    model.adapter_hash = None
    model.dtype = torch.bfloat16

    fake_generation_config = MagicMock()
    fake_generation_config.repetition_penalty = repetition_penalty
    fake_generation_config.top_k = top_k

    fake_hf_model = MagicMock()
    fake_hf_model.generation_config = fake_generation_config
    fake_hf_model.device = torch.device("cpu")
    input_ids = torch.tensor([[1, 2, 3]])
    fake_hf_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
    fake_hf_model.parameters.return_value = iter([torch.zeros(1)])
    model.model = fake_hf_model

    fake_tokenizer = MagicMock()
    fake_tokenizer.apply_chat_template.return_value = "prompt text"
    fake_tokenizer.return_value = MagicMock(
        to=MagicMock(return_value={"input_ids": input_ids})
    )
    fake_tokenizer.decode.return_value = "response text"
    fake_tokenizer.chat_template = "{% for m in messages %}{{ m['content'] }}{% endfor %}"
    model.tokenizer = fake_tokenizer

    return model


def test_repetition_penalty_and_top_k_pinned_from_checkpoint_and_logged():
    model = _make_model(repetition_penalty=1.1, top_k=20)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    call_kwargs = model.model.generate.call_args.kwargs
    assert call_kwargs["repetition_penalty"] == 1.1
    assert call_kwargs["top_k"] == 20

    assert out.generation_config["repetition_penalty"] == 1.1
    assert out.generation_config["repetition_penalty_source"] == "checkpoint_generation_config"
    assert out.generation_config["top_k"] == 20
    assert out.generation_config["top_k_source"] == "checkpoint_generation_config"


def test_different_checkpoint_repetition_penalty_reflected_exactly():
    """32B ships repetition_penalty=1.05, not 1.1 — must not be hardcoded."""
    model = _make_model(repetition_penalty=1.05, top_k=20)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["repetition_penalty"] == 1.05


def test_greedy_decoding_omits_sampling_only_params():
    """do_sample=False (greedy) must not send temperature/top_p/repetition_penalty/top_k."""
    model = _make_model()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=False)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    call_kwargs = model.model.generate.call_args.kwargs
    assert "repetition_penalty" not in call_kwargs
    assert "top_k" not in call_kwargs
    assert out.generation_config["repetition_penalty"] is None
    assert out.generation_config["repetition_penalty_source"] is None


def test_chat_template_source_and_hash_logged():
    """RQ5 cross-family extension (2026-07-28): a new model family means an
    untested chat template, so which template got applied (and that it came
    from tokenizer_config, not some silent fallback) must be part of the
    logged run identity, the same way repetition_penalty/top_k are."""
    model = _make_model()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["chat_template_source"] == "tokenizer_config"
    assert isinstance(out.generation_config["chat_template_hash"], str)
    assert len(out.generation_config["chat_template_hash"]) == 16


def test_chat_template_source_none_defined_when_tokenizer_has_no_template():
    model = _make_model()
    model.tokenizer.chat_template = None
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["chat_template_source"] == "none_defined"
    assert out.generation_config["chat_template_hash"] is None
