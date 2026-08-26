"""Build prompt -> ground-truth-test training pairs for the CANONICAL
Comparison C fine-tune (PROJECT_BRIEF.md Sec 7/Sec 11, 2026-07-25 supervisor
meeting): Qwen-1.5B LoRA fine-tuned on ULT, evaluated pre/post on ULT/PLT/
Dynamic for the 2x3 DiD table.

This is NOT scripts/prepare_finetune_data.py's approach. That
script (used for the six *supplementary* memorisation-stability runs) pairs
a prompt with a MODEL'S OWN extracted test output (self-distillation). This
script pairs a prompt with ULT's OWN SHIPPED ground-truth `tests` field,
see data/raw/ult_plt/PROVENANCE.md's "Known discrepancy" note: ULT.jsonl
contains real pytest assertions despite the source repo's README claiming
ground-truth tests are withheld. That discrepancy is exactly what this
experiment simulates: "the whole static benchmark leaked into training."

Scope (2026-07-25 supervisor-meeting default, approved): the FULL effective ULT
(CC>=8 filtered, ~3,676 problems, same filter src/data/ult_plt.py:load()
applies for evaluation, so training and eval prompts are byte-identical for
any shared task_id). core_400 is a subsample of this same pool by
construction, so every core_400 problem is guaranteed seen-in-training,
checked below, not assumed. No held-out split: deliberate contamination is
the point of this experiment, not a confound to control for.

Each ULT record's `tests` field is 5 short pytest functions, not a complete
file. build_test_file() concatenates them under a `from under_test import
...` header matching this project's expected model-output format
(src/data/test_gen.py:SYSTEM_INSTRUCTION). ~19% of ULT `code` blobs define
helper classes/functions the target function depends on (PROVENANCE.md);
build_test_file() imports any such helper actually referenced by the test
bodies alongside the target function, so the generated file is import-
complete instead of failing on a bare NameError.

Output: data/finetune/train_ult_full.jsonl
Each line: {"messages": [...same messages as eval-time prompting...,
                          {"role": "assistant", "content": "<test file>"}],
            "template_id": "ULT-<task_id>", "instance_seed": <task_id as int>,
            "tier": "L4", "source": "ult_ground_truth"}

Usage:
    python scripts/build_ult_training_pairs.py
    python scripts/build_ult_training_pairs.py --max-n 20   # smoke test
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import ult_plt  # noqa: E402

OUT_FILE = ROOT / "data" / "finetune" / "train_ult_full.jsonl"
MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"


def _module_level_names(code: str, exclude: str) -> set[str]:
    """Top-level names defined in `code` besides the target function --
    candidate helper names a ground-truth test might reference (see module
    docstring's "helper classes" note). Covers class/function defs AND
    module-level constant assignments (`FOO = ...`, `FOO: int = ...`) --
    an earlier version only collected def/class names, which meant a test
    referencing a module-level constant got a spurious NameError that was a
    bug in THIS builder, not a real ULT data problem (see
    scripts/repair_ult_ground_truth.py's harness-incompatibility category).
    """
    tree = ast.parse(code)
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name != exclude:
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _referenced_names(test_src: str) -> set[str]:
    tree = ast.parse(test_src)
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def build_test_file(func_name: str, code: str, tests: list[str]) -> str:
    """Concatenate ULT's ground-truth test functions into one pytest file.

    Imports the target function plus any module-level helper (class,
    function, or constant) the test bodies actually reference, not every
    helper `code` defines, only the ones a test needs, keeping the import
    line minimal and matching how a real model response would import
    exactly what it uses. Also adds a bare `import pytest` when a test body
    references the name `pytest` (e.g. `pytest.approx`, `pytest.raises`) and
    it isn't already one of `code`'s own helper names. ULT's shipped test
    snippets are bare function bodies with no import preamble of their own.
    """
    helpers = _module_level_names(code, exclude=func_name)
    used: set[str] = set()
    for t in tests:
        used |= _referenced_names(t)
    needed_helpers = sorted(helpers & used)
    import_names = [func_name, *needed_helpers]
    import_line = f"from under_test import {', '.join(import_names)}"
    prelude = import_line
    if "pytest" in used and "pytest" not in helpers:
        prelude = f"import pytest\n{prelude}"
    body = "\n\n".join(t.strip() for t in tests)
    return f"{prelude}\n\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-n", type=int, default=None,
                         help="Cap the number of problems (smoke-test only; "
                              "omit for the full effective-ULT training set).")
    parser.add_argument("--out", type=Path, default=OUT_FILE)
    args = parser.parse_args()

    # max_n is passed straight into load() (not sliced afterward) so a
    # smoke-test run doesn't pay the mutant-generation cost for the full
    # ~3,676-problem set only to discard most of it.
    problems = ult_plt.load(benchmark="ult", prompting_condition="zero_shot", max_n=args.max_n)
    print(f"Loaded {len(problems)} problems"
          f"{' (full effective ULT, CC>=8 filtered)' if args.max_n is None else ' (--max-n smoke test)'}")

    raw_by_task_id = {r["task_id"]: r for r in ult_plt._iter_records("ult")}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.out.open("w") as fh:
        for p in problems:
            r = raw_by_task_id[str(p.instance_seed)]
            test_file = build_test_file(r["func_name"], r["code"], r["tests"])
            record = {
                "messages": [*p.messages, {"role": "assistant", "content": test_file}],
                "template_id": p.template_id,
                "instance_seed": p.instance_seed,
                "tier": p.tier,
                "source": "ult_ground_truth",
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Wrote {written} training examples to {args.out}")

    if args.max_n is None and MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text())
        core_400_ult_ids = {p["template_id"] for p in manifest["core_400"]["ult"]["problems"]}
        train_ids = {p.template_id for p in problems}
        missing = core_400_ult_ids - train_ids
        if missing:
            print(f"WARNING: {len(missing)} core_400 ULT ids NOT in the training set: {sorted(missing)[:10]}")
        else:
            print(f"Verified: all {len(core_400_ult_ids)} core_400 ULT ids are contained in the training set.")


if __name__ == "__main__":
    main()
