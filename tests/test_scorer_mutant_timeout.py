"""Regression test: a subprocess.TimeoutExpired on the import-check inside
_evaluate_mutant must be treated as a dropped mutant, not propagate and
crash the whole job. Found in production: 4 separate SLURM jobs (the same
code path as scripts/eval_checkpoints.py's known stuck-subprocess pattern,
but a different call site) died mid-run with subprocess.TimeoutExpired:
'import under_test' after 30s, losing all remaining problems in that job
despite results being written incrementally up to that point.

_run_pytest and _collect_ok already caught this correctly; _evaluate_mutant
was the one call site that didn't."""
from unittest.mock import patch
import subprocess

from src.eval.test_gen_scorer import _evaluate_mutant


def test_import_check_timeout_returns_dropped_not_raise():
    with patch(
        "src.eval.test_gen_scorer.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["python", "-c", "import under_test"], timeout=30),
    ):
        verdict = _evaluate_mutant(("def f(): return 1\n", "def test_f(): pass\n", 30))

    assert verdict == "dropped"


def test_import_check_normal_failure_still_returns_dropped():
    """Non-timeout import failures (returncode != 0) already worked --
    confirm the fix didn't change that path."""
    import unittest.mock as mock
    fake_proc = mock.MagicMock(returncode=1)
    with patch("src.eval.test_gen_scorer.subprocess.run", return_value=fake_proc):
        verdict = _evaluate_mutant(("def f(): return 1\n", "def test_f(): pass\n", 30))

    assert verdict == "dropped"
