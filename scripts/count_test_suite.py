"""Count the test suite's live size: analysis/test_suite_count.csv +
provenance sidecar, read by scripts/build_paper_values.py so
paper/supporting_report/REPORT.md's "N tests" claim is checked by
scripts/check_doc_citations.py like every other number in that document,
instead of silently drifting the way it did across 136/141/145/152 at
different points in this project's history.

Runs `pytest --collect-only -q` (collection only -- no test execution, so
this step stays cheap and side-effect-free like every other
build_thesis_assets.py step) and parses the "N tests collected" summary
line.

Usage:
    python scripts/count_test_suite.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.Analysis.provenance import stamp_block  # noqa: E402

CSV_OUT = ROOT / "analysis" / "test_suite_count.csv"
PROVENANCE_OUT = ROOT / "analysis" / "TEST_SUITE_COUNT_PROVENANCE.md"
_COLLECTED_RE = re.compile(r"(\d+)\s+tests?\s+collected")


def main() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    m = _COLLECTED_RE.search(result.stdout)
    if not m:
        print("ERROR: could not parse a 'N tests collected' line from "
              "`pytest --collect-only -q` output:", file=sys.stderr)
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    collected = int(m.group(1))

    CSV_OUT.write_text(f"collected\n{collected}\n")

    provenance = f"""# Test suite count — provenance

{stamp_block("scripts/count_test_suite.py")}
`pytest --collect-only -q` against `testpaths = ["tests"]`
(pyproject.toml): **{collected} tests collected**.

Collection only, no test executed, no pass/fail claim here. For the
executed-and-passing count, run `pytest -q` directly (README.md's
"Running the tests" section has the CPU-only vs GPU-node split via the
`torch` marker).
"""
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {CSV_OUT.relative_to(ROOT)} ({collected} tests), "
          f"{PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
