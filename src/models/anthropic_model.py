"""Anthropic Claude API wrapper.

Same `generate()` interface as LocalModel. Translates GenerationConfig
to Anthropic's API parameters, captures token usage, computes cost.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from anthropic import Anthropic

from src.models.base import GenerationConfig, Model, ModelOutput
from src.pricing import compute_cost


class AnthropicModel(Model):
    provider = "anthropic"

    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self.model_id = model_id
        # For closed APIs, "revision" is the model snapshot string itself,
        # because the provider controls versioning. Keep the same field
        # name for shape compatibility with LocalModel.
        self.model_revision = revision or model_id
        self.client = Anthropic()  # reads ANTHROPIC_API_KEY from env

    def generate(
        self,
        messages: list[dict[str, str]],
        cfg: GenerationConfig,
    ) -> ModelOutput:
        # Anthropic separates system prompts from the messages list.
        system_msg, user_messages = _split_system(messages)

        # Anthropic accepts temperature in [0, 1]; we treat do_sample=False
        # as "as deterministic as the API allows" (temperature=0).
        # NOTE: even at temp=0, closed APIs are NOT bit-deterministic.
        temperature = 0.0 if not cfg.do_sample else (cfg.temperature or 1.0)

        api_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "max_tokens": cfg.max_new_tokens,
            "messages": user_messages,
            "temperature": temperature,
        }
        if system_msg:
            api_kwargs["system"] = system_msg
        # Some Claude models 400 if both temperature and top_p are set
        # ("cannot both be specified for this model"), found running the
        # Haiku 4.5 pilot. temperature is this project's pinned methodological
        # knob (PROJECT_BRIEF.md 5.4); top_p=1.0 in every config here is a
        # mathematical no-op (no truncation) anyway, so only send top_p when
        # it's an actual constraint (<1.0), and drop temperature in that case
        # to respect the model's "only one" rule.
        if cfg.do_sample and cfg.top_p is not None and cfg.top_p < 1.0:
            api_kwargs["top_p"] = cfg.top_p
            del api_kwargs["temperature"]

        response = self.client.messages.create(**api_kwargs)

        # Concatenate any text content blocks (usually just one).
        text_parts = [b.text for b in response.content if b.type == "text"]
        response_text = "".join(text_parts)

        # Build a "prompt" string for hashing. We serialise the messages
        # deterministically. Closed APIs don't expose the literal tokenised
        # prompt, so we hash the JSON of what we sent.
        canonical_prompt = json.dumps(
            {"system": system_msg, "messages": user_messages},
            sort_keys=True,
            ensure_ascii=False,
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = compute_cost(self.model_id, input_tokens, output_tokens)

        return ModelOutput(
            prompt=canonical_prompt,
            prompt_hash=hashlib.sha256(canonical_prompt.encode()).hexdigest(),
            response=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_id=self.model_id,
            model_revision=self.model_revision,
            generation_config={
                "max_new_tokens": cfg.max_new_tokens,
                "do_sample": cfg.do_sample,
                # Log what was actually sent, not the config's nominal values —
                # api_kwargs is the source of truth since temperature/top_p are
                # mutually exclusive on this API (see above).
                "temperature": api_kwargs.get("temperature"),
                "top_p": api_kwargs.get("top_p"),
                "seed": cfg.seed,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            runtime_info={
                "hostname": os.uname().nodename,
                "api_response_id": response.id,
                "stop_reason": response.stop_reason,
            },
            provider=self.provider,
            cost_usd=cost,
        )


def _split_system(
    messages: list[dict[str, str]],
) -> tuple[str | None, list[dict[str, str]]]:
    """Extract a leading system message; Anthropic API takes it separately."""
    if messages and messages[0]["role"] == "system":
        return messages[0]["content"], messages[1:]
    return None, list(messages)