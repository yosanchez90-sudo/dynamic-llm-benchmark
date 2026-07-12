"""The test-generation evaluation harness: Exec@K, Cov-S@K, Cov-B@K, Mut@K.

DESIGN DECISIONS (viva-relevant)
-----------------------------------------------------------------
1. SUBPROCESS ISOLATION. Every pytest run happens in its own temp directory
   containing a fresh `under_test.py` + the generated test file, executed in a
   separate `python -m pytest` subprocess with a timeout. No shared interpreter
   state: infinite loops get killed, a crashing mutant can't crash the harness.
   This is the safe model for mutation testing — Cosmic Ray and mutmut both fork
   for the same reason: mutants are deliberately broken code.

2. IMPORT MODE. Every pytest call uses --import-mode=importlib (pytest's own
   recommendation). This avoids sys.path pollution between consecutive runs in
   the same process and is strictly better than the default prepend mode for
   isolated temp directories. It does NOT remove subprocess isolation.

3. PRECOMPUTED MUTANTS (open question #1). Mutants are generated ONCE per
   problem at load time (see data/test_gen.py) and passed in here. The same
   mutant set is reused across all models — necessary for a fair comparison.

4. KILLED DEFINITION. A mutant is KILLED iff the suite PASSES on the original
   and FAILS (or times out) on the mutant. If the suite does not pass on the
   original, mutation score is ill-defined; we record baseline_passed=False and
   mutation_score=None so downstream analysis can exclude it.
   >>> CONFIRM this against ULT's methodology (your decision). <<<

5. PARALLELISM. Mutants for ONE problem are evaluated in a thread pool (Level 1
   parallelism). Threads rather than processes: each worker just coordinates a
   subprocess.run() call (I/O-bound), so threads give the same concurrency
   without forking the CUDA context that LocalModel already loaded — forking
   CUDA causes workers to hang indefinitely on GPU nodes.
   For the full 1,500-problem sweep use SLURM array jobs (Level 2) — see
   test_gen_runner.py and scripts/slurm/run_mutation_array.slurm.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from src.eval.test_gen_problem import Mutant


@dataclass
class ScoreResult:
    exec_ok: bool
    baseline_passed: bool
    statement_coverage: float | None
    branch_coverage: float | None
    mutants_total: int
    mutants_killed: int
    mutants_dropped: int
    mutation_score: float | None
    notes: str = ""


# ---------------------------------------------------------------------------
# Extraction: pull the pytest file out of the model's response
# ---------------------------------------------------------------------------

def extract_test_file(response: str) -> str:
    """Extract a pytest file from a model response.

    Strategy: prefer a fenced ```python block; else take from the first
    import/def to the end of the response.
    """
    fenced = re.search(r"```(?:python|py)?\s*\n(.*?)```", response, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    m = re.search(r"^(import |from |def test_|def )", response, re.MULTILINE)
    return response[m.start():].strip() if m else response.strip()


def sanitize_test_file(test_source: str, fn_name: str) -> str:
    """Remove any reimplementation of fn_name and ensure the import line exists.

    Small models (e.g. 1.5B) sometimes reimplement the function-under-test
    inside the test file instead of importing it from under_test. This causes
    baseline_passed=False because the reimplemented version uses different
    constants and the tests never exercise the real function.

    Two repairs (applied in order):
      1. Strip any top-level `def <fn_name>(...)` block from the test source.
      2. If `from under_test import <fn_name>` is absent, prepend it.

    The repairs are deliberate and recorded — the scorer notes them so the
    tidy record can flag affected rows for sensitivity analysis.
    """
    import ast
    repairs: list[str] = []

    # --- repair 1: remove reimplementation ---
    try:
        tree = ast.parse(test_source)
        lines = test_source.splitlines(keepends=True)
        to_remove: list[tuple[int, int]] = []  # (start_line, end_line) 1-indexed
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                to_remove.append((node.lineno, node.end_lineno))
        if to_remove:
            keep = []
            for i, line in enumerate(lines, 1):
                if any(start <= i <= end for start, end in to_remove):
                    continue
                keep.append(line)
            test_source = "".join(keep)
            repairs.append(f"stripped reimplementation of {fn_name!r}")
    except SyntaxError:
        pass  # unparseable; leave as-is, exec gate will catch it

    # --- repair 2: ensure import ---
    import_line = f"from under_test import {fn_name}"
    if import_line not in test_source:
        test_source = import_line + "\n" + test_source
        repairs.append(f"prepended '{import_line}'")

    return test_source, repairs


# ---------------------------------------------------------------------------
# Low-level: run pytest in an isolated temp dir
# ---------------------------------------------------------------------------

def _write_case(workdir: Path, fn_source: str, test_source: str) -> None:
    """Write function-under-test and test file into a work dir.

    Tests import the function via `from under_test import <fn_name>`.
    Keeping them in separate modules lets us swap in a mutant without
    touching the test file.
    """
    (workdir / "under_test.py").write_text(fn_source)
    (workdir / "test_generated.py").write_text(test_source)


def _run_pytest(workdir: Path, timeout: int, cov: bool = False) -> tuple[int, str]:
    """Run pytest in workdir. Returns (exit_code, stdout+stderr).

    exit code: 0 = all passed, 1 = tests failed, 2+ = collection/usage error,
    -1 = our timeout sentinel.
    """
    cmd = [
        sys.executable, "-m", "pytest", "-q", "--no-header",
        "--import-mode=importlib",   # cleaner imports, still fully isolated
        "-p", "no:cacheprovider",
    ]
    if cov:
        cmd += ["--cov=under_test", "--cov-branch",
                "--cov-report=json:cov.json", "--cov-report="]
    try:
        proc = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def _collect_ok(workdir: Path, timeout: int) -> bool:
    """Exec@K gate: does pytest collect the suite without import error?"""
    cmd = [
        sys.executable, "-m", "pytest", "--collect-only", "-q",
        "--import-mode=importlib",
        "-p", "no:cacheprovider",
    ]
    try:
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True,
                              text=True, timeout=timeout)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _parse_coverage(workdir: Path) -> tuple[float | None, float | None]:
    """Parse coverage.py JSON for statement and branch coverage fractions."""
    cov_path = workdir / "cov.json"
    if not cov_path.exists():
        return None, None
    data = json.loads(cov_path.read_text())
    totals = data.get("totals", {})
    n_stmt = totals.get("num_statements", 0)
    stmt = (totals.get("covered_lines", 0) / n_stmt) if n_stmt else None
    n_branch = totals.get("num_branches", 0)
    branch = (totals.get("covered_branches", 0) / n_branch) if n_branch else None
    return stmt, branch


# ---------------------------------------------------------------------------
# Mutation: module-level worker so multiprocessing.Pool can pickle it
# ---------------------------------------------------------------------------

def _evaluate_mutant(args: tuple[str, str, int]) -> str:
    """Run the test suite against ONE mutant in an isolated temp dir.

    args = (mutant_source, test_source, timeout).
    Returns "killed", "survived", or "dropped" (mutant didn't import cleanly).
    Only called when the baseline already passed.
    """
    mutant_source, test_source, timeout = args
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        _write_case(wd, mutant_source, test_source)
        chk = subprocess.run(
            [sys.executable, "-c", "import under_test"],
            cwd=wd, capture_output=True, text=True, timeout=timeout,
        )
        if chk.returncode != 0:
            return "dropped"
        code, _ = _run_pytest(wd, timeout)
        return "killed" if code != 0 else "survived"


# ---------------------------------------------------------------------------
# Top-level: score one (function, test-file, mutants) triple
# ---------------------------------------------------------------------------

def score_problem(
    fn_source: str,
    fn_name: str,
    test_source: str,
    mutants: list[Mutant],
    timeout: int = 30,
    n_workers: int = 4,
) -> ScoreResult:
    """Compute Exec@K gate, coverage, and mutation score for one response."""

    # 1. Exec gate -----------------------------------------------------------
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        _write_case(wd, fn_source, test_source)
        exec_ok = _collect_ok(wd, timeout)
        if not exec_ok:
            return ScoreResult(False, False, None, None,
                               len(mutants), 0, 0, None,
                               notes="exec gate failed (collection error)")

        # 2. Baseline + coverage on the original function --------------------
        base_code, _ = _run_pytest(wd, timeout, cov=True)
        baseline_passed = (base_code == 0)
        stmt_cov, branch_cov = _parse_coverage(wd)

    if not baseline_passed:
        return ScoreResult(True, False, stmt_cov, branch_cov,
                           len(mutants), 0, 0, None,
                           notes="suite failed on original; Mut@K excluded")

    # 3. Mutation scoring (parallel over mutants within this problem) --------
    # Thread pool, not process pool: workers only coordinate subprocess.run()
    # calls (I/O-bound). Using processes would fork the CUDA context and cause
    # workers to hang on GPU nodes.
    work = [(m.source, test_source, timeout) for m in mutants]
    if work:
        per_task_timeout = timeout + 5  # hard ceiling above subprocess timeout
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            futures = {ex.submit(_evaluate_mutant, arg): i for i, arg in enumerate(work)}
            verdicts_map: dict[int, str] = {}
            for fut in as_completed(futures, timeout=per_task_timeout * len(work)):
                verdicts_map[futures[fut]] = fut.result()
        verdicts = [verdicts_map[i] for i in range(len(work))]
    else:
        verdicts = []

    killed = verdicts.count("killed")
    dropped = verdicts.count("dropped")
    scored = len(verdicts) - dropped
    mut_score = (killed / scored) if scored else None

    return ScoreResult(
        exec_ok=True,
        baseline_passed=True,
        statement_coverage=stmt_cov,
        branch_coverage=branch_cov,
        mutants_total=len(mutants),
        mutants_killed=killed,
        mutants_dropped=dropped,
        mutation_score=mut_score,
    )
