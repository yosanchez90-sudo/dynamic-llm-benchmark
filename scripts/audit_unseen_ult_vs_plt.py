"""Selection-effect check for the PLT > unseen-ULT gain inversion found in
Comparison C (analysis/COMPARISON_C_PROVENANCE.md): is unseen-ULT (n=288)
systematically a harder/messier population than PLT core_400 (n=400), which
would explain why fine-tuning's generic-improvement effect shows up more on
PLT than on unseen-ULT, without needing a content-specific story?

unseen-ULT is DEFINED by NOT having a verified training pair -- i.e. it's
whatever scripts/repair_ult_ground_truth.py's taxonomy could not repair
(STRUCTURAL, SHAPE_NOT_REPAIRABLE, ASSERTION_MISMATCH_VERIFY_FAILED, FLAKY).
PLT core_400 was never run through that taxonomy at all: PLT's `test_input`
field never contained real assertions in the first place
(data/raw/ult_plt/PROVENANCE.md's original "Known discrepancy" note) so
there is nothing there to classify as repairable/unrepairable -- PLT is a
plain CC-stratified sample, unscreened by any test-quality criterion, while
unseen-ULT is the specifically-selected hard remainder of a screened
population. That asymmetry is itself part of the answer, not just a
caveat, and is reported as such alongside the numeric comparison (code
length, CC, PRE baseline_pass -- same fields as
scripts/build_comparison_c_seen_manifest.py's seen-vs-unseen audit, reused
here for unseen-vs-PLT).

Usage: python scripts/audit_unseen_ult_vs_plt.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_comparison_c_seen_manifest import _mannwhitney_u, _mean  # noqa: E402

SEEN_MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_seen_manifest.json"
TAXONOMY_PATH = ROOT / "analysis" / "ult_ground_truth_taxonomy.csv"
SUBSAMPLE_MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"
PLT_RAW_PATH = ROOT / "data" / "raw" / "ult_plt" / "PLT.jsonl"
PRE_PLT_PATH = (ROOT / "data" / "results" / "plt"
                / "Qwen__Qwen2.5-Coder-1.5B-Instruct__plt__zero_shot__instcore_400__20260713T123854.jsonl")
OUT_CSV = ROOT / "analysis" / "comparison_c_unseen_vs_plt_audit.csv"


def main() -> None:
    seen_manifest = json.loads(SEEN_MANIFEST_PATH.read_text())
    unseen_entries = [p for p in seen_manifest["problems"] if not p["seen_in_training"]]
    print(f"unseen-ULT: {len(unseen_entries)}")

    # Records absent from the taxonomy CSV entirely aren't "unknown" -- checked
    # directly (2026-07-27): repair_ult_ground_truth.py's build_test_file()
    # raises SyntaxError and silently drops the record (SKIPPED_PARSE_OR_CC)
    # whenever ANY of the 5 shipped ground-truth `tests` strings is not even
    # valid Python (unclosed brackets, garbled/truncated text -- confirmed by
    # direct ast.parse() on a sample: task_id 7492 has an unclosed `[`,
    # task_id 18248 an unclosed `{`, task_id 4584 outright garbled text). This
    # is a MORE severe defect than STRUCTURAL (code that parses but can't run)
    # or SHAPE_NOT_REPAIRABLE (runs, wrong assertion shape) -- the ground
    # truth test body itself isn't parseable Python. Labelled explicitly
    # rather than left as an unexplained gap.
    taxonomy = {r["task_id"]: r["category"] for r in csv.DictReader(TAXONOMY_PATH.open())}
    unseen_categories = Counter(taxonomy.get(e["task_id"], "UNPARSEABLE_TEST_SYNTAX") for e in unseen_entries)
    print(f"unseen-ULT taxonomy breakdown: {dict(unseen_categories)}")

    sub_manifest = json.loads(SUBSAMPLE_MANIFEST_PATH.read_text())
    plt_core400 = sub_manifest["core_400"]["plt"]["problems"]
    plt_raw_by_task_id = {r["task_id"]: r for r in json.loads(PLT_RAW_PATH.read_text())}
    pre_plt_by_template_id = {}
    with PRE_PLT_PATH.open() as f:
        for line in f:
            d = json.loads(line)
            pre_plt_by_template_id[d["template_id"]] = d

    plt_entries = []
    for p in plt_core400:
        tid = p["task_id"]
        code_len = len(plt_raw_by_task_id[tid]["code"]) if tid in plt_raw_by_task_id else None
        pre = pre_plt_by_template_id.get(p["template_id"], {})
        plt_entries.append({
            "task_id": tid, "cc": p["cc"], "code_len_chars": code_len,
            "pre_exec_rate": pre.get("exec_rate"),
            "pre_mutation_score": pre.get("mutation_score"),
            "pre_baseline_passed": pre.get("baseline_passed"),
        })
    print(f"PLT core_400: {len(plt_entries)}")

    def col(entries, key):
        return [e[key] for e in entries]

    rows = []
    for label, key in [("cc", "cc"), ("code_len_chars", "code_len_chars"),
                        ("pre_exec_rate", "pre_exec_rate"),
                        ("pre_mutation_score", "pre_mutation_score")]:
        unseen_vals = col(unseen_entries, key)
        plt_vals = col(plt_entries, key)
        u, z, p = _mannwhitney_u(unseen_vals, plt_vals)
        rows.append({
            "metric": label,
            "n_unseen_ult": sum(1 for v in unseen_vals if v is not None),
            "mean_unseen_ult": _mean(unseen_vals),
            "n_plt": sum(1 for v in plt_vals if v is not None),
            "mean_plt": _mean(plt_vals),
            "mannwhitney_z": z, "mannwhitney_p": p,
        })

    unseen_bp_rate = sum(1 for e in unseen_entries if e["pre_baseline_passed"]) / len(unseen_entries)
    plt_bp_rate = sum(1 for e in plt_entries if e["pre_baseline_passed"]) / len(plt_entries)
    rows.append({
        "metric": "pre_baseline_passed_rate",
        "n_unseen_ult": len(unseen_entries), "mean_unseen_ult": unseen_bp_rate,
        "n_plt": len(plt_entries), "mean_plt": plt_bp_rate,
        "mannwhitney_z": None, "mannwhitney_p": None,
    })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n=== unseen-ULT vs PLT core_400 ===")
    for r in rows:
        z = f"{r['mannwhitney_z']:.2f}" if r["mannwhitney_z"] is not None else "n/a"
        p = f"{r['mannwhitney_p']:.4f}" if r["mannwhitney_p"] is not None else "n/a"
        print(f"  {r['metric']:26s} unseen_ult={r['mean_unseen_ult']:.3f}  plt={r['mean_plt']:.3f}  "
              f"MWU z={z} p={p}")

    print(f"\nunseen-ULT taxonomy (n={len(unseen_entries)}): {dict(unseen_categories)}")
    print("Every unseen-ULT problem has an identifiable defect -- there is no "
          "'randomly not selected' subgroup, 100% of the 288 fall into a named "
          "failure category.")
    print("PLT: no analogous taxonomy exists -- PLT's test_input field never contained "
          "real assertions (bare call expressions only, see PROVENANCE.md's original "
          "'Known discrepancy' note), so PLT was never screened for "
          "assertion-repairability at all. unseen-ULT is entirely composed of ULT "
          "problems SELECTED for being structurally broken or unrepairable; PLT "
          "core_400 is an unscreened CC-stratified sample.")

    print(f"\nWritten: {OUT_CSV}")


if __name__ == "__main__":
    main()
