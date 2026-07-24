"""Build Comparison A (Dynamic vs ULT, RQ1/H1) and Comparison B (ULT vs PLT,
observational contamination signal) tables from real result files.

Writes to analysis/:
  comparison_a_paired.csv       per-model mean Mut@K, Dynamic-L4 vs ULT
  comparison_a_wilcoxon.csv     paired Wilcoxon signed-rank across models (H1)
  comparison_b_paired.csv       per-model mean Mut@K, ULT vs PLT
  comparison_b_wilcoxon.csv     paired Wilcoxon signed-rank across models
  comparison_b_matched_cc.csv   per-CC-band ULT vs PLT mean Mut@K
  COMPARISON_PROVENANCE.md      generation timestamp, git commit, data
                                 sources, and which of the 9 canonical
                                 models are still missing from each table
                                 (never zero-filled — see src/Analysis/
                                 comparison.py's module docstring)

Re-running this script after more data lands (e.g. once the GPT batches in
analysis/SUPERVISOR_HANDOFF_*.md are processed) regenerates all outputs from
whatever is on disk at that time — safe to re-run any time, append-only
result files are never modified.

Usage:
    python scripts/build_comparison_tables.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_matrix import MODEL_SPECS  # noqa: E402
from src.Analysis.comparison import (  # noqa: E402
    DYNAMIC_TIER,
    load_cc_bands,
    matched_cc_table,
    paired_model_table,
    paired_wilcoxon,
)
from src.Analysis.loader import load_records  # noqa: E402

ANALYSIS_DIR = ROOT / "analysis"
CANONICAL_MODELS = [m.model_label for m in MODEL_SPECS]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    ult = load_records("data/results/ult", benchmark="ult")
    plt = load_records("data/results/plt", benchmark="plt")

    dynamic_l4 = dynamic[dynamic["tier"] == DYNAMIC_TIER]

    # --- Comparison A: Dynamic (L4) vs ULT ---------------------------------
    a_paired = paired_model_table(dynamic_l4, ult, label_a="dynamic_l4", label_b="ult")
    a_wilcoxon = paired_wilcoxon(a_paired, label_a="dynamic_l4", label_b="ult")

    # --- Comparison B: ULT vs PLT -------------------------------------------
    b_paired = paired_model_table(ult, plt, label_a="ult", label_b="plt")
    b_wilcoxon = paired_wilcoxon(b_paired, label_a="ult", label_b="plt")

    bands_ult = load_cc_bands("ult", tag="core_400")
    bands_plt = load_cc_bands("plt", tag="core_400")
    b_matched_cc = matched_cc_table(ult, plt, bands_ult, bands_plt)

    a_paired.to_csv(ANALYSIS_DIR / "comparison_a_paired.csv", index=False)
    b_paired.to_csv(ANALYSIS_DIR / "comparison_b_paired.csv", index=False)
    b_matched_cc.to_csv(ANALYSIS_DIR / "comparison_b_matched_cc.csv", index=False)

    import pandas as pd
    pd.DataFrame([vars(a_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_a_wilcoxon.csv", index=False)
    pd.DataFrame([vars(b_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_b_wilcoxon.csv", index=False)

    a_missing = sorted(set(CANONICAL_MODELS) - set(a_paired["model_label"]))
    b_missing = sorted(set(CANONICAL_MODELS) - set(b_paired["model_label"]))

    provenance = f"""# Comparison A/B generation provenance

Generated: {datetime.now(timezone.utc).isoformat()}
Git commit: {_git_commit()}

Sources: data/results/dynamic/*.jsonl (tier={DYNAMIC_TIER} only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — {len(a_paired)}/{len(CANONICAL_MODELS)} models
Missing (no scorable data on one or both sides — NOT zero-filled, simply
absent from comparison_a_paired.csv): {a_missing or "none"}

## Comparison B (ULT vs PLT) — {len(b_paired)}/{len(CANONICAL_MODELS)} models
Missing: {b_missing or "none"}

Pairing unit and CC-band methodology: see src/Analysis/comparison.py's
module docstring.
"""
    (ANALYSIS_DIR / "COMPARISON_PROVENANCE.md").write_text(provenance)

    print(provenance)
    print("Comparison A paired table:")
    print(a_paired.to_string(index=False))
    print("\nComparison A Wilcoxon:", vars(a_wilcoxon))
    print("\nComparison B paired table:")
    print(b_paired.to_string(index=False))
    print("\nComparison B Wilcoxon:", vars(b_wilcoxon))
    print("\nComparison B matched-CC table:")
    print(b_matched_cc.to_string(index=False))


if __name__ == "__main__":
    main()
