"""Regression test for the temperature/top_p mutual-exclusion bug found
running the Claude Haiku 4.5 pilot: some Claude models 400 if both
temperature and top_p are set on the same request ("cannot both be
specified for this model")."""
from unittest.mock import MagicMock, patch

from src.models.anthropic_model import AnthropicModel
from src.models.base import GenerationConfig


def _make_model() -> AnthropicModel:
    with patch("src.models.anthropic_model.Anthropic"):
        return AnthropicModel(model_id="claude-haiku-4-5-20251001")


def _mock_response():
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text="ok")]
    resp.usage.input_tokens = 1
    resp.usage.output_tokens = 1
    resp.id = "resp-1"
    resp.stop_reason = "end_turn"
    return resp


def test_top_p_1_0_omits_top_p_keeps_temperature():
    """top_p=1.0 (every config in this repo) is a mathematical no-op —
    must not be sent alongside temperature, since the API now rejects that
    combination for some models."""
    model = _make_model()
    model.client.messages.create.return_value = _mock_response()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    model.generate([{"role": "user", "content": "hi"}], cfg)

    kwargs = model.client.messages.create.call_args.kwargs
    assert "top_p" not in kwargs
    assert kwargs["temperature"] == 0.2


def test_top_p_below_1_sends_top_p_drops_temperature():
    """A genuine top_p constraint (<1.0) is respected — and temperature is
    dropped to satisfy the API's mutual-exclusion rule."""
    model = _make_model()
    model.client.messages.create.return_value = _mock_response()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=0.9)

    model.generate([{"role": "user", "content": "hi"}], cfg)

    kwargs = model.client.messages.create.call_args.kwargs
    assert kwargs["top_p"] == 0.9
    assert "temperature" not in kwargs


def test_logged_generation_config_matches_what_was_sent():
    """generation_config in the returned ModelOutput must reflect the
    actual API request, not the config's nominal values — a logged top_p
    that was never sent would silently misrepresent run identity."""
    model = _make_model()
    model.client.messages.create.return_value = _mock_response()
    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0)

    out = model.generate([{"role": "user", "content": "hi"}], cfg)

    assert out.generation_config["temperature"] == 0.2
    assert out.generation_config["top_p"] is None
