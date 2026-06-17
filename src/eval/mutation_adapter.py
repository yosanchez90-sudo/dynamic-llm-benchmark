"""Thin adapter: mutator.Mutant → test_gen_problem.Mutant.

The mutation engine (template_corpus/templates/_smoke/mutator.py) now has a
working generate_mutants() for all 7 SAC operators. This file bridges its
Mutant type (source, operator) to the harness Mutant type (operator, source,
description) so test_gen.py doesn't need to know about the engine's internals.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SMOKE = Path(__file__).resolve().parent.parent.parent / "template_corpus" / "templates" / "_smoke"
sys.path.insert(0, str(_SMOKE))

from mutator import generate_mutants as _engine_generate  # noqa: E402
from src.eval.test_gen_problem import Mutant


def generate_mutants(source: str) -> list[Mutant]:
    """Run all 7 SAC operators and return harness-typed Mutant objects.

    Raises SyntaxError if source doesn't parse (caller's responsibility to
    guard against this — engine.instantiate() always produces valid Python).
    """
    return [
        Mutant(operator=m.operator, source=m.source)
        for m in _engine_generate(source)
    ]
