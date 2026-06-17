"""Abstract base types shared by all model providers.

Defines the single source of truth for GenerationConfig, ModelOutput, and
the Model interface so that the runner can be provider-agnostic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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
    """One model response with full provenance.

    Fields required by every provider (local + API) so the runner works
    uniformly. API-only fields (cost_usd) are None for local models.
    """
    prompt: str
    prompt_hash: str
    response: str
    input_tokens: int
    output_tokens: int
    model_id: str
    model_revision: str
    generation_config: dict[str, Any]
    timestamp: str
    runtime_info: dict[str, Any]
    provider: str = ""
    cost_usd: float | None = None


class Model(ABC):
    """Common interface for all model providers."""

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        cfg: GenerationConfig,
    ) -> ModelOutput: ...
