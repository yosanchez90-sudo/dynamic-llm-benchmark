"""L3-parse-001 - Accumulate until a stop value, capping each contribution.

Tier L3: CC=4 (for + if/elif; the break is an early exit, not a branch).
Body pattern:
    total = 0
    for x in items:
        if x < 0:
            break
        elif x > cap:
            total += cap
        else:
            total += x
    return total
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, cap):
    total = 0
    for x in items:
        if x < 0:
            break
        elif x > cap:
            total += cap
        else:
            total += x
    return total


template = Template(
    template_id="L3-parse-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(15, 21),   # measured 18; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "total":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "cap":     IntRange(lo=10, hi=40),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {total} = 0
    for {x} in {items}:
        if {x} < 0:
            break
        elif {x} > {cap}:
            {total} += {cap}
        else:
            {total} += {x}
    return {total}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a {sum_word} that {halts} at the first {neg_word}, {caps} {big_word} values, {takes} the rest.",
        synonyms={
            "intro": ("Return", "Compute", "Accumulate", "Produce", "Build"),
            "sum_word": ("total", "sum", "running figure", "tally", "aggregate"),
            "halts": ("halts", "stops", "breaks off", "terminates", "bails out"),
            "neg_word": ("negative", "sub-zero entry", "minus value", "downturn", "drop"),
            "caps": ("caps", "limits", "clips", "bounds", "trims"),
            "big_word": ("large", "oversized", "high", "outsized", "towering"),
            "takes": ("takes", "adds", "folds in", "counts", "keeps"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],              "cap": 20},
        {"items": [5],             "cap": 20},
        {"items": [8, 30, -1, 9],  "cap": 20},
    ),
)
