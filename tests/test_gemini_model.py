"""Regression test: transient Gemini API errors (429/5xx) must be retried
with backoff rather than crashing the whole job — found in practice when a
503 UNAVAILABLE ("high demand") on gemini-3.1-pro-preview killed a job
25/75 problems in, despite the SDK's own internal retry."""
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


def _mock_response():
    resp = MagicMock()
    resp.text = "ok"
    resp.usage_metadata.prompt_token_count = 1
    resp.usage_metadata.candidates_token_count = 1
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
