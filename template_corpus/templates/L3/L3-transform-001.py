"""L3-transform-001 - Map each element through a three-way rule.

Tier L3: CC=4 (for + if/elif; else adds none). Body pattern:
    result = []
    for x in items:
        if x % 2 == 0: result.append(x * k)
        elif x > t:    result.append(c)
        else:          result.append(x)
    return result
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, k, t, c):
    result = []
    for x in items:
        if x % 2 == 0:
            result.append(x * k)
        elif x > t:
            result.append(c)
        else:
            result.append(x)
    return result


template = Template(
    template_id="L3-transform-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(21, 27),   # measured 24; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "result":  IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "k":       IntRange(lo=2, hi=9),
        "t":       IntRange(lo=10, hi=40),
        "c":       IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {result} = []
    for {x} in {items}:
        if {x} % 2 == 0:
            {result}.append({x} * {k})
        elif {x} > {t}:
            {result}.append({c})
        else:
            {result}.append({x})
    return {result}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a list {scaling} {even_word} entries and {swapping} {bigodd_word} ones for a {const_word}.",
        synonyms={
            "intro": ("Return", "Build", "Produce", "Map to", "Assemble", "Compose"),
            "scaling": ("scaling", "doubling", "multiplying", "boosting", "weighting"),
            "even_word": ("even", "divisible", "halvable", "parity-even", "two-fold"),
            "swapping": ("swapping", "replacing", "substituting", "overwriting", "exchanging"),
            "bigodd_word": ("large odd", "high odd", "sizeable odd", "big odd", "upper odd"),
            "const_word": ("constant", "fixed value", "set figure", "flat amount", "preset"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],              "k": 3, "t": 20, "c": 7},
        {"items": [4],             "k": 3, "t": 20, "c": 7},
        {"items": [4, 25, 3, 30],  "k": 3, "t": 20, "c": 7},
    ),
)
