"""Google Gemini API wrapper (via the `google-genai` SDK).

Gemini has the most divergent message format of the three providers,
so this wrapper does the most translation. Output shape is still the
same ModelOutput.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from src.models.base import GenerationConfig, Model, ModelOutput
from src.pricing import compute_cost


class GeminiModel(Model):
    provider = "gemini"

    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self.model_id = model_id
        self.model_revision = revision or model_id
        # Reads GEMINI_API_KEY (or GOOGLE_API_KEY) from env.
        self.client = genai.Client()

    def generate(
        self,
        messages: list[dict[str, str]],
        cfg: GenerationConfig,
    ) -> ModelOutput:
        # Gemini uses "model" instead of "assistant" for the assistant role,
        # and takes system instructions separately. Translate.
        system_instruction, contents = _to_gemini_format(messages)

        temperature = 0.0 if not cfg.do_sample else (cfg.temperature or 1.0)

        gen_config = types.GenerateContentConfig(
            max_output_tokens=cfg.max_new_tokens,
            temperature=temperature,
            top_p=cfg.top_p if (cfg.do_sample and cfg.top_p is not None) else None,
            system_instruction=system_instruction,
        )

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config=gen_config,
        )

        response_text = response.text or ""

        canonical_prompt = json.dumps(
            {"system": system_instruction, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
        )

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
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
                "finish_reason": (
                    response.candidates[0].finish_reason.name
                    if response.candidates else None
                ),
            },
            provider=self.provider,
            cost_usd=cost,
        )


def _to_gemini_format(
    messages: list[dict[str, str]],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Translate our role conventions to Gemini's:

    - system → system_instruction (separate field)
    - user → role "user"
    - assistant → role "model"
    """
    system_instruction: str | None = None
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]
        text = msg["content"]
        if role == "system":
            # If multiple system messages, concatenate.
            system_instruction = (
                f"{system_instruction}\n\n{text}" if system_instruction else text
            )
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
    return system_instruction, contents