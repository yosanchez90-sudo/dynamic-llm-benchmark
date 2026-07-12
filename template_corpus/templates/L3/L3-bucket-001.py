"""L3-bucket-001 - Score a sequence by a two-band scheme.

Tier L3: CC=4 (for + if/elif), single accumulator. Body pattern:
    score = 0
    for x in items:
        if x > hi:   score += 2
        elif x > lo: score += 1
    return score
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, hi, lo):
    score = 0
    for x in items:
        if x > hi:
            score += 2
        elif x > lo:
            score += 1
    return score


template = Template(
    template_id="L3-bucket-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(17, 23),   # measured 20; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "score":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "hi":      IntRange(lo=20, hi=50),
        "lo":      IntRange(lo=5, hi=15),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {score} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {score} += 2
        elif {x} > {lo}:
            {score} += 1
    return {score}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a {score_word}: two points {reach1} the upper mark, one {reach2} the lower.",
        synonyms={
            "intro": ("Return", "Compute", "Tally", "Accumulate", "Produce"),
            "score_word": ("score", "weighted count", "rating", "figure", "running total"),
            "reach1": ("above", "over", "past", "beyond", "topping"),
            "reach2": ("clearing", "exceeding", "surpassing", "outranking", "crossing"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],               "hi": 30, "lo": 10},
        {"items": [40],             "hi": 30, "lo": 10},
        {"items": [5, 12, 35, 50],  "hi": 30, "lo": 10},
    ),
)
