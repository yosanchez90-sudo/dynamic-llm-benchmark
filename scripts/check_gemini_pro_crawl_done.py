"""Exit 0 if Gemini 3.1 Pro Preview's Dynamic-benchmark coverage (inst1-4,
L1-L4, the scoped target, inst5 was cut, PROJECT_BRIEF.md Sec 11) is
complete; exit 1 (and print what's still missing) otherwise.

Used by scripts/slurm/run_gemini_daily_crawl.slurm to decide whether to
resubmit itself for another day or stop the chain.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_matrix import load_coverage, TIERS, EXPECTED_PER_CELL  # noqa: E402

LABEL = "gemini-3.1-pro-preview"
SCOPED_INSTANTIATIONS = ("1", "2", "3", "4")  # inst5 deliberately excluded


def main() -> None:
    main_cells, _, _ = load_coverage(ROOT / "data" / "results" / "dynamic")
    total_missing = 0
    rows = []
    for tier in TIERS:
        for inst in SCOPED_INSTANTIATIONS:
            n = len(main_cells.get((LABEL, tier, inst), ()))
            missing = max(EXPECTED_PER_CELL - n, 0)
            total_missing += missing
            rows.append((tier, inst, n, EXPECTED_PER_CELL, missing))

    for tier, inst, n, expected, missing in rows:
        flag = "  <- missing" if missing else ""
        print(f"{tier} inst{inst}: {n}/{expected}{flag}")
    print(f"\nTotal missing (inst1-4 scope): {total_missing}")

    if total_missing == 0:
        print("COMPLETE.")
        sys.exit(0)
    else:
        print("INCOMPLETE.")
        sys.exit(1)


if __name__ == "__main__":
    main()
