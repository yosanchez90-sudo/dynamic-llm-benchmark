#!/usr/bin/env python3
"""Score ONE test-suite file against ONE problem instance, with per-mutant detail.

score_problem() builds a per-mutant verdict list internally and then collapses it
to counts, so the detail is not recoverable from its return value. This wrapper
calls score_problem() for the gates and the aggregate, then re-runs each mutant
through _evaluate_mutant() to recover the killed/survived/dropped table. This
means every mutant subprocess actually runs twice per invocation; confirmed
2026-09-03 this costs under a second for this problem's ten mutants, so it is
not worth avoiding for a five-minute demo.

_evaluate_mutant is private by name but is imported directly by the project's own
tests (tests/test_scorer_mutant_timeout.py), so this is not a novel access pattern.

Run from the repository root:

    python demo/score_suite.py --template L2-clamp-001 --seed 1101 \
        --suite demo/suite_seed_1101.py
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data.test_gen import load  # noqa: E402
from src.eval.test_gen_scorer import score_problem, _evaluate_mutant  # noqa: E402

RULE = "=" * 74
MARK = {"killed": "KILLED  ", "survived": "SURVIVED", "dropped": "dropped "}


def tier_of(template_id: str) -> str:
    return template_id.split("-", 1)[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--suite", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--label", default="", help="printed in the header, e.g. 'memorised suite'")
    args = ap.parse_args()

    test_source = args.suite.read_text()

    # instantiation_seed MUST stay 0: load() computes the real instance seed as
    # instantiation_seed*1000 + base_seed (src/data/test_gen.py:130), so with 0
    # the value passed via --seed maps straight through -- the same instance
    # show_instance.py generates by calling instantiate() with that seed
    # directly. Any other instantiation_seed silently generates a DIFFERENT
    # instance. instantiation_id is just a free-text label on the result and
    # does not need to match anything on disk. Confirmed against
    # src/data/test_gen.py:103-152, 2026-09-03.
    problems = load(
        instantiation_id="inst1",
        instantiation_seed=0,
        tiers=(tier_of(args.template),),
        instance_seeds=(args.seed,),
        only_instances=frozenset({(args.template, args.seed)}),
    )
    if not problems:
        print(f"load() returned nothing for {args.template} seed {args.seed}", file=sys.stderr)
        return 2
    problem = problems[0]

    print(RULE)
    header = f"  {args.suite.name}  ->  {args.template} seed {args.seed}"
    print(header + (f"   [{args.label}]" if args.label else ""))
    print(f"  function under test: {problem.fn_name}")
    print(RULE)

    result = score_problem(
        fn_source=problem.source,
        fn_name=problem.fn_name,
        test_source=test_source,
        mutants=problem.mutants,
    )

    print(f"  1  EXEC GATE       {'pass' if result.exec_ok else 'FAIL'}")
    if not result.exec_ok:
        print(RULE)
        print("  Not scorable. The suite never reaches the baseline gate.")
        print(RULE)
        return 0

    print(f"  2  BASELINE GATE   {'pass' if result.baseline_passed else 'FAIL'}")
    if not result.baseline_passed:
        print(RULE)
        print("  Mut@K is UNDEFINED -- this problem leaves the denominator entirely.")
        print("  It is not scored zero under the primary metric.")
        print(RULE)
        return 0

    print(f"  3  MUTATION SCORING  ({len(problem.mutants)} mutants)")
    print(RULE)

    killed = survived = dropped = 0
    for i, m in enumerate(problem.mutants, 1):
        verdict = _evaluate_mutant((m.source, test_source, args.timeout))
        killed += verdict == "killed"
        survived += verdict == "survived"
        dropped += verdict == "dropped"
        print(f"  M{i:<3} {m.operator:<5} {MARK.get(verdict, verdict)}")

    print(RULE)
    print(f"  killed {killed}   survived {survived}   dropped {dropped}")
    print(f"  Mut@K = {killed}/{killed + survived} = {result.mutation_score:.3f}")
    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
