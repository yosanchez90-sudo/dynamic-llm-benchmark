"""L3-minmax-001 - Guarded spread (max minus min) via two independent guards.

Tier L3: CC=5 (guard-if + for + if + if). Body pattern:
    if not items:
        return base
    lo = items[0]
    hi = items[0]
    for x in items:
        if x < lo: lo = x
        if x > hi: hi = x
    return hi - lo
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, base):
    if not items:
        return base
    lo = items[0]
    hi = items[0]
    for x in items:
        if x < lo:
            lo = x
        if x > hi:
            hi = x
    return hi - lo


template = Template(
    template_id="L3-minmax-001",
    declared_tier="L3",
    declared_ast_depth=2,
    expected_mutant_count=(18, 24),   # measured 21; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "lo":      IdentifierBank(role="accumulator"),
        "hi":      IdentifierBank(role="accumulator", avoid_collision_with=("lo",)),
        "x":       IdentifierBank(role="single_item"),
        "base":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {base}
    {lo} = {items}[0]
    {hi} = {items}[0]
    for {x} in {items}:
        if {x} < {lo}:
            {lo} = {x}
        if {x} > {hi}:
            {hi} = {x}
    return {hi} - {lo}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} the {spread_word} of the largest and smallest values, or a {fallback_word} code if {empty_word}.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Report", "Derive", "Measure"),
            "spread_word": ("spread", "range", "gap", "distance", "extent"),
            "fallback_word": ("fallback", "default", "spare", "reserve", "guard"),
            "empty_word": ("empty", "blank", "void", "vacant", "unfilled"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "base": 4},
        {"items": [7],           "base": 4},
        {"items": [3, 9, 1, 6],  "base": 4},
    ),
)
