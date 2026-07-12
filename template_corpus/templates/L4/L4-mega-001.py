"""L4-mega-001 - Guarded nested three-way relation pass plus a three-key reduce pass.

Tier L4: CC=11 (guard + for/for + if/elif/elif + for + if/elif/elif). The
densest L4 shape, held in range by Name-based accumulation in the nested loop.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, k1, k2, hi):
    if not items:
        return 0
    a = 0
    for x in items:
        for y in items:
            if x == y:
                a += x
            elif x > y:
                a += y
            elif x < y:
                a -= 1
    b = 0
    for z in items:
        if z == k1:
            b += z
        elif z == k2:
            b += 1
        elif z > hi:
            b -= 1
    return a + b


template = Template(
    template_id="L4-mega-001",
    declared_tier="L4",
    declared_ast_depth=5,
    expected_mutant_count=(36, 42),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "a":       IdentifierBank(role="accumulator"),
        "b":       IdentifierBank(role="accumulator", avoid_collision_with=("a",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "z":       IdentifierBank(role="single_item", avoid_collision_with=("x", "y")),
        "k1":      IntRange(lo=5, hi=18),
        "k2":      IntRange(lo=20, hi=35),
        "hi":      IntRange(lo=38, hi=55),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {a} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} == {y}:
                {a} += {x}
            elif {x} > {y}:
                {a} += {y}
            elif {x} < {y}:
                {a} -= 1
    {b} = 0
    for {z} in {items}:
        if {z} == {k1}:
            {b} += {z}
        elif {z} == {k2}:
            {b} += 1
        elif {z} > {hi}:
            {b} -= 1
    return {a} + {b}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} ordered pairs by {relation_word}, then {reduce_act} against two keys and a ceiling.",
        synonyms={
            "intro": ("Evaluate", "Process", "Resolve", "Compute", "Weigh", "Sweep"),
            "relation_word": ("ordering", "relative size", "comparison", "relation", "sizing"),
            "reduce_act": ("reduce", "fold", "collapse", "settle", "distil"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],             "k1": 10, "k2": 25, "hi": 45},
        {"items": [25],           "k1": 10, "k2": 25, "hi": 45},
        {"items": [10, 50, 25, 7], "k1": 10, "k2": 25, "hi": 45},
    ),
)
