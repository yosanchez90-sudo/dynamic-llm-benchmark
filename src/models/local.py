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


def _hash_adapter(adapter_path: str) -> str:
    """sha256 over adapter_config.json + the adapter weights file, the
    identity of "which adapter was actually loaded", not just its path
    (a path like .../adapter_final can get overwritten by a later training
    run without the path itself changing, which a hash catches).
    """
    adir = Path(adapter_path)
    h = hashlib.sha256()
    h.update((adir / "adapter_config.json").read_bytes())
    weights_file = next(
        (f for f in (adir / "adapter_model.safetensors", adir / "adapter_model.bin")
         if f.exists()),
        None,
    )
    if weights_file is None:
        raise FileNotFoundError(f"No adapter_model.{{safetensors,bin}} found in {adir}")
    h.update(weights_file.read_bytes())
    return h.hexdigest()


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

        self.adapter_hash: str | None = None
        if adapter_path:
            from peft import PeftModel
            # PeftModel.from_pretrained requires an absolute path for local adapters;
            # relative paths are mistakenly validated as HF repo IDs and rejected.
            abs_adapter = str(Path(adapter_path).resolve())
            self.adapter_path = abs_adapter   # store the resolved path, not the raw config value
            self.adapter_hash = _hash_adapter(abs_adapter)
            self.model = PeftModel.from_pretrained(base, abs_adapter)
            print(f"[LocalModel] LoRA adapter loaded from {abs_adapter} "
                  f"(hash={self.adapter_hash[:12]}...)", flush=True)
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
        # No fallback path exists here by design: apply_chat_template() raises
        # if the tokenizer has no chat_template instead of silently applying
        # some other format, so "chat_template_source" below is always
        # "tokenizer_config" for any row that made it past this call. Logged
        # explicitly (not just implied by the absence of a crash) after the
        # RQ5 cross-family extension raised chat-template provenance as an
        # open question for models this project hadn't run before (2026-07-28).
        chat_template = getattr(self.tokenizer, "chat_template", None)
        chat_template_hash = (
            hashlib.sha256(chat_template.encode()).hexdigest()[:16] if chat_template else None
        )
        # Inferred from the actual messages received, not from config intent
        # (src/data/test_gen.py::_build_messages's supports_system_role flag),
        # reflects what was really sent even if something upstream changes.
        prompt_delivery_mode = (
            "system_role" if any(m["role"] == "system" for m in messages)
            else "system_folded_into_user"
        )
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        torch.manual_seed(cfg.seed)
        # Anything not explicitly passed to generate() falls back to the
        # checkpoint's own generation_config.json (loaded into
        # self.model.generation_config at from_pretrained time), silently,
        # with no record of it anywhere. This is the same failure mode as
        # the no_repeat_ngram_size collapse (analysis/README_QUARANTINE.md),
        # just via a different unlogged inherited default: Qwen2.5-Coder's
        # checkpoints ship repetition_penalty=1.1 (1.5B/7B) or 1.05 (32B) and
        # top_k=20. Resolve and pin them explicitly here (values unchanged
        # from what has always been in effect, this is a logging fix, not a
        # behavior change) so run identity is actually complete and doesn't
        # depend on whatever happens to be cached in HF_HOME.
        ckpt_gen_cfg = self.model.generation_config
        repetition_penalty = getattr(ckpt_gen_cfg, "repetition_penalty", 1.0)
        top_k = getattr(ckpt_gen_cfg, "top_k", 50)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": cfg.max_new_tokens,
            "do_sample": cfg.do_sample,
        }
        if cfg.do_sample:
            gen_kwargs["temperature"] = cfg.temperature
            gen_kwargs["top_p"] = cfg.top_p
            gen_kwargs["repetition_penalty"] = repetition_penalty
            gen_kwargs["top_k"] = top_k

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
                # Inherited from the checkpoint's generation_config.json, not
                # this project's YAML configs, recorded explicitly so a
                # future checkpoint update that changes these can't silently
                # change results without showing up in the logged record.
                "repetition_penalty": gen_kwargs.get("repetition_penalty"),
                "repetition_penalty_source": "checkpoint_generation_config" if cfg.do_sample else None,
                "top_k": gen_kwargs.get("top_k"),
                "top_k_source": "checkpoint_generation_config" if cfg.do_sample else None,
                "chat_template_source": "tokenizer_config" if chat_template else "none_defined",
                "chat_template_hash": chat_template_hash,
                "prompt_delivery_mode": prompt_delivery_mode,
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
            adapter_path=self.adapter_path,
            adapter_hash=self.adapter_hash,
        )