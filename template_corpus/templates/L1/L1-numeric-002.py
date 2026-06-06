"""L1-numeric-002 - Compute the area of a rectangle with a fixed margin removed.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 6.
Pattern: w*h - c  -> AOR=2, CR=3, RSM=1 (total 6).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-numeric-002",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(3, 9),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "w":       IdentifierBank(role="single_item"),
        "h":       IdentifierBank(role="single_item", avoid_collision_with=("w",)),
        "margin":  IntRange(lo=2, hi=20),
    },

    body_skeleton="""
def {fn_name}({w}, {h}):
    \"\"\"{docstring}\"\"\"
    return {w} * {h} - {margin}
""",

    oracle=lambda w, h, margin: w * h - margin,

    docstring_template=DocstringTemplate(
        template="{intro} the {area_word} of a rectangle after subtracting a fixed {margin_word}.",
        synonyms={
            "intro": ("Return", "Compute", "Calculate", "Determine", "Produce", "Yield"),
            "area_word": ("area", "footprint", "surface", "extent", "coverage", "region size"),
            "margin_word": ("margin", "buffer", "border", "padding", "gap", "frame"),
        },
    ),

    smoke_test_inputs=(
        {"w": 10, "h": 5, "margin": 2},
        {"w": 0,  "h": 8, "margin": 1},
        {"w": 4,  "h": 4, "margin": 4},
    ),
)
