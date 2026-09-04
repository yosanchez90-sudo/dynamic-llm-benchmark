#!/usr/bin/env python3
"""Generate one problem instance from one template and one seed.

Prints the instantiated source, its recomputed cyclomatic complexity, and its
mutant set. This is the thin CLI the repo does not otherwise have; it composes
two functions confirmed working directly against the real template corpus
(2026-09-03):

    template_corpus/templates/_smoke/engine.py  -> load_template, instantiate
    template_corpus/templates/_smoke/mutator.py -> generate_mutants

Run from the repository root:

    python demo/show_instance.py --template L2-clamp-001 --seed 1101
    python demo/show_instance.py --template L2-clamp-001 --seed 1101 --no-mutants
"""

import argparse
import difflib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = REPO_ROOT / "template_corpus" / "templates"

sys.path.insert(0, str(TEMPLATES_ROOT))
sys.path.insert(0, str(TEMPLATES_ROOT / "_smoke"))

from engine import load_template, instantiate  # noqa: E402
from mutator import generate_mutants  # noqa: E402

RULE = "=" * 74


def tier_of(template_id: str) -> str:
    """L2-clamp-001 -> L2"""
    return template_id.split("-", 1)[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="e.g. L2-clamp-001")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--no-mutants", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="source only, for diffing")
    ap.add_argument("--show-mutant", type=int, metavar="N",
                    help="print a unified diff of the original vs mutant N (1-indexed)")
    args = ap.parse_args()

    path = TEMPLATES_ROOT / tier_of(args.template) / f"{args.template}.py"
    if not path.exists():
        print(f"no such template: {path}", file=sys.stderr)
        return 2

    result = instantiate(load_template(path), args.seed)

    if args.show_mutant is not None:
        mutants = generate_mutants(result["source"])
        if not 1 <= args.show_mutant <= len(mutants):
            print(f"--show-mutant must be 1..{len(mutants)}", file=sys.stderr)
            return 2
        m = mutants[args.show_mutant - 1]
        # strip()+newline on both sides: the generated source starts with a
        # blank line, which otherwise shows up as a spurious diff hunk, and
        # without the trailing newline the closing rule runs onto the last line
        diff = difflib.unified_diff(
            (result["source"].strip() + "\n").splitlines(keepends=True),
            (m.source.strip() + "\n").splitlines(keepends=True),
            fromfile="original", tofile=f"mutant M{args.show_mutant} ({m.operator})",
        )
        print(RULE)
        print(f"  {args.template} seed {args.seed} -- mutant M{args.show_mutant}, operator {m.operator}")
        print(RULE)
        print("".join(diff), end="")
        print(RULE)
        return 0

    if args.quiet:
        print(result["source"], end="")
        if not args.no_mutants:
            for m in generate_mutants(result["source"]):
                print(f"{m.operator}\t{m.source!r}")
        return 0

    print(RULE)
    print(f"  {args.template}   seed {args.seed}")
    print(RULE)
    print(result["source"])
    print(RULE)
    print(f"  cyclomatic complexity = {result['cc']}   (recomputed on this instance)")
    print(f"  ast depth             = {result.get('ast_depth', '?')}")

    errors = result.get("validation_errors") or []
    print(f"  validation            = {'clean' if not errors else errors}")

    if args.no_mutants:
        print(RULE)
        return 0

    mutants = generate_mutants(result["source"])
    print(f"  mutants               = {len(mutants)}  (precomputed once, shared by every model)")
    print(RULE)

    by_op: dict[str, int] = {}
    for m in mutants:
        by_op[m.operator] = by_op.get(m.operator, 0) + 1
    print("  " + "   ".join(f"{op} x{n}" for op, n in sorted(by_op.items())))
    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
