"""L3-nested2-001 - Conditional nested scan (gate then inner two-way rule).

Tier L3: CC=6 (for + if + for + if/elif). Equality keeps the inner ROR cheap.
Body pattern:
    count = 0
    for x in items:
        if x > t:
            for y in items:
                if y < x: count += 1
                elif y == x: count += 2
    return count
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, t):
    count = 0
    for x in items:
        if x > t:
            for y in items:
                if y < x:
                    count += 1
                elif y == x:
                    count += 2
    return count


template = Template(
    template_id="L3-nested2-001",
    declared_tier="L3",
    declared_ast_depth=5,
    expected_mutant_count=(16, 22),   # measured 19; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "count":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "t":       IntRange(lo=10, hi=40),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {count} = 0
    for {x} in {items}:
        if {x} > {t}:
            for {y} in {items}:
                if {y} < {x}:
                    {count} += 1
                elif {y} == {x}:
                    {count} += 2
    return {count}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro}, per number {abovegate}, how many later entries {rank_below} or {match_word} it.",
        synonyms={
            "intro": ("Return a count", "Tally", "Report", "Compute", "Total"),
            "abovegate": ("above the gate", "past the threshold", "over the cut", "beyond the bar", "clearing the mark"),
            "rank_below": ("rank below", "sit under", "trail", "undercut", "fall short of"),
            "match_word": ("tie with", "equal", "coincide with", "level with", "mirror"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "t": 20},
        {"items": [25],          "t": 20},
        {"items": [5, 25, 25, 30], "t": 20},
    ),
)
