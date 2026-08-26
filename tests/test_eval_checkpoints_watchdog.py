"""Tests for _ProcessWatchdog in scripts/eval_checkpoints.py.

This is the process-external guard added after re-examining job 9315777's
hang: it stalled mid-generate() with zero incremental output for 11.5h,
which _TimeLimitCriteria can't catch (that check only runs between
successfully generated tokens inside generate()'s own loop, a stuck
forward pass never returns control to it). _ProcessWatchdog is a
background thread that force-exits the process on a stale deadline,
independent of the main thread's cooperation.

Runs the watchdog in a real subprocess so its os._exit(99) path can be
exercised without killing the test runner itself.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run_snippet(code: str, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout,
    )


def test_watchdog_fires_when_never_kicked():
    code = (
        "import sys, time; sys.path.insert(0, 'scripts')\n"
        "from eval_checkpoints import _ProcessWatchdog\n"
        "_ProcessWatchdog(timeout_s=1).start()\n"
        "time.sleep(10)\n"          # should never be reached
        "sys.exit(0)\n"
    )
    result = _run_snippet(code, timeout=20)
    assert result.returncode == 99, (
        f"expected watchdog os._exit(99), got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "WATCHDOG" in result.stdout


def test_watchdog_does_not_fire_when_kicked_regularly():
    code = (
        "import sys, time; sys.path.insert(0, 'scripts')\n"
        "from eval_checkpoints import _ProcessWatchdog\n"
        "wd = _ProcessWatchdog(timeout_s=2).start()\n"
        "for _ in range(6):\n"
        "    wd.kick()\n"
        "    time.sleep(0.5)\n"       # 3s of kicks, each well under the 2s deadline
        "wd.stop()\n"
        "sys.exit(0)\n"
    )
    result = _run_snippet(code, timeout=20)
    assert result.returncode == 0, (
        f"watchdog fired despite regular kicks\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_watchdog_stop_prevents_firing():
    code = (
        "import sys, time; sys.path.insert(0, 'scripts')\n"
        "from eval_checkpoints import _ProcessWatchdog\n"
        "wd = _ProcessWatchdog(timeout_s=1).start()\n"
        "wd.stop()\n"
        "time.sleep(3)\n"            # well past the 1s deadline, but stopped
        "sys.exit(0)\n"
    )
    result = _run_snippet(code, timeout=20)
    assert result.returncode == 0, (
        f"watchdog fired after stop()\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_watchdog_disabled_via_zero_timeout_cli_flag():
    """--watchdog-timeout 0 must be honored as "disabled" in main(), not
    passed straight to _ProcessWatchdog (which would fire immediately)."""
    import ast
    source = (ROOT / "scripts" / "eval_checkpoints.py").read_text()
    tree = ast.parse(source)
    main_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            main_src = ast.get_source_segment(source, node)
            break
    assert main_src is not None, "main() not found in eval_checkpoints.py"
    assert "watchdog_timeout > 0" in main_src, (
        "main() must gate _ProcessWatchdog construction on --watchdog-timeout > 0 "
        "so --watchdog-timeout 0 disables it instead of firing immediately"
    )
