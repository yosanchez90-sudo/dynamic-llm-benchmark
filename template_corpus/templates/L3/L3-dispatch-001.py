"""L3-dispatch-001 - Pairwise relation tally over nested loops (guarded).

Tier L3: CC=7 (guard-if + for + for + if/elif/elif). Equality-led comparisons
keep ROR moderate despite the high CC. This is the densest L3 shape; it sits at
the top of the L3 mutant range and is documented as such.
Body pattern:
    if not items:
        return base
    hits = 0
    for x in items:
        for y in items:
            if x == y:   hits += 1
            elif x > y:  hits += 2
            elif x < y:  hits += 3
    return hits
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, base):
    if not items:
        return base
    hits = 0
    for x in items:
        for y in items:
            if x == y:
                hits += 1
            elif x > y:
                hits += 2
            elif x < y:
                hits += 3
    return hits


template = Template(
    template_id="L3-dispatch-001",
    declared_tier="L3",
    declared_ast_depth=5,
    expected_mutant_count=(23, 29),   # measured 26; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "hits":    IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "base":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {base}
    {hits} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} == {y}:
                {hits} += 1
            elif {x} > {y}:
                {hits} += 2
            elif {x} < {y}:
                {hits} += 3
    return {hits}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} ordered {pair_word} as equal, larger, or smaller, or a {fallback_word} code if {empty_word}.",
        synonyms={
            "intro": ("Return a tally of", "Classify", "Score", "Weigh", "Rank"),
            "pair_word": ("pairs", "couples", "duos", "combinations", "two-tuples"),
            "fallback_word": ("fallback", "default", "spare", "reserve", "guard"),
            "empty_word": ("empty", "blank", "void", "vacant", "unfilled"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],          "base": 5},
        {"items": [7],         "base": 5},
        {"items": [2, 5, 2],   "base": 5},
    ),
)
