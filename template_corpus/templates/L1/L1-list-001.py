"""L1-list-001 - Build a three-element list by scaling the input with two multipliers.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 9.
Pattern: [x, x*c1, x*c2]  -> AOR=2, CR=6, RSM=1 (total 9).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-list-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(6, 12),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "x":       IdentifierBank(role="single_item"),
        "mid":     IntRange(lo=2, hi=5),
        "high":    IntRange(lo=6, hi=12),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    return [{x}, {x} * {mid}, {x} * {high}]
""",

    oracle=lambda x, mid, high: [x, x * mid, x * high],

    docstring_template=DocstringTemplate(
        template="{intro} a three-element {seq_word} of the input scaled by two multipliers.",
        synonyms={
            "intro": ("Return", "Build", "Produce", "Generate", "Compose", "Construct"),
            "seq_word": ("list", "sequence", "set", "triple", "trio", "collection"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,  "mid": 2, "high": 10},
        {"x": 5,  "mid": 3, "high": 7},
        {"x": -2, "mid": 4, "high": 8},
    ),
)
