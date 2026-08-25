"""Google Gemini API wrapper (via the `google-genai` SDK).

Gemini has the most divergent message format of the three providers,
so this wrapper does the most translation. Output shape is still the
same ModelOutput.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import errors, types

from src.models.base import GenerationConfig, Model, ModelOutput
from src.pricing import compute_cost

# Transient (retryable) HTTP codes: 429 rate limit, 5xx server-side (e.g. the
# 503 UNAVAILABLE "high demand" seen in practice on gemini-3.1-pro-preview —
# the SDK's own internal retry wasn't enough to ride it out and crashed the
# whole job with 25/75 problems done). Everything else (400 bad request, 404
# model not found, etc.) is a permanent error — retrying wastes time hitting
# the same wall. Gemini has no batch API equivalent to OpenAI's, so this
# retry loop is the only mitigation rather than a stopgap before batch infra.
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5
_BASE_BACKOFF_SECONDS = 2.0


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

        response = self._generate_with_backoff(contents, gen_config)

        response_text = response.text or ""

        canonical_prompt = json.dumps(
            {"system": system_instruction, "messages": messages},
            sort_keys=True,
            ensure_ascii=False,
        )

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
        # Thinking-enabled Gemini models (e.g. gemini-3.1-pro-preview) bill
        # internal reasoning tokens separately from the visible response, at
        # the same output-token rate (ai.google.dev/gemini-api/docs/pricing)
        # -- the SDK exposes this as usage_metadata.thoughts_token_count,
        # which candidates_token_count does NOT include. Found 2026-08-08:
        # real AI Studio billing (£34.53 over Jul11-Aug7) ran ~4x this
        # project's own logged cost_usd sum for the same window -- this is
        # why. Cost must count thinking tokens even though the logged
        # `output_tokens` field (kept as "visible response tokens" for
        # comparability with the non-thinking providers) does not.
        thoughts_tokens = usage.thoughts_token_count or 0
        cost = compute_cost(self.model_id, input_tokens, output_tokens + thoughts_tokens)

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
                # Preview-alias model IDs (e.g. "gemini-3.1-pro-preview") can
                # point to a different underlying checkpoint over time --
                # model_version/model_status are the SDK's own audit trail
                # for which actual snapshot served this response, distinct
                # from the (fixed, requested) self.model_id above. Added
                # 2026-08-05 for the multi-day Gemini Pro crawl, where a
                # silent mid-crawl version change would otherwise be
                # invisible in the logged data.
                "model_version": getattr(response, "model_version", None),
                "model_status": getattr(response, "model_status", None),
                # Preserved for audit even though it's already folded into
                # cost_usd above -- lets a future reconciliation pass verify
                # the fix against real per-row thinking-token counts instead
                # of just the account-level total.
                "thoughts_token_count": thoughts_tokens,
            },
            provider=self.provider,
            cost_usd=cost,
        )

    def _generate_with_backoff(self, contents, gen_config):
        attempt = 0
        while True:
            try:
                return self.client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=gen_config,
                )
            except errors.APIError as exc:
                attempt += 1
                if exc.code not in _RETRYABLE_CODES or attempt > _MAX_RETRIES:
                    raise
                wait = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"[GeminiModel] {self.model_id} got {exc.code} "
                      f"(attempt {attempt}/{_MAX_RETRIES}), retrying in {wait:.0f}s...",
                      flush=True)
                time.sleep(wait)


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