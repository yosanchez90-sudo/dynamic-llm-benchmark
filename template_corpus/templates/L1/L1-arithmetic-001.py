"""L1-arithmetic-001 - Apply a linear combination of two inputs.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 10.
Pattern: x * c1 + y - c2  -> AOR=3, CR=6, RSM=1 (total 10).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-arithmetic-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(7, 13),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L1"),
        "x":        IdentifierBank(role="single_item"),
        "y":        IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "factor":   IntRange(lo=2, hi=10),
        "offset":   IntRange(lo=1, hi=20),
    },

    body_skeleton="""
def {fn_name}({x}, {y}):
    \"\"\"{docstring}\"\"\"
    return {x} * {factor} + {y} - {offset}
""",

    oracle=lambda x, y, factor, offset: x * factor + y - offset,

    docstring_template=DocstringTemplate(
        template="{intro} a linear {action_noun} of the inputs {scaled_by} a factor and {shifted_by} an offset.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Yield", "Calculate", "Evaluate"),
            "action_noun": ("combination", "transformation", "expression", "blend", "mixture", "fusion"),
            "scaled_by": ("scaled by", "multiplied by", "weighted by", "amplified by", "boosted by"),
            "shifted_by": ("shifted by", "reduced by", "decreased by", "lowered by", "diminished by"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,   "y": 0,   "factor": 3, "offset": 5},
        {"x": 10,  "y": 7,   "factor": 4, "offset": 1},
        {"x": -3,  "y": 2,   "factor": 5, "offset": 8},
    ),
)
