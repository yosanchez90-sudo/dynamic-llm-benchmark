"""Regression tests for scripts/run_gemini_daily_crawl.py's
_run_config_with_retries, found 2026-08-09/10 (jobs 9587710, 9590545)
both crashing the ENTIRE day's crawl on a persistent 5xx (Gemini's own
"high demand" 503) on one specific problem (L4-matrix-001/L4-mega-001)
after GeminiModel's internal 5-retry/62s backoff was exhausted, wasting
~95% of that day's request budget since the old code treated ANY non-429
APIError as immediately fatal. Confirmed empirically (resuming the same
config a day later got past the exact failure point before hitting the
same class of error again) that this is transient, not a permanent block.
These tests cover the fixed retry-then-defer-to-next-config behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from google.genai import errors

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_gemini_daily_crawl as crawl  # noqa: E402


def _api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "boom", "status": "X"}})


def test_succeeds_on_first_attempt():
    run_fn = MagicMock(return_value=Path("out.jsonl"))
    sleep_fn = MagicMock()

    result_path, quota_exhausted = crawl._run_config_with_retries(
        {}, "cfg.yaml", run_fn, sleep_fn=sleep_fn,
    )

    assert result_path == Path("out.jsonl")
    assert quota_exhausted is False
    assert run_fn.call_count == 1
    sleep_fn.assert_not_called()


def test_429_stops_immediately_no_retry():
    run_fn = MagicMock(side_effect=_api_error(429))
    sleep_fn = MagicMock()

    result_path, quota_exhausted = crawl._run_config_with_retries(
        {}, "cfg.yaml", run_fn, sleep_fn=sleep_fn,
    )

    assert result_path is None
    assert quota_exhausted is True
    assert run_fn.call_count == 1  # no retries burned on a quota stop
    sleep_fn.assert_not_called()


def test_transient_503_retries_then_succeeds():
    """This is the exact real-world shape: a couple of 503s, then a
    successful call once the transient condition clears."""
    run_fn = MagicMock(side_effect=[_api_error(503), _api_error(503), Path("out.jsonl")])
    sleep_fn = MagicMock()

    result_path, quota_exhausted = crawl._run_config_with_retries(
        {}, "cfg.yaml", run_fn, sleep_fn=sleep_fn,
    )

    assert result_path == Path("out.jsonl")
    assert quota_exhausted is False
    assert run_fn.call_count == 3
    assert sleep_fn.call_count == 2
    sleep_fn.assert_called_with(crawl.CONFIG_RETRY_PAUSE_SECONDS)


def test_persistent_503_defers_to_next_config_not_crash():
    """The actual bug: retries exhausted on a persistent 5xx must defer
    (return None, False) so the caller moves to the NEXT config, not raise
    and crash the whole script's remaining budget for the day."""
    run_fn = MagicMock(side_effect=_api_error(503))
    sleep_fn = MagicMock()

    result_path, quota_exhausted = crawl._run_config_with_retries(
        {}, "cfg.yaml", run_fn, sleep_fn=sleep_fn,
    )

    assert result_path is None
    assert quota_exhausted is False  # NOT a daily stop, caller should continue to next config
    assert run_fn.call_count == crawl.CONFIG_RETRY_ATTEMPTS
    assert sleep_fn.call_count == crawl.CONFIG_RETRY_ATTEMPTS - 1


def test_non_api_error_propagates_immediately():
    """A genuinely unexpected error (not a Gemini APIError at all) must
    still crash loudly. This fix only tolerates the specific "retryable
    HTTP code exhausted its own retries" case, not arbitrary failures."""
    run_fn = MagicMock(side_effect=ValueError("something actually broken"))
    sleep_fn = MagicMock()

    with pytest.raises(ValueError):
        crawl._run_config_with_retries({}, "cfg.yaml", run_fn, sleep_fn=sleep_fn)

    assert run_fn.call_count == 1
    sleep_fn.assert_not_called()
