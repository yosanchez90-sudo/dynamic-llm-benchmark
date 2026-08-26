"""Taxonomy + repair + verification for ULT's ground-truth `tests` field,
following the 2026-07-25 decision on STOP GATE A (Comparison C training
data): only 8.5% of CC>=8 ULT records had all 5 shipped tests pass against
ULT's own shipped code (scripts/check_ult_ground_truth_baseline.py).

Runs the REAL scoring harness (src/eval/test_gen_scorer.py's _write_case /
_collect_ok / _run_pytest, the same subprocess+pytest+importlib path
score_problem() uses at eval time), not an ad hoc in-process exec() check,
so any "failure" this script reports is a genuine harness-verified failure,
not an artifact of a cruder checker.

STAGE 1: TAXONOMY. Every CC>=8 record's (code, built-test-file) pair is
run once through the real harness. Failing records are re-run once more to
flag flakiness (status changes between runs, unseeded randomness / wall-
clock dependence). Failures are classified by the exception type in the
first failing test:
  CLEAN,               all 5 tests already pass, nothing to do.
  ASSERTION_MISMATCH,  code executes fine, an expected VALUE is wrong.
                          Repair candidate (Stage 2).
  STRUCTURAL,          code itself can't run cleanly for at least one
                          test (NameError/AttributeError/etc, or collection
                          fails outright). NOT repaired, see "why
                          NameError isn't fixed" below.
  FLAKY,               status changed between the two runs.
  OTHER,               didn't fit the above (rare).

STAGE 2: REPAIR (ASSERTION_MISMATCH only). ULT test bodies are
overwhelmingly `def test_x(): assert <call-expr> == <literal>` (single
statement). For that exact shape, re-evaluate <call-expr> against the
UNMODIFIED code and rewrite the literal to the actual value. Inputs and
code stay ULT's own, only the recorded expected output is corrected. Any
test whose shape isn't exactly one `assert x == y` is left alone (not
guessed at) and the record falls back to STRUCTURAL/OTHER accounting.

Why NameError records are excluded, not import-repaired: PROJECT_BRIEF.md's
Comparison C design reuses the ALREADY-LANDED Qwen-1.5B PRE baseline on
ULT/PLT core_400 (Part 1 item 3), "same eval config as post, or the DiD
is invalid". If a record's underlying `code` itself needs a missing stdlib
import to run (not just its test), fixing that would require changing
`code` at POST-eval time too (the function can't execute without it,
regardless of what test is used). This would silently diverge POST's
eval config from the already-landed PRE config for exactly that record.
Repairing only the ASSERTION_MISMATCH class (never touches `code`) keeps
every training-set record's eval-time code byte-identical to what PRE
already measured.

STAGE 3: VERIFY. Every repaired test file is re-scored through the same
real harness; only records that come back baseline_passed=True enter the
final training set. This is a hard gate, not a sanity check: if the Stage 2
rewrite logic has any bug or the "single assert" shape assumption doesn't
actually guarantee determinism, verification catches it here, not
downstream in training.

CPU-bound across ~3,676 records with several harness invocations each.
Submit via SLURM (scripts/slurm/run_repair_ult_ground_truth.slurm), not the
login node.

Outputs:
  analysis/ult_ground_truth_taxonomy.csv   one row per record, full detail
  data/finetune/train_ult_repaired.jsonl   final verified training pairs

Usage:
    python scripts/repair_ult_ground_truth.py
    python scripts/repair_ult_ground_truth.py --max-n 50   # smoke test
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "template_corpus" / "templates" / "_smoke"))

from validate_cc import compute_cc  # noqa: E402
from build_ult_training_pairs import build_test_file  # noqa: E402
from src.data.test_gen import _build_messages  # noqa: E402
from src.eval.test_gen_scorer import _write_case, _collect_ok, _run_pytest  # noqa: E402

CC_MIN = 8
TIMEOUT = 15
RAW_PATH = ROOT / "data" / "raw" / "ult_plt" / "ULT.jsonl"
MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"
TAXONOMY_OUT = ROOT / "analysis" / "ult_ground_truth_taxonomy.csv"
TRAIN_OUT = ROOT / "data" / "finetune" / "train_ult_repaired.jsonl"

_ERR_RE = re.compile(r"^E\s+(\w+Error)\b", re.MULTILINE)
_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")
_ERRORED_RE = re.compile(r"(\d+) error")


def _target_function_node(code: str, func_name: str):
    tree = ast.parse(code)
    return next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == func_name), None)


def run_harness(code: str, test_file: str, timeout: int = TIMEOUT):
    """(status, n_passed, n_failed, first_error, raw_log). status one of
    COLLECT_ERROR / ALL_PASS / SOME_FAIL / TIMEOUT, exactly the real
    score_problem() gate, minus mutation scoring (not needed here).
    """
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        _write_case(wd, code, test_file)
        if not _collect_ok(wd, timeout):
            return "COLLECT_ERROR", 0, 5, "(collection/import error)", ""
        rc, log = _run_pytest(wd, timeout)
        if rc == -1:
            return "TIMEOUT", 0, 5, "", log
        passed = int(m.group(1)) if (m := _PASSED_RE.search(log)) else 0
        failed = int(m.group(1)) if (m := _FAILED_RE.search(log)) else 0
        errored = int(m.group(1)) if (m := _ERRORED_RE.search(log)) else 0
        if rc == 0 and failed == 0 and errored == 0:
            return "ALL_PASS", passed, 0, "", log
        errs = _ERR_RE.findall(log)
        first_err = errs[0] if errs else "(assertion mismatch, no named exception)"
        return "SOME_FAIL", passed, failed + errored, first_err, log


# ---------------------------------------------------------------------------
# Stage 2: repair, rewrite `assert <call> == <literal>` to the actual value
# ---------------------------------------------------------------------------

def _repairable_shape(test_src: str):
    """Return the single ast.Assert(Compare(==)) node if `test_src` is
    exactly one such statement inside one function def; else None. Defensive
    try/except: this is called on ULT's raw text, and while
    build_test_file() already parses every test once (a genuine SyntaxError
    there routes the whole record to SKIPPED_PARSE_OR_CC upstream), belt and
    braces costs nothing here.
    """
    try:
        tree = ast.parse(test_src)
    except SyntaxError:
        return None
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        return None
    fn_body = tree.body[0].body
    if len(fn_body) != 1 or not isinstance(fn_body[0], ast.Assert):
        return None
    test = fn_body[0].test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1):
        return None
    return tree.body[0], fn_body[0]


def repair_test(code: str, func_name: str, test_src: str):
    """Try to rewrite one ULT test's expected value to match the real
    function's actual output on the test's own input expression. Returns
    (repaired_source, actual_value), or None if the shape doesn't qualify,
    evaluating the left-hand side itself raises (then it's not an
    ASSERTION_MISMATCH at all, leave it to the STRUCTURAL bucket), or the
    actual value's repr() isn't valid Python to re-embed as a literal (e.g.
    an Enum member reprs as `<Matches.BothSame: 5>`, not valid syntax,
    happens for functions that return a non-literal type; such records fall
    through to SHAPE_NOT_REPAIRABLE instead of being silently miscoded).
    """
    shape = _repairable_shape(test_src)
    if shape is None:
        return None
    fn_def, assert_node = shape
    ns: dict = {}
    # ULT `code` blobs are arbitrary scraped real-world functions. Some do
    # relative-path file I/O as a side effect of normal operation (a sibling
    # check script that exec'd ULT code with cwd left at the repo root
    # littered it with fort.*/moldyn.vel-style debris from whatever those
    # functions happened to write; see CLAUDE.md's isolation rule). Isolate
    # this exec()/eval() in a throwaway directory and always restore cwd,
    # since repair_test() is called many times in this one long-lived process.
    orig_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp(prefix="ult_repair_")
    try:
        os.chdir(tmpdir)
        exec(compile(code, "<under_test>", "exec"), ns)
        lhs_expr = ast.Expression(body=assert_node.test.left)
        ast.fix_missing_locations(lhs_expr)
        actual = eval(compile(lhs_expr, "<lhs>", "eval"), ns)
    except Exception:
        return None
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)
    lhs_src = ast.unparse(assert_node.test.left)
    candidate = f"def {fn_def.name}():\n    assert {lhs_src} == {actual!r}\n"
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate, actual


_SOURCE_BY_CATEGORY = {
    "CLEAN": "ult_ground_truth",
    "ASSERTION_MISMATCH_REPAIRED_VERIFIED": "ult_ground_truth_repaired",
    "ASSERTION_MISMATCH_REPAIRED_DEGENERATE": "ult_ground_truth_repaired_degenerate",
}


def process_record(r: dict):
    """Full taxonomy+repair+verify pipeline for one ULT record. Returns
    (skip_reason_or_None, cc, category, first_error, train_row_or_None).
    Standalone/picklable so ProcessPoolExecutor can run it across records.
    """
    fn = _target_function_node(r["code"], r["func_name"])
    if fn is None:
        return "SKIPPED_PARSE_OR_CC", None, None, None, None
    cc = compute_cc(fn)
    if cc < CC_MIN:
        return "BELOW_CC_MIN", None, None, None, None
    try:
        test_file = build_test_file(r["func_name"], r["code"], r["tests"])
    except SyntaxError:
        return "SKIPPED_PARSE_OR_CC", None, None, None, None

    status1, p1, f1, err1, _ = run_harness(r["code"], test_file)

    category = ""
    final_test_file = None

    if status1 == "ALL_PASS":
        category = "CLEAN"
        final_test_file = test_file
    else:
        status2, *_rest = run_harness(r["code"], test_file)
        if status2 != status1:
            category = "FLAKY"
        elif status1 in ("COLLECT_ERROR", "TIMEOUT"):
            category = "STRUCTURAL"
        elif err1 in ("(assertion mismatch, no named exception)", "AssertionError"):
            repaired_tests = []
            actual_values = []
            all_repaired = True
            for t in r["tests"]:
                rep = repair_test(r["code"], r["func_name"], t)
                if rep is None:
                    all_repaired = False
                    break
                repaired_src, actual_val = rep
                repaired_tests.append(repaired_src)
                actual_values.append(repr(actual_val))
            if not all_repaired:
                category = "SHAPE_NOT_REPAIRABLE"
            else:
                repaired_file = build_test_file(r["func_name"], r["code"], repaired_tests)
                status3, *_rest3 = run_harness(r["code"], repaired_file)
                if status3 == "ALL_PASS":
                    # All 5 repaired tests vary their inputs (that's how ULT wrote
                    # them) but a few functions short-circuit to the same output
                    # for every one of them (e.g. a bare except swallowing a
                    # missing-fixture-file IOError and returning None). Verify-
                    # via-scorer passes such a record (it IS self-consistent) but
                    # the resulting "test" barely exercises the function. Flagged,
                    # not excluded, see PROVENANCE.md.
                    degenerate = len(set(actual_values)) == 1
                    category = ("ASSERTION_MISMATCH_REPAIRED_DEGENERATE" if degenerate
                                else "ASSERTION_MISMATCH_REPAIRED_VERIFIED")
                    final_test_file = repaired_file
                else:
                    category = "ASSERTION_MISMATCH_VERIFY_FAILED"
        else:
            category = "STRUCTURAL"

    train_row = None
    if final_test_file is not None:
        messages = [*_build_messages(r["code"], "zero_shot"),
                    {"role": "assistant", "content": final_test_file}]
        train_row = {
            "messages": messages,
            "template_id": f"ULT-{r['task_id']}",
            "instance_seed": int(r["task_id"]),
            "tier": "L4",
            "source": _SOURCE_BY_CATEGORY[category],
        }

    return None, cc, category, err1, train_row


# ---------------------------------------------------------------------------

def main() -> None:
    import os
    from concurrent.futures import ProcessPoolExecutor, as_completed

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-n", type=int, default=None, help="Smoke-test cap")
    parser.add_argument("--workers", type=int, default=None,
                         help="Process pool size (default: SLURM_CPUS_PER_TASK or os.cpu_count())")
    args = parser.parse_args()

    records = json.loads(RAW_PATH.read_text())
    if args.max_n:
        records = records[: args.max_n]
    print(f"Raw ULT records: {len(records)}", flush=True)

    n_workers = args.workers or int(os.environ.get("SLURM_CPUS_PER_TASK", 0)) or os.cpu_count() or 4
    print(f"Workers: {n_workers}", flush=True)

    train_rows = []
    counts = {
        "CLEAN": 0, "ASSERTION_MISMATCH_REPAIRED_VERIFIED": 0,
        "ASSERTION_MISMATCH_REPAIRED_DEGENERATE": 0,
        "ASSERTION_MISMATCH_VERIFY_FAILED": 0, "SHAPE_NOT_REPAIRABLE": 0,
        "STRUCTURAL": 0, "FLAKY": 0, "OTHER": 0, "SKIPPED_PARSE_OR_CC": 0,
    }
    t0 = time.time()
    n_seen = 0

    # Written incrementally, not buffered to the end: a ~4-hour, 16-way
    # parallel run over arbitrary real-world code WILL eventually hit an
    # edge case (an Enum-repr crash took down the first full attempt of this
    # script after a long partial run with zero output to show for it --
    # see PROVENANCE.md). One row per completed record, flushed immediately,
    # so a late crash keeps everything scored before it.
    TAXONOMY_OUT.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    tax_fh = TAXONOMY_OUT.open("w", newline="")
    tax_w = csv.DictWriter(tax_fh, fieldnames=["task_id", "func_name", "cc", "category", "first_error"])
    tax_w.writeheader()
    train_fh = TRAIN_OUT.open("w")

    try:
        with ProcessPoolExecutor(max_workers=n_workers) as ex:
            futures = {ex.submit(process_record, r): r for r in records}
            for fut in as_completed(futures):
                r = futures[fut]
                try:
                    skip_reason, cc, category, err1, train_row = fut.result()
                except Exception as e:
                    # Real-world ULT code/tests are arbitrary and unpredictable --
                    # one unforeseen edge case (e.g. the Enum-repr crash this
                    # except clause was added after hitting) must not lose
                    # multiple CPU-hours of completed work on every other record.
                    n_seen += 1
                    counts["OTHER"] += 1
                    tax_w.writerow({
                        "task_id": r["task_id"], "func_name": r["func_name"], "cc": "",
                        "category": "OTHER", "first_error": f"{type(e).__name__}: {e}"[:150],
                    })
                    tax_fh.flush()
                    continue
                if skip_reason == "BELOW_CC_MIN":
                    continue
                if skip_reason == "SKIPPED_PARSE_OR_CC":
                    counts["SKIPPED_PARSE_OR_CC"] += 1
                    continue

                n_seen += 1
                counts[category] += 1
                tax_w.writerow({
                    "task_id": r["task_id"], "func_name": r["func_name"], "cc": cc,
                    "category": category, "first_error": err1,
                })
                tax_fh.flush()
                if train_row is not None:
                    train_rows.append(train_row)
                    train_fh.write(json.dumps(train_row, ensure_ascii=False) + "\n")
                    train_fh.flush()

                if n_seen % 200 == 0:
                    elapsed = time.time() - t0
                    print(f"...{n_seen} done in {elapsed:.0f}s -- {counts}", flush=True)
    finally:
        tax_fh.close()
        train_fh.close()

    print(f"\n=== FINAL: {n_seen} CC>=8 records checked ===")
    for k, v in counts.items():
        pct = 100 * v / n_seen if n_seen and k != "SKIPPED_PARSE_OR_CC" else 0
        print(f"  {k:38s} {v:5d}  ({pct:.1f}%)")
    print(f"\nVerified training set: {len(train_rows)} records -> {TRAIN_OUT}")
    print(f"Taxonomy: {TAXONOMY_OUT}")

    if args.max_n is None and MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        core_400_ids = {p["task_id"] for p in manifest["core_400"]["ult"]["problems"]}
        verified_ids = {row["template_id"].split("-", 1)[1] for row in train_rows}
        covered = core_400_ids & verified_ids
        pct = 100 * len(covered) / len(core_400_ids)
        print(f"\ncore_400 ULT coverage: {len(covered)}/{len(core_400_ids)} ({pct:.1f}%) "
              f"have a verified seen-in-training pair")
        if pct < 90:
            print("WARNING: core_400 coverage below 90% -- flagged per the 90% target threshold.")


if __name__ == "__main__":
    main()
