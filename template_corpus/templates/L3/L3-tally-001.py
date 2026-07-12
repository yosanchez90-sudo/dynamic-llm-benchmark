"""L3-tally-001 - Weighted tally over three recognised keys (equality chain).

Tier L3: CC=5 (for + if/elif/elif). Equality comparisons keep ROR cheap so a
three-way branch stays inside the L3 band. Body pattern:
    total = 0
    for x in items:
        if x == k1:   total += w1
        elif x == k2: total += w2
        elif x == k3: total += w3
    return total
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, k1, k2, k3, w1, w2, w3):
    total = 0
    for x in items:
        if x == k1:
            total += w1
        elif x == k2:
            total += w2
        elif x == k3:
            total += w3
    return total


template = Template(
    template_id="L3-tally-001",
    declared_tier="L3",
    declared_ast_depth=4,
    expected_mutant_count=(21, 27),   # measured 24; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "total":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "k1":      IntRange(lo=1, hi=3),
        "k2":      IntRange(lo=4, hi=6),
        "k3":      IntRange(lo=7, hi=9),
        "w1":      IntRange(lo=2, hi=9),
        "w2":      IntRange(lo=2, hi=9),
        "w3":      IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {total} = 0
    for {x} in {items}:
        if {x} == {k1}:
            {total} += {w1}
        elif {x} == {k2}:
            {total} += {w2}
        elif {x} == {k3}:
            {total} += {w3}
    return {total}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a weighted sum {crediting} three known keys {distinctly} and {skipping} the rest.",
        synonyms={
            "intro": ("Return", "Compute", "Accumulate", "Produce", "Tally"),
            "crediting": ("crediting", "rewarding", "scoring", "weighting", "ranking"),
            "distinctly": ("distinctly", "separately", "individually", "by key", "uniquely"),
            "skipping": ("skipping", "ignoring", "dropping", "discarding", "passing over"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "k1": 2, "k2": 5, "k3": 8, "w1": 3, "w2": 4, "w3": 5},
        {"items": [5],           "k1": 2, "k2": 5, "k3": 8, "w1": 3, "w2": 4, "w3": 5},
        {"items": [2, 8, 2, 0],  "k1": 2, "k2": 5, "k3": 8, "w1": 3, "w2": 4, "w3": 5},
    ),
)
