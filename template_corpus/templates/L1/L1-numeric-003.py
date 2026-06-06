"""L1-numeric-003 - Compute the hypotenuse of a right triangle plus a fixed offset.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 10.
Pattern: (a*a + b*b) ** 0.5 + c  -> AOR=5, CR=4, RSM=1 (total 10).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-numeric-003",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(7, 13),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "a":       IdentifierBank(role="single_item"),
        "b":       IdentifierBank(role="single_item", avoid_collision_with=("a",)),
        "offset":  IntRange(lo=1, hi=15),
    },

    body_skeleton="""
def {fn_name}({a}, {b}):
    \"\"\"{docstring}\"\"\"
    return ({a} * {a} + {b} * {b}) ** 0.5 + {offset}
""",

    oracle=lambda a, b, offset: (a * a + b * b) ** 0.5 + offset,

    docstring_template=DocstringTemplate(
        template="{intro} the length of the {target_word} plus an offset.",
        synonyms={
            "intro": ("Return", "Compute", "Calculate", "Determine", "Produce", "Yield"),
            "target_word": ("hypotenuse", "diagonal", "Euclidean distance", "line length", "straight-line span"),
        },
    ),

    smoke_test_inputs=(
        {"a": 3, "b": 4, "offset": 1},
        {"a": 0, "b": 5, "offset": 2},
        {"a": 1, "b": 1, "offset": 0},
    ),
)
