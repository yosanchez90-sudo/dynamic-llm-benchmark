"""OpenAI Chat Completions API wrapper.

Translates GenerationConfig to OpenAI's API params, captures usage,
computes cost. Mirrors the AnthropicModel structure exactly.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from openai import BadRequestError, OpenAI

from src.models.base import GenerationConfig, Model, ModelOutput
from src.pricing import compute_cost


class OpenAIModel(Model):
    provider = "openai"

    # 3 requests/minute rate limit → minimum 21s between calls.
    _MIN_INTERVAL: float = 21.0

    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self.model_id = model_id
        self.model_revision = revision or model_id
        self.client = OpenAI()  # reads OPENAI_API_KEY from env
        self._last_call_t: float = 0.0  # monotonic seconds; 0 = never called
        self._temperature_supported: bool = True  # set False on first 400 error

    def generate(
        self,
        messages: list[dict[str, str]],
        cfg: GenerationConfig,
    ) -> ModelOutput:
        # Enforce rate limit before every call (skips sleep on the first call).
        wait = self._MIN_INTERVAL - (time.monotonic() - self._last_call_t)
        if wait > 0:
            time.sleep(wait)

        # OpenAI accepts the messages list directly, including a leading
        # system role — no need to split.
        temperature = 0.0 if not cfg.do_sample else (cfg.temperature or 1.0)

        api_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_completion_tokens": cfg.max_new_tokens,
            "temperature": temperature,
        }
        if cfg.do_sample and cfg.top_p is not None:
            api_kwargs["top_p"] = cfg.top_p

        if not self._temperature_supported:
            api_kwargs.pop("temperature", None)
            api_kwargs.pop("top_p", None)

        try:
            response = self.client.chat.completions.create(**api_kwargs)
        except BadRequestError as exc:
            if "temperature" in str(exc) and self._temperature_supported:
                # Model does not accept custom temperature (e.g. gpt-5-mini).
                # Disable it for all subsequent calls and retry immediately.
                self._temperature_supported = False
                print(
                    f"[OpenAIModel] {self.model_id} rejected temperature; "
                    "falling back to model default for all calls.",
                    flush=True,
                )
                api_kwargs.pop("temperature", None)
                api_kwargs.pop("top_p", None)
                response = self.client.chat.completions.create(**api_kwargs)
            else:
                raise
        self._last_call_t = time.monotonic()
        choice = response.choices[0]
        response_text = choice.message.content or ""

        canonical_prompt = json.dumps(
            {"messages": messages},
            sort_keys=True,
            ensure_ascii=False,
        )

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
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
                "temperature": temperature,
                "top_p": cfg.top_p,
                "seed": cfg.seed,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            runtime_info={
                "hostname": os.uname().nodename,
                "api_response_id": response.id,
                "finish_reason": choice.finish_reason,
                "system_fingerprint": getattr(response, "system_fingerprint", None),
            },
            provider=self.provider,
            cost_usd=cost,
        )