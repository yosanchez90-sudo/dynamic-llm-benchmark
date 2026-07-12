"""L3-max-001 - Guarded running maximum with a tie counter.

Tier L3: CC=5 (guard-if + for + if/elif). Body pattern:
    if not items:
        return base
    best = items[0]
    ties = 0
    for x in items:
        if x > best: best = x
        elif x == best: ties += 1
    return best + ties
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, base):
    if not items:
        return base
    best = items[0]
    ties = 0
    for x in items:
        if x > best:
            best = x
        elif x == best:
            ties += 1
    return best + ties


template = Template(
    template_id="L3-max-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(17, 23),   # measured 20; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "best":    IdentifierBank(role="accumulator"),
        "ties":    IdentifierBank(role="accumulator", avoid_collision_with=("best",)),
        "x":       IdentifierBank(role="single_item"),
        "base":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {base}
    {best} = {items}[0]
    {ties} = 0
    for {x} in {items}:
        if {x} > {best}:
            {best} = {x}
        elif {x} == {best}:
            {ties} += 1
    return {best} + {ties}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} the {peak_word} value plus its {tie_word}, or a {fallback_word} code if {empty_word}.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Report", "Derive", "Give"),
            "peak_word": ("largest", "highest", "maximum", "top", "greatest"),
            "tie_word": ("repeat count", "tie count", "duplicate count", "recurrences", "match count"),
            "fallback_word": ("fallback", "default", "spare", "reserve", "guard"),
            "empty_word": ("empty", "blank", "void", "vacant", "unfilled"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "base": 5},
        {"items": [7],           "base": 5},
        {"items": [3, 9, 9, 2],  "base": 5},
    ),
)
