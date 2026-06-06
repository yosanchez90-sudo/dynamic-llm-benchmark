"""L1-arithmetic-002 - Compute a shifted difference of squares.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 8.
Pattern: x*x - y*y + c  -> AOR=4, CR=3, RSM=1 (total 8).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-arithmetic-002",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(5, 11),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L1"),
        "x":        IdentifierBank(role="single_item"),
        "y":        IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "shift":    IntRange(lo=2, hi=20),
    },

    body_skeleton="""
def {fn_name}({x}, {y}):
    \"\"\"{docstring}\"\"\"
    return {x} * {x} - {y} * {y} + {shift}
""",

    oracle=lambda x, y, shift: x * x - y * y + shift,

    docstring_template=DocstringTemplate(
        template="{intro} the {kind_word} of two squares {adj_phrase} a {constant_word}.",
        synonyms={
            "intro": ("Return", "Compute", "Calculate", "Produce", "Yield", "Evaluate"),
            "kind_word": ("difference", "gap", "spread", "delta", "margin", "subtraction"),
            "adj_phrase": ("shifted by", "offset by", "raised by", "boosted by", "lifted by", "increased by"),
            "constant_word": ("constant", "offset", "shift", "bias", "increment", "addend"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,  "y": 0, "shift": 1},
        {"x": 5,  "y": 3, "shift": 10},
        {"x": -4, "y": 2, "shift": 7},
    ),
)
