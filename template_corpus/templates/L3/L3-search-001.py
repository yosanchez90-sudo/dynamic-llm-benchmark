"""L3-search-001 - Guarded linear search with an early-exit secondary branch.

Tier L3: CC=5 (guard-if + for + if/elif), early return. Target band set by
measurement. Body pattern:
    if not items:
        return miss
    for i in range(len(items)):
        if items[i] == target:
            return i
        elif items[i] > cap:
            return early
    return miss
Exercises LOR (not), ROR (==, >), BM (cap, target), CR/RSM across the returns.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, target, cap, miss, early):
    if not items:
        return miss
    for i in range(len(items)):
        if items[i] == target:
            return i
        elif items[i] > cap:
            return early
    return miss


template = Template(
    template_id="L3-search-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(19, 25),   # measured 22; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "i":       IdentifierBank(role="counter"),
        "target":  IntRange(lo=2, hi=9),
        "cap":     IntRange(lo=20, hi=60),
        "miss":    IntRange(lo=2, hi=9),
        "early":   IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {miss}
    for {i} in range(len({items})):
        if {items}[{i}] == {target}:
            return {i}
        elif {items}[{i}] > {cap}:
            return {early}
    return {miss}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} the {first_word} match index, an {bail_word} marker {pastcap}, or a {miss_word} code.",
        synonyms={
            "intro": ("Return", "Report", "Find", "Locate", "Give", "Surface"),
            "first_word": ("first", "earliest", "leading", "initial", "soonest"),
            "bail_word": ("bail-out", "early-exit", "abort", "cutoff", "stop"),
            "pastcap": ("past the cap", "beyond the limit", "over the ceiling", "above the bound", "over-limit"),
            "miss_word": ("fallback", "sentinel", "default", "spare", "reserve"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "target": 5, "cap": 40, "miss": 9, "early": 8},
        {"items": [5],           "target": 5, "cap": 40, "miss": 9, "early": 8},
        {"items": [1, 3, 99, 5], "target": 5, "cap": 40, "miss": 9, "early": 8},
    ),
)
