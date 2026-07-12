"""L4-partition-001 - Split into two lists, then reduce each in its own pass.

Tier L4: CC=8 (for + if/elif + for + if + for + if). Three loops, two lists.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, t):
    highs = []
    lows = []
    for x in items:
        if x > t:
            highs.append(x)
        elif x < t:
            lows.append(x)
        else:
            highs.append(0)
    score = 0
    for h in highs:
        if h > t:
            score += h
    for l in lows:
        if l < 0:
            score -= 1
    return score


template = Template(
    template_id="L4-partition-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(30, 36),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "highs":   IdentifierBank(role="accumulator"),
        "lows":    IdentifierBank(role="accumulator", avoid_collision_with=("highs",)),
        "score":   IdentifierBank(role="accumulator", avoid_collision_with=("highs", "lows")),
        "x":       IdentifierBank(role="single_item"),
        "h":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "l":       IdentifierBank(role="single_item", avoid_collision_with=("x", "h")),
        "t":       IntRange(lo=10, hi=40),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {highs} = []
    {lows} = []
    for {x} in {items}:
        if {x} > {t}:
            {highs}.append({x})
        elif {x} < {t}:
            {lows}.append({x})
        else:
            {highs}.append(0)
    {score} = 0
    for {h} in {highs}:
        if {h} > {t}:
            {score} += {h}
    for {l} in {lows}:
        if {l} < 0:
            {score} -= 1
    return {score}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} entries into {high_word} and {low_word} groups, then {reduce_act} each.",
        synonyms={
            "intro": ("Split", "Partition", "Divide", "Separate", "Sort", "Route"),
            "high_word": ("upper", "high", "top", "greater", "over-line"),
            "low_word": ("lower", "small", "bottom", "lesser", "under-line"),
            "reduce_act": ("reduces", "folds", "totals", "scores", "collapses"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],             "t": 20},
        {"items": [25],           "t": 20},
        {"items": [5, 30, -2, 20], "t": 20},
    ),
)
