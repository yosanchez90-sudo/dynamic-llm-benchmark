"""Unit tests for the `scope_fn_name` parameter added to
mutator.generate_mutants() (template_corpus/templates/_smoke/mutator.py).

Context: Dynamic templates are always a single self-contained function, so
the mutation engine originally walked the whole parsed module unscoped —
harmless there. External sources (ULT/PLT) sometimes ship helper
classes/functions alongside the function under test; without scoping, all
7 operators would also generate mutants inside that unrelated helper code.
These tests confirm the fix: scoped mutation never touches the helper, and
unscoped (the Dynamic-compatible default) still reaches everywhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SMOKE = Path(__file__).resolve().parent.parent / "template_corpus" / "templates" / "_smoke"
sys.path.insert(0, str(_SMOKE))

from mutator import generate_mutants  # noqa: E402


MULTI_DEF_SOURCE = """
class Helper:
    def __init__(self, x):
        self.x = x + 1

def target(a, b):
    if a > b:
        return a - b
    return b - a
"""


def test_unscoped_reaches_into_helper_class():
    mutants = generate_mutants(MULTI_DEF_SOURCE)
    scoped = generate_mutants(MULTI_DEF_SOURCE, scope_fn_name="target")
    assert len(mutants) > len(scoped)
    # unscoped must produce at least one mutant that actually changes Helper's body
    assert any("self.x = x + 1" not in m.source for m in mutants)


def test_scoped_never_touches_helper_class():
    scoped = generate_mutants(MULTI_DEF_SOURCE, scope_fn_name="target")
    assert scoped, "expected target() to yield mutants"
    for m in scoped:
        assert "self.x = x + 1" in m.source


def test_scoped_still_finds_target_function_mutants():
    scoped = generate_mutants(MULTI_DEF_SOURCE, scope_fn_name="target")
    ops = {m.operator for m in scoped}
    assert "ROR" in ops  # `a > b`
    assert "AOR" in ops  # `a - b` / `b - a`


def test_unknown_scope_fn_name_raises():
    with pytest.raises(ValueError):
        generate_mutants(MULTI_DEF_SOURCE, scope_fn_name="does_not_exist")


def test_sdl_respects_scope_fn_name_when_multiple_functions_present():
    src = (
        "def helper():\n"
        "    y = 1\n"
        "    return y\n"
        "\n"
        "def target(a):\n"
        "    z = a + 1\n"
        "    return z\n"
    )
    scoped = generate_mutants(src, scope_fn_name="target")
    sdl_mutants = [m for m in scoped if m.operator == "SDL"]
    assert len(sdl_mutants) == 1
    assert "    y = 1\n" in sdl_mutants[0].source  # helper() body left untouched
