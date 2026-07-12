"""L4-flow-001 - Guarded twin-pass with Name-based accumulation, no constants.

Tier L4: CC=8 (guard + for + if/elif + for + if/elif).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo, mid):
    if not items:
        return 0
    a = 0
    for x in items:
        if x > hi:
            a += x
        elif x < lo:
            a -= x
    b = 0
    for y in items:
        if y > mid:
            b += y
        elif y == hi:
            b += 1
    return a + b


template = Template(
    template_id="L4-flow-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(30, 36),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "a":       IdentifierBank(role="accumulator"),
        "b":       IdentifierBank(role="accumulator", avoid_collision_with=("a",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":      IntRange(lo=25, hi=50),
        "lo":      IntRange(lo=2, hi=10),
        "mid":     IntRange(lo=12, hi=22),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {a} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {a} += {x}
        elif {x} < {lo}:
            {a} -= {x}
    {b} = 0
    for {y} in {items}:
        if {y} > {mid}:
            {b} += {y}
        elif {y} == {hi}:
            {b} += 1
    return {a} + {b}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} a {first_word} extremes pass, then a {second_word} sweep {credit_act} the mid-band.",
        synonyms={
            "intro": ("Run", "Compute", "Drive", "Stage", "Build", "Execute"),
            "first_word": ("leading", "primary", "front", "first", "opening"),
            "second_word": ("trailing", "secondary", "back", "follow-up", "closing"),
            "credit_act": ("rewarding", "boosting", "banking", "crediting", "favouring"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],              "hi": 30, "lo": 5, "mid": 15},
        {"items": [40],            "hi": 30, "lo": 5, "mid": 15},
        {"items": [3, 35, 18, 5],  "hi": 30, "lo": 5, "mid": 15},
    ),
)
