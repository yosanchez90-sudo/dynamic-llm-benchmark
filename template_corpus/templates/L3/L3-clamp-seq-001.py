"""L3-clamp-seq-001 - Clamp every element into [lo, hi] (build a new list).

Tier L3: CC=4 (for + if/elif; the else adds no decision). Body pattern:
    result = []
    for x in items:
        if x < lo:   result.append(lo)
        elif x > hi: result.append(hi)
        else:        result.append(x)
    return result
The bound literals appear once in a comparison (BM site) and once in an
append (CR site), so the same value drives both operator families.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, lo, hi):
    result = []
    for x in items:
        if x < lo:
            result.append(lo)
        elif x > hi:
            result.append(hi)
        else:
            result.append(x)
    return result


template = Template(
    template_id="L3-clamp-seq-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(18, 24),   # measured 21; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "result":  IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "lo":      IntRange(lo=2, hi=12),
        "hi":      IntRange(lo=20, hi=50),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {result} = []
    for {x} in {items}:
        if {x} < {lo}:
            {result}.append({lo})
        elif {x} > {hi}:
            {result}.append({hi})
        else:
            {result}.append({x})
    return {result}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a list with values {confined} {between_word} the floor and ceiling, {else_word} unchanged.",
        synonyms={
            "intro": ("Return", "Build", "Produce", "Assemble", "Compose", "Yield"),
            "confined": ("confined", "clamped", "pinned", "bounded", "held"),
            "between_word": ("between", "inside", "within", "across", "amid"),
            "else_word": ("otherwise", "or else", "failing which", "when mid-range", "in between"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],              "lo": 5, "hi": 30},
        {"items": [40],            "lo": 5, "hi": 30},
        {"items": [1, 18, 35, 7],  "lo": 5, "hi": 30},
    ),
)
