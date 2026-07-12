"""L3-count-001 - Count entries above a ceiling and below a floor (net).

Tier L3: CC=4 (for + if/elif), two accumulators. Body pattern:
    high = 0
    low = 0
    for x in items:
        if x > hi:   high += 1
        elif x < lo: low += 1
    return high - low
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, hi, lo):
    high = 0
    low = 0
    for x in items:
        if x > hi:
            high += 1
        elif x < lo:
            low += 1
    return high - low


template = Template(
    template_id="L3-count-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(19, 25),   # measured 22; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "high":    IdentifierBank(role="accumulator"),
        "low":     IdentifierBank(role="accumulator", avoid_collision_with=("high",)),
        "x":       IdentifierBank(role="single_item"),
        "hi":      IntRange(lo=15, hi=40),
        "lo":      IntRange(lo=2, hi=12),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {high} = 0
    {low} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {high} += 1
        elif {x} < {lo}:
            {low} += 1
    return {high} - {low}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} the {net_word}: numbers {clear} the ceiling, {versus} those {below} the floor.",
        synonyms={
            "intro": ("Return", "Compute", "Tally", "Produce", "Report", "Derive"),
            "net_word": ("net count", "balance", "difference", "margin", "surplus"),
            "clear": ("clearing", "exceeding", "topping", "passing", "beating"),
            "versus": ("against", "offset by", "balanced by", "less", "minus"),
            "below": ("under", "beneath", "short of", "dipping below", "slipping past"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],                "hi": 20, "lo": 5},
        {"items": [25],              "hi": 20, "lo": 5},
        {"items": [1, 30, 3, 22, 8], "hi": 20, "lo": 5},
    ),
)
