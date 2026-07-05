"""Build a Model from config. The single place that knows about providers."""
from __future__ import annotations

from typing import Any

import torch

from src.models.anthropic_model import AnthropicModel
from src.models.base import Model
from src.models.gemini_model import GeminiModel
from src.models.local import LocalModel
from src.models.openai_model import OpenAIModel


_DTYPE_MAP = {
    "bfloat16": torch.bfloat16,
    "float16": torch.float16,
    "float32": torch.float32,
}


def build_model(model_config: dict[str, Any]) -> Model:
    provider = model_config["provider"]

    if provider == "local":
        return LocalModel(
            model_id=model_config["id"],
            revision=model_config.get("revision"),
            dtype=_DTYPE_MAP[model_config.get("dtype", "bfloat16")],
            adapter_path=model_config.get("adapter_path"),   # None for baseline runs
        )

    if provider == "anthropic":
        return AnthropicModel(
            model_id=model_config["id"],
            revision=model_config.get("revision"),
        )

    if provider == "openai":
        return OpenAIModel(
            model_id=model_config["id"],
            revision=model_config.get("revision"),
        )

    if provider == "gemini":
        return GeminiModel(
            model_id=model_config["id"],
            revision=model_config.get("revision"),
        )

    raise ValueError(
        f"Unknown provider: {provider}. "
        f"Expected one of: local, anthropic, openai, gemini."
    )