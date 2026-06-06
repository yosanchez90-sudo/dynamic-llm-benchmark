"""L2-clamp-002 - Lower-bound clamp (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if x < floor: return floor; return x
  -> ROR=3 (Lt), BM=2 (floor in compare), CR=3 (floor in return), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-clamp-002",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(8, 13),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "floor":   IntRange(lo=2, hi=40),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    if {x} < {floor}:
        return {floor}
    return {x}
""",

    oracle=lambda x, floor: floor if x < floor else x,

    docstring_template=DocstringTemplate(
        template="{intro} the input as-is while it {stays_over} the {limit}, and {raise_action} it there {otherwise}.",
        synonyms={
            "intro": ("Return", "Pass", "Forward", "Relay", "Carry", "Hand back"),
            "stays_over": ("stays over", "remains above", "sits beyond", "keeps above", "holds over", "rests above"),
            "limit": ("floor", "lower bound", "minimum", "base", "lower limit", "ground level"),
            "raise_action": ("raises", "lifts", "pulls", "fixes", "snaps", "bounds"),
            "otherwise": ("otherwise", "once it dips below", "beneath that", "when it falls short", "under that point"),
        },
    ),

    smoke_test_inputs=(
        {"x": 50, "floor": 10},
        {"x": 1,  "floor": 10},
        {"x": 10, "floor": 10},
    ),
)
