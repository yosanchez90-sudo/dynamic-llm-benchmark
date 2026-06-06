"""L1-tuple-001 - Build a three-element tuple of arithmetic combinations of two inputs.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 9.
Pattern: (x+c, y*c, x+y)  -> AOR=3, CR=5, RSM=1 (total 9).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-tuple-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(6, 12),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "shift":   IntRange(lo=2, hi=10),
        "scale":   IntRange(lo=2, hi=8),
    },

    body_skeleton="""
def {fn_name}({x}, {y}):
    \"\"\"{docstring}\"\"\"
    return ({x} + {shift}, {y} * {scale}, {x} + {y})
""",

    oracle=lambda x, y, shift, scale: (x + shift, y * scale, x + y),

    docstring_template=DocstringTemplate(
        template="{intro} a {seq_word} of arithmetic combinations of the two inputs.",
        synonyms={
            "intro": ("Return", "Build", "Compose", "Produce", "Form", "Construct", "Yield"),
            "seq_word": ("triple", "trio", "three-tuple", "tuple", "collection", "set"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,   "y": 0,  "shift": 1, "scale": 2},
        {"x": 5,   "y": 3,  "shift": 4, "scale": 3},
        {"x": -2,  "y": 7,  "shift": 5, "scale": 2},
    ),
)
