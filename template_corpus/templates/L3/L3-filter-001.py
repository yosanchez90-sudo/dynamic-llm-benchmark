"""L3-filter-001 - Build a transformed list with a two-sided filter.

Tier L3: CC=4 (for + if/elif), list accumulator. Body pattern:
    result = []
    for x in items:
        if x > t:   result.append(x * k)
        elif x < 0: result.append(0)
    return result
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, t, k):
    result = []
    for x in items:
        if x > t:
            result.append(x * k)
        elif x < 0:
            result.append(0)
    return result


template = Template(
    template_id="L3-filter-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(16, 22),   # measured 19; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "result":  IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "t":       IntRange(lo=5, hi=30),
        "k":       IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {result} = []
    for {x} in {items}:
        if {x} > {t}:
            {result}.append({x} * {k})
        elif {x} < 0:
            {result}.append(0)
    return {result}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a list of {big_word} numbers {scaled}, with zeros for {neg_word} ones.",
        synonyms={
            "intro": ("Return", "Build", "Assemble", "Produce", "Collect", "Compose"),
            "big_word": ("above-threshold", "high", "qualifying", "large", "upper"),
            "scaled": ("scaled by a factor", "weighted", "multiplied", "boosted", "amplified"),
            "neg_word": ("negative", "sub-par", "minus", "deficient", "below-baseline"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],              "t": 10, "k": 2},
        {"items": [15],            "t": 10, "k": 2},
        {"items": [3, 12, -5, 20], "t": 10, "k": 2},
    ),
)
