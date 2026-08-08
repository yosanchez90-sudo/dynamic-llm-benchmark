"""Regression tests for src/models/gemini_model.py:
1. transient Gemini API errors (429/5xx) must be retried with backoff
   rather than crashing the whole job — found in practice when a 503
   UNAVAILABLE ("high demand") on gemini-3.1-pro-preview killed a job
   25/75 problems in, despite the SDK's own internal retry.
2. cost_usd must include usage_metadata.thoughts_token_count, not just
   candidates_token_count — found 2026-08-08 by reconciling real AI
   Studio billing (~4x this project's own logged cost_usd sum for the
   same window) for gemini-3.1-pro-preview, a thinking-enabled model
   whose internal reasoning tokens are billed separately from the
   visible response but were silently excluded from every cost_usd
   this model ever logged before the fix."""
from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors

from src.models.base import GenerationConfig
from src.models.gemini_model import GeminiModel


def _make_model() -> GeminiModel:
    with patch("src.models.gemini_model.genai.Client"):
        return GeminiModel(model_id="gemini-3.1-pro-preview")


def _api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "boom", "status": "X"}})


def _mock_response(thoughts_token_count=0):
    resp = MagicMock()
    resp.text = "ok"
    resp.usage_metadata.prompt_token_count = 1
    resp.usage_metadata.candidates_token_count = 1
    resp.usage_metadata.thoughts_token_count = thoughts_token_count
    resp.candidates = [MagicMock(finish_reason=MagicMock(name="STOP"))]
    return resp


def test_retries_on_503_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    model = _make_model()
    model.client.models.generate_content.side_effect = [
        _api_error(503), _api_error(503), _mock_response(),
    ]
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.response == "ok"
    assert model.client.models.generate_content.call_count == 3


def test_does_not_retry_on_404_permanent_error():
    """A 404 (model not found / retired) must fail immediately, not burn
    through 5 retries hitting the same permanent wall."""
    model = _make_model()
    model.client.models.generate_content.side_effect = _api_error(404)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    with pytest.raises(errors.APIError):
        model.generate([{"role": "user", "content": "hi"}], cfg)

    assert model.client.models.generate_content.call_count == 1


def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    model = _make_model()
    model.client.models.generate_content.side_effect = _api_error(503)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    with pytest.raises(errors.APIError):
        model.generate([{"role": "user", "content": "hi"}], cfg)

    assert model.client.models.generate_content.call_count == 6  # 1 + 5 retries


def test_cost_includes_thinking_tokens(monkeypatch):
    """gemini-3.1-pro-preview bills thoughts_token_count at the output rate
    (12.00 USD/Mtok, src/pricing.py) in addition to candidates_token_count
    -- cost_usd must reflect both, not just the visible response tokens."""
    model = _make_model()
    model.client.models.generate_content.return_value = _mock_response(thoughts_token_count=1000)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    # 1 prompt tok @ 2.00/Mtok + (1 candidate + 1000 thinking) tok @ 12.00/Mtok
    expected_cost = (1 / 1_000_000) * 2.00 + (1001 / 1_000_000) * 12.00
    assert out.cost_usd == pytest.approx(expected_cost)
    # output_tokens stays "visible response tokens" for cross-provider
    # comparability -- thinking tokens are folded into cost_usd only, not
    # counted here.
    assert out.output_tokens == 1
    assert out.runtime_info["thoughts_token_count"] == 1000


def test_cost_with_zero_thinking_tokens_unaffected(monkeypatch):
    """Non-thinking responses (thoughts_token_count=0/None) must cost exactly
    what candidates_token_count alone implies -- the fix must not inflate
    cost for calls that genuinely have no thinking tokens."""
    model = _make_model()
    model.client.models.generate_content.return_value = _mock_response(thoughts_token_count=0)
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    expected_cost = (1 / 1_000_000) * 2.00 + (1 / 1_000_000) * 12.00
    assert out.cost_usd == pytest.approx(expected_cost)
