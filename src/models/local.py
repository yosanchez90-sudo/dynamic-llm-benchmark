"""Wrapper for loading and running local (open-source) HuggingFace models.

Records full provenance for every generation, so results are reproducible.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import torch
from huggingface_hub import HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class GenerationConfig:
    """Decoding parameters. Defaults to greedy (deterministic)."""
    max_new_tokens: int = 512
    do_sample: bool = False
    temperature: float | None = None
    top_p: float | None = None
    seed: int = 42


@dataclass
class ModelOutput:
    """One model response, plus everything needed to reproduce it."""
    prompt: str
    prompt_hash: str
    response: str
    input_tokens: int
    output_tokens: int
    model_id: str
    model_revision: str          # exact commit SHA on HuggingFace
    generation_config: dict[str, Any]
    timestamp: str
    runtime_info: dict[str, Any]


class LocalModel:
    """A HuggingFace causal LM, loaded with a pinned revision."""

    def __init__(
        self,
        model_id: str,
        revision: str | None = None,
        dtype: torch.dtype = torch.bfloat16,
    ) -> None:
        self.model_id = model_id

        # Resolve current SHA if not explicitly pinned. We RECORD it
        # regardless, that way, even "first run" results are reproducible.
        if revision is None:
            self.revision = HfApi().model_info(model_id).sha
        else:
            self.revision = revision
        self.dtype = dtype

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=self.revision
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=self.revision,
            torch_dtype=dtype,
            device_map="auto",   # transformers chooses GPU placement
        )
        self.model.eval()        # turn off dropout, etc.

    def generate(
        self,
        messages: list[dict[str, str]],
        cfg: GenerationConfig,
    ) -> ModelOutput:
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        torch.manual_seed(cfg.seed)
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": cfg.max_new_tokens,
            "do_sample": cfg.do_sample,
        }
        if cfg.do_sample:
            gen_kwargs["temperature"] = cfg.temperature
            gen_kwargs["top_p"] = cfg.top_p

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **gen_kwargs)

        input_len = inputs["input_ids"].shape[1]
        new_tokens = output_ids[0][input_len:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

        return ModelOutput(
            prompt=prompt,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            response=response,
            input_tokens=input_len,
            output_tokens=len(new_tokens),
            model_id=self.model_id,
            model_revision=self.revision,
            generation_config={
                "max_new_tokens": cfg.max_new_tokens,
                "do_sample": cfg.do_sample,
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "seed": cfg.seed,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            runtime_info={
                "torch_version": torch.__version__,
                "cuda_version": torch.version.cuda,
                "gpu": (
                    torch.cuda.get_device_name(0)
                    if torch.cuda.is_available() else None
                ),
                "hostname": os.uname().nodename,
                "dtype": str(self.dtype),
            },
        )