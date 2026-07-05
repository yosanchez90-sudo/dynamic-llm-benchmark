"""Wrapper for loading and running local (open-source) HuggingFace models.

Records full provenance for every generation, so results are reproducible.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.models.base import GenerationConfig, Model, ModelOutput  # noqa: F401 (re-exported)


class LocalModel(Model):
    """A HuggingFace causal LM, optionally with a LoRA adapter loaded on top."""

    def __init__(
        self,
        model_id: str,
        revision: str | None = None,
        dtype: torch.dtype = torch.bfloat16,
        adapter_path: str | None = None,
    ) -> None:
        self.model_id = model_id

        if revision is None:
            self.revision = HfApi().model_info(model_id).sha
        else:
            self.revision = revision
        self.dtype = dtype
        self.adapter_path = adapter_path

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id, revision=self.revision, local_files_only=True
        )
        base = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=self.revision,
            dtype=dtype,
            device_map="auto",
            local_files_only=True,
        )

        if adapter_path:
            from peft import PeftModel
            # PeftModel.from_pretrained requires an absolute path for local adapters;
            # relative paths are mistakenly validated as HF repo IDs and rejected.
            abs_adapter = str(Path(adapter_path).resolve())
            self.model = PeftModel.from_pretrained(base, abs_adapter)
            print(f"[LocalModel] LoRA adapter loaded from {abs_adapter}", flush=True)
        else:
            self.model = base

        self.model.eval()
        device = next(self.model.parameters()).device
        print(f"[LocalModel] loaded on {device} | dtype={dtype} | revision={self.revision[:8]}...", flush=True)

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
            provider="local",
            cost_usd=None,
        )