"""L4-dispatch2-001 - Guarded nested three-way pairwise dispatch plus an adjust pass.

Tier L4: CC=10 (guard + for/for + if/elif/elif + for + if/elif).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo):
    if not items:
        return 0
    rel = 0
    for x in items:
        for y in items:
            if x > y:
                rel += 1
            elif x < y:
                rel -= 1
            elif x == y:
                rel += 2
    cap = 0
    for z in items:
        if z > hi:
            cap += z
        elif z == lo:
            cap += 1
    return rel + cap


template = Template(
    template_id="L4-dispatch2-001",
    declared_tier="L4",
    declared_ast_depth=5,
    expected_mutant_count=(35, 41),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "rel":     IdentifierBank(role="accumulator"),
        "cap":     IdentifierBank(role="accumulator", avoid_collision_with=("rel",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "z":       IdentifierBank(role="single_item", avoid_collision_with=("x", "y")),
        "hi":      IntRange(lo=25, hi=50),
        "lo":      IntRange(lo=2, hi=12),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {rel} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} > {y}:
                {rel} += 1
            elif {x} < {y}:
                {rel} -= 1
            elif {x} == {y}:
                {rel} += 2
    {cap} = 0
    for {z} in {items}:
        if {z} > {hi}:
            {cap} += {z}
        elif {z} == {lo}:
            {cap} += 1
    return {rel} + {cap}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} ordered pairs by {relation_word}, then {adjust_act} for {edge_word} singles.",
        synonyms={
            "intro": ("Dispatch", "Classify", "Route", "Sort", "Weigh", "Rank"),
            "relation_word": ("relative order", "comparison", "ordering", "size", "standing"),
            "adjust_act": ("adjust", "nudge", "shift", "correct", "tune"),
            "edge_word": ("over-cap", "extreme", "boundary", "outlying", "flagged"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],             "hi": 30, "lo": 5},
        {"items": [20],           "hi": 30, "lo": 5},
        {"items": [5, 35, 5, 30], "hi": 30, "lo": 5},
    ),
)
