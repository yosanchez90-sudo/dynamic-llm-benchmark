"""Comparison C seen/unseen manifest + confounder audit for core_400 ULT.

The repair pipeline (scripts/repair_ult_ground_truth.py) only reaches
verified-training-pair status for 112/400 (28.0%) of core_400's ULT
problems -- far short of "every evaluated problem guaranteed seen." Decided
(2026-07-25): proceed with the 1,017-record verified training set as-is,
and analyse core_400 POST results split by seen-in-training vs not, instead
of pretending full coverage. This script:

  1. Writes data/raw/ult_plt/comparison_c_seen_manifest.json -- for every
     core_400 ULT task_id: whether it has a verified training pair (and if
     so, which repair category), fixed once training data is frozen so
     later re-runs of the repair pipeline can't silently redefine "seen"
     for an experiment already in flight.
  2. Confounder audit: compares the seen (112) vs unseen (288) split on CC,
     code length, and the ALREADY-LANDED Qwen-1.5B PRE-baseline eval
     (data/results/ult/.../instcore_400/...) -- exec_rate and
     mutation_score. DiD differencing plus the Dynamic-benchmark control
     already address most difficulty-confound concerns, but the numbers
     should be visible, not assumed.

Usage:
    python scripts/build_comparison_c_seen_manifest.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"
ULT_RAW_PATH = ROOT / "data" / "raw" / "ult_plt" / "ULT.jsonl"
TRAIN_PATH = ROOT / "data" / "finetune" / "train_ult_repaired.jsonl"
PRE_BASELINE_PATH = (ROOT / "data" / "results" / "ult"
                     / "Qwen__Qwen2.5-Coder-1.5B-Instruct__ult__zero_shot__instcore_400__20260713T123923.jsonl")
OUT_MANIFEST = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_seen_manifest.json"
OUT_AUDIT_CSV = ROOT / "analysis" / "comparison_c_confounder_audit.csv"


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def _mannwhitney_u(a: list[float], b: list[float]):
    """Dependency-free Mann-Whitney U (normal approximation), two-sided.
    Returns (U, z, p) or (None, None, None) if either group is empty.
    """
    a = [x for x in a if x is not None]
    b = [x for x in b if x is not None]
    if not a or not b:
        return None, None, None
    combined = sorted((v, 0) for v in a) + sorted((v, 1) for v in b)
    combined.sort(key=lambda t: t[0])
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    rank_sum_a = sum(r for r, (_, grp) in zip(ranks, combined) if grp == 0)
    n1, n2 = len(a), len(b)
    u1 = rank_sum_a - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sigma = (n1 * n2 * (n1 + n2 + 1) / 12) ** 0.5
    z = (u1 - mu) / sigma if sigma > 0 else 0.0
    # two-sided normal-approx p-value via erf
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return u1, z, p


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    core_400_ult = manifest["core_400"]["ult"]["problems"]  # 400 dicts: template_id, task_id, fn_name, cc, band
    print(f"core_400 ULT problems: {len(core_400_ult)}")

    verified_task_ids = set()
    verified_category_by_task_id = {}
    with TRAIN_PATH.open() as f:
        for line in f:
            d = json.loads(line)
            tid = d["template_id"].split("-", 1)[1]
            verified_task_ids.add(tid)
            verified_category_by_task_id[tid] = d["source"]

    raw_by_task_id = {r["task_id"]: r for r in json.loads(ULT_RAW_PATH.read_text())}

    pre_baseline_by_template_id = {}
    with PRE_BASELINE_PATH.open() as f:
        for line in f:
            d = json.loads(line)
            pre_baseline_by_template_id[d["template_id"]] = d

    seen_entries = []
    unseen_entries = []
    manifest_problems = []
    for p in core_400_ult:
        tid = p["task_id"]
        is_seen = tid in verified_task_ids
        code_len = len(raw_by_task_id[tid]["code"]) if tid in raw_by_task_id else None
        pre = pre_baseline_by_template_id.get(p["template_id"], {})
        entry = {
            "template_id": p["template_id"], "task_id": tid, "cc": p["cc"], "band": p["band"],
            "seen_in_training": is_seen,
            "repair_category": verified_category_by_task_id.get(tid),
            "code_len_chars": code_len,
            "pre_exec_rate": pre.get("exec_rate"),
            "pre_mutation_score": pre.get("mutation_score"),
            "pre_baseline_passed": pre.get("baseline_passed"),
        }
        manifest_problems.append(entry)
        (seen_entries if is_seen else unseen_entries).append(entry)

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps({
        "generated_by": "scripts/build_comparison_c_seen_manifest.py",
        "purpose": ("Frozen seen/unseen split for Comparison C's core_400 ULT POST-eval "
                    "stratification -- see data/raw/ult_plt/PROVENANCE.md"),
        "n_seen": len(seen_entries), "n_unseen": len(unseen_entries),
        "problems": manifest_problems,
    }, indent=2))
    print(f"Wrote {OUT_MANIFEST} ({len(seen_entries)} seen / {len(unseen_entries)} unseen)")

    # ---- confounder audit ----
    def col(entries, key):
        return [e[key] for e in entries]

    rows = []
    for label, key, fmt in [
        ("cc", "cc", "{:.2f}"),
        ("code_len_chars", "code_len_chars", "{:.0f}"),
        ("pre_exec_rate", "pre_exec_rate", "{:.3f}"),
        ("pre_mutation_score", "pre_mutation_score", "{:.3f}"),
    ]:
        seen_vals = col(seen_entries, key)
        unseen_vals = col(unseen_entries, key)
        u, z, p = _mannwhitney_u(seen_vals, unseen_vals)
        rows.append({
            "metric": label,
            "n_seen": sum(1 for v in seen_vals if v is not None),
            "mean_seen": _mean(seen_vals),
            "n_unseen": sum(1 for v in unseen_vals if v is not None),
            "mean_unseen": _mean(unseen_vals),
            "mannwhitney_z": z, "mannwhitney_p": p,
        })

    seen_baseline_pass_rate = sum(1 for e in seen_entries if e["pre_baseline_passed"]) / len(seen_entries)
    unseen_baseline_pass_rate = sum(1 for e in unseen_entries if e["pre_baseline_passed"]) / len(unseen_entries)

    import csv
    OUT_AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_AUDIT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n=== Confounder audit: seen (n={len(seen_entries)}) vs unseen (n={len(unseen_entries)}) ===")
    for r in rows:
        print(f"  {r['metric']:20s} seen_mean={r['mean_seen']:.3f}  unseen_mean={r['mean_unseen']:.3f}  "
              f"MWU z={r['mannwhitney_z']:.2f} p={r['mannwhitney_p']:.4f}")
    print(f"  pre_baseline_passed_rate    seen={seen_baseline_pass_rate:.3f}  unseen={unseen_baseline_pass_rate:.3f}")
    print(f"\nWritten: {OUT_AUDIT_CSV}")

    # band distribution (categorical, not covered by Mann-Whitney above)
    from collections import Counter
    print("\nBand distribution:")
    print("  seen:  ", dict(Counter(e["band"] for e in seen_entries)))
    print("  unseen:", dict(Counter(e["band"] for e in unseen_entries)))


if __name__ == "__main__":
    main()
