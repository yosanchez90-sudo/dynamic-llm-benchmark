"""L4-tally2-001 - Guarded nested three-way relation tally plus a reduce pass.

Tier L4: CC=9 (guard + for/for + if/elif/elif + for + if). Equality-led so the
dense nested branch stays inside the L4 range.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi):
    if not items:
        return 0
    score = 0
    for x in items:
        for y in items:
            if x == y:
                score += 1
            elif x > y:
                score += 2
            elif x < y:
                score -= 1
    bonus = 0
    for z in items:
        if z > hi:
            bonus += z
    return score + bonus


template = Template(
    template_id="L4-tally2-001",
    declared_tier="L4",
    declared_ast_depth=5,
    expected_mutant_count=(29, 35),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "score":   IdentifierBank(role="accumulator"),
        "bonus":   IdentifierBank(role="accumulator", avoid_collision_with=("score",)),
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
    {score} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} == {y}:
                {score} += 1
            elif {x} > {y}:
                {score} += 2
            elif {x} < {y}:
                {score} -= 1
    {bonus} = 0
    for {z} in {items}:
        if {z} > {hi}:
            {bonus} += {z}
    return {score} + {bonus}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} ordered pairs by {relation_word}, then {add_act} an over-cap bonus.",
        synonyms={
            "intro": ("Score", "Tally", "Weigh", "Rank", "Classify", "Sweep"),
            "relation_word": ("ordering", "relative size", "comparison", "relation", "sizing"),
            "add_act": ("add", "fold in", "credit", "bank", "layer on"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],          "hi": 30},
        {"items": [15],        "hi": 30},
        {"items": [5, 35, 5],  "hi": 30},
    ),
)
