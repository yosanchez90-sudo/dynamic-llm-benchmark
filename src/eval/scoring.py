"""Extract code from a model response and check if it passes tests."""
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    passed: bool
    error: str | None
    extracted_code: str


def extract_code(text: str) -> str:
    """Best-effort extraction of Python code from a model response.

    Strategy:
      1. If a ```python ... ``` fence exists, use its contents.
      2. Otherwise, start at the first `def`/`class`/`import`/`from` line
         and stop when an unindented line clearly looks like prose.

    This is a heuristic. Real benchmark harnesses are more sophisticated.
    """
    fenced = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    lines = text.split("\n")
    code_lines: list[str] = []
    started = False

    code_starters = re.compile(r"^(def |class |import |from |@)")
    code_keywords = re.compile(
        r"^(def |class |import |from |@|return|if |elif |else|for |while |"
        r"try|except|finally|with |raise |yield |assert |pass|break|"
        r"continue|print|#)"
    )

    for line in lines:
        stripped = line.strip()

        if not started:
            if code_starters.match(stripped):
                started = True
                code_lines.append(line)
            continue

        # Already in code. Detect end-of-code: an unindented line that
        # looks like English prose, not a Python statement.
        is_unindented = line == line.lstrip() and stripped != ""
        looks_like_prose = (
            is_unindented
            and " " in stripped
            and not code_keywords.match(stripped)
            and "=" not in stripped[:30]      # not an assignment
            and not stripped.endswith(":")    # not a block header
        )
        if looks_like_prose:
            break
        code_lines.append(line)

    return "\n".join(code_lines).strip() if code_lines else text.strip()


def run_tests(generated_code: str, test_code: str, timeout: int = 10) -> TestResult:
    """Run generated code + tests in a subprocess. Returns pass/fail.

    The subprocess gives us isolation (a crash doesn't kill our runner)
    and timeout (infinite loops get killed).
    """
    program = generated_code + "\n\n" + test_code

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(program)
        path = Path(f.name)

    try:
        result = subprocess.run(
            ["python", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return TestResult(True, None, generated_code)
        return TestResult(False, result.stderr.strip(), generated_code)
    except subprocess.TimeoutExpired:
        return TestResult(False, f"Timeout after {timeout}s", generated_code)
    finally:
        path.unlink(missing_ok=True)