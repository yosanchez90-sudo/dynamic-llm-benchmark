"""L3-nested-001 - Count ordered pairs via nested loops with a two-sided rule.

Tier L3: CC=5 (for + for + if/elif). Body pattern:
    count = 0
    for x in items:
        for y in items:
            if x + y > t: count += 1
            elif x - y < s: count += 2
    return count
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, t, s):
    count = 0
    for x in items:
        for y in items:
            if x + y > t:
                count += 1
            elif x - y < s:
                count += 2
    return count


template = Template(
    template_id="L3-nested-001",
    declared_tier="L3",
    declared_ast_depth=4,
    expected_mutant_count=(19, 25),   # measured 22; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "count":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "t":       IntRange(lo=10, hi=40),
        "s":       IntRange(lo=2, hi=12),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {count} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} + {y} > {t}:
                {count} += 1
            elif {x} - {y} < {s}:
                {count} += 2
    return {count}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} ordered {pair_word} where a {agg1} {tops} the cap or a {agg2} {dips} below the margin.",
        synonyms={
            "intro": ("Return", "Tally", "Count", "Accumulate", "Compute"),
            "pair_word": ("pairs", "couples", "duos", "combinations", "two-tuples"),
            "agg1": ("sum", "total", "combined value", "joint figure", "addition"),
            "tops": ("tops", "exceeds", "overshoots", "clears", "beats"),
            "agg2": ("gap", "difference", "spread", "distance", "offset"),
            "dips": ("dips", "drops", "falls", "sinks", "slips"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],          "t": 20, "s": 5},
        {"items": [10],        "t": 20, "s": 5},
        {"items": [3, 12, 18], "t": 20, "s": 5},
    ),
)
