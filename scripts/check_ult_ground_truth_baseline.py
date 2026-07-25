"""Does ULT's own shipped `tests` field actually pass against ULT's own
shipped `code` field? A pre-flight check for the canonical Comparison C
training-pair build (scripts/build_ult_training_pairs.py) -- STOP GATE A's
5-sample preview found 0/5 samples fully passing, which is unexpected enough
(session rule: ambiguous/contradicts-expectations evidence gets a full
check, not a shrug) to need a real denominator across the whole corpus
before anyone decides what to do about it.

Runs each record's ground-truth test functions in a forked subprocess
(timeout-guarded, since some real-world ULT functions loop/print heavily)
against the record's own code -- no pytest/mutation machinery, just
does-it-pass. CPU-bound across ~3,676 records: submit via SLURM
(scripts/slurm/run_check_ult_baseline.slurm), do not run on the login node.

Usage:
    python scripts/check_ult_ground_truth_baseline.py
    python scripts/check_ult_ground_truth_baseline.py --out analysis/ult_ground_truth_baseline.csv
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "template_corpus" / "templates" / "_smoke"))

from validate_cc import compute_cc  # noqa: E402
from build_ult_training_pairs import build_test_file  # noqa: E402

CC_MIN = 8
RAW_PATH = ROOT / "data" / "raw" / "ult_plt" / "ULT.jsonl"
OUT_PATH = ROOT / "analysis" / "ult_ground_truth_baseline.csv"


def _target_function_node(code: str, func_name: str):
    tree = ast.parse(code)
    return next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func_name), None)


def _worker(code: str, tests: list[str], q: mp.Queue) -> None:
    ns: dict = {}
    try:
        exec(compile(code, "<under_test>", "exec"), ns)
    except Exception as e:
        q.put(("CODE_EXEC_ERROR", 0, len(tests), f"{type(e).__name__}: {e}"[:150]))
        return
    n_pass, n_fail, first_err = 0, 0, ""
    for t in tests:
        test_ns = dict(ns)
        try:
            exec(compile(t, "<test>", "exec"), test_ns)
            fn_name = next(n.name for n in ast.parse(t).body if isinstance(n, ast.FunctionDef))
            test_ns[fn_name]()
            n_pass += 1
        except Exception as e:
            n_fail += 1
            if not first_err:
                first_err = f"{type(e).__name__}: {e}"[:150]
    q.put(("ALL_PASS" if n_fail == 0 else "SOME_FAIL", n_pass, n_fail, first_err))


def run_with_timeout(code: str, tests: list[str], timeout: float = 3.0):
    q: mp.Queue = mp.Queue()
    p = mp.Process(target=_worker, args=(code, tests, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return "TIMEOUT", 0, len(tests), ""
    if not q.empty():
        return q.get()
    return "CRASH", 0, len(tests), ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    records = json.loads(RAW_PATH.read_text())
    print(f"Raw ULT records: {len(records)}", flush=True)

    rows = []
    n_checked = n_all_pass = n_skipped_parse = 0
    t0 = time.time()

    for r in records:
        fn = _target_function_node(r["code"], r["func_name"])
        if fn is None:
            n_skipped_parse += 1
            continue
        cc = compute_cc(fn)
        if cc < CC_MIN:
            continue
        try:
            test_file = build_test_file(r["func_name"], r["code"], r["tests"])
        except SyntaxError:
            n_skipped_parse += 1
            continue

        n_checked += 1
        status, npassed, nfailed, err = run_with_timeout(r["code"], r["tests"])
        if status == "ALL_PASS":
            n_all_pass += 1
        rows.append({
            "task_id": r["task_id"], "func_name": r["func_name"], "cc": cc,
            "status": status, "n_passed": npassed, "n_failed": nfailed,
            "first_error": err,
        })

        if n_checked % 300 == 0:
            elapsed = time.time() - t0
            print(f"...{n_checked} checked in {elapsed:.0f}s, "
                  f"{n_all_pass} all-pass ({100*n_all_pass/n_checked:.1f}%)", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n=== FINAL: {n_checked} problems checked (of {len(records)} raw, "
          f"{n_skipped_parse} skipped on parse/CC filter) ===")
    print(f"ALL ground-truth tests pass: {n_all_pass} ({100*n_all_pass/n_checked:.1f}%)")
    print(f"At least 1 fails/errors/times out: {n_checked - n_all_pass} "
          f"({100*(n_checked - n_all_pass)/n_checked:.1f}%)")
    print(f"Written: {args.out}")


if __name__ == "__main__":
    main()
