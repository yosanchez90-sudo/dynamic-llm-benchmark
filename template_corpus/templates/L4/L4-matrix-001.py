"""L4-matrix-001 - Guarded nested pair scan (conjunction) plus a reduce pass.

Tier L4: CC=9 (guard + for/for + if(and)/elif + for + if). LOR via 'and'/'not'.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi):
    if not items:
        return 0
    pairs = 0
    for x in items:
        for y in items:
            if x > y and x < hi:
                pairs += 1
            elif x == y:
                pairs += 2
    extra = 0
    for z in items:
        if z > hi:
            extra += z
    return pairs + extra


template = Template(
    template_id="L4-matrix-001",
    declared_tier="L4",
    declared_ast_depth=4,
    expected_mutant_count=(29, 35),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "pairs":   IdentifierBank(role="accumulator"),
        "extra":   IdentifierBank(role="accumulator", avoid_collision_with=("pairs",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "z":       IdentifierBank(role="single_item", avoid_collision_with=("x", "y")),
        "hi":      IntRange(lo=20, hi=45),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {pairs} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} > {y} and {x} < {hi}:
                {pairs} += 1
            elif {x} == {y}:
                {pairs} += 2
    {extra} = 0
    for {z} in {items}:
        if {z} > {hi}:
            {extra} += {z}
    return {pairs} + {extra}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} ordered pairs that are {order_word} and {bound_word}, plus over-cap singles.",
        synonyms={
            "intro": ("Count", "Tally", "Score", "Weigh", "Rank", "Sweep"),
            "order_word": ("descending", "out-of-order", "left-heavy", "top-leading", "unequal"),
            "bound_word": ("within-cap", "under-ceiling", "in-range", "capped", "bounded"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],          "hi": 30},
        {"items": [15],        "hi": 30},
        {"items": [10, 35, 10], "hi": 30},
    ),
)
