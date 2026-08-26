"""Regression test: logged generation_config must reflect what was actually
sent to the API, not the nominal config values, same bug class fixed in
anthropic_model.py. OpenAIModel pops temperature/top_p and retries when a
model rejects them (e.g. gpt-5-mini); the log must follow."""
from unittest.mock import MagicMock, patch

from src.models.base import GenerationConfig
from src.models.openai_model import OpenAIModel


def _make_model() -> OpenAIModel:
    with patch("src.models.openai_model.OpenAI"):
        model = OpenAIModel(model_id="gpt-5-mini-2025-08-07")
    model._last_call_t = 0.0
    return model


def _mock_response():
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content="ok"), finish_reason="stop")]
    resp.usage.prompt_tokens = 1
    resp.usage.completion_tokens = 1
    resp.id = "resp-1"
    resp.system_fingerprint = None
    return resp


def test_logged_config_matches_normal_request():
    model = _make_model()
    model.client.chat.completions.create.return_value = _mock_response()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["temperature"] == 0.2
    assert out.generation_config["top_p"] == 1.0


def test_logged_config_reflects_temperature_rejection_retry():
    """After a model rejects temperature and the code retries without it,
    the logged config must show null, not the nominal 0.2. It was never
    actually sent on the successful call."""
    from openai import BadRequestError

    model = _make_model()

    bad_request = BadRequestError(
        message="temperature is not supported with this model",
        response=MagicMock(status_code=400),
        body={"error": {"message": "temperature is not supported with this model"}},
    )
    model.client.chat.completions.create.side_effect = [bad_request, _mock_response()]

    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)
    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["temperature"] is None
    assert out.generation_config["top_p"] is None
    # And the actual retried call must not have included them either.
    second_call_kwargs = model.client.chat.completions.create.call_args_list[1].kwargs
    assert "temperature" not in second_call_kwargs
    assert "top_p" not in second_call_kwargs
