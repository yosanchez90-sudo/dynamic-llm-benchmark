"""L4-route-001 - Guarded twin-pass routing with Name-based accumulation.

Tier L4: CC=8 (guard + for + if/elif + for + if/elif). LOR via 'not'.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo):
    if not items:
        return 0
    up = 0
    for x in items:
        if x > hi:
            up += x
        elif x == lo:
            up += 1
    down = 0
    for y in items:
        if y < lo:
            down += y
        elif y > hi:
            down -= 1
    return up - down


template = Template(
    template_id="L4-route-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(32, 38),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "up":      IdentifierBank(role="accumulator"),
        "down":    IdentifierBank(role="accumulator", avoid_collision_with=("up",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":      IntRange(lo=25, hi=50),
        "lo":      IntRange(lo=2, hi=12),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {up} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {up} += {x}
        elif {x} == {lo}:
            {up} += 1
    {down} = 0
    for {y} in {items}:
        if {y} < {lo}:
            {down} += {y}
        elif {y} > {hi}:
            {down} -= 1
    return {up} - {down}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} an upward and a downward {tally_word}, then {return_act} the {gap_word}.",
        synonyms={
            "intro": ("Route", "Compute", "Build", "Derive", "Split", "Resolve"),
            "tally_word": ("total", "sum", "count", "figure", "balance"),
            "return_act": ("returns", "reports", "yields", "emits", "gives"),
            "gap_word": ("difference", "spread", "net", "margin", "gap"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],             "hi": 30, "lo": 5},
        {"items": [40],           "hi": 30, "lo": 5},
        {"items": [2, 35, 5, 28], "hi": 30, "lo": 5},
    ),
)
