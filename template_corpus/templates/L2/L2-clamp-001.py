"""L2-clamp-001 - Upper-bound clamp (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if x > ceil: return ceil; return x
  -> ROR=3 (Gt), BM=2 (ceil in compare), CR=3 (ceil in return), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-clamp-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(8, 13),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "ceil":    IntRange(lo=20, hi=99),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    if {x} > {ceil}:
        return {ceil}
    return {x}
""",

    oracle=lambda x, ceil: ceil if x > ceil else x,

    docstring_template=DocstringTemplate(
        template="{intro} the input as-is while it {stays_under} the {limit}, and {cap_action} it there {otherwise}.",
        synonyms={
            "intro": ("Return", "Pass", "Forward", "Relay", "Carry", "Hand back"),
            "stays_under": ("stays under", "remains below", "sits beneath", "keeps below", "holds under", "rests below"),
            "limit": ("ceiling", "upper bound", "maximum", "top", "upper limit", "cap"),
            "cap_action": ("caps", "pins", "holds", "fixes", "clips", "bounds"),
            "otherwise": ("otherwise", "once it passes", "beyond that", "when it exceeds", "after that point"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,   "ceil": 50},
        {"x": 99,  "ceil": 50},
        {"x": 50,  "ceil": 50},
    ),
)
