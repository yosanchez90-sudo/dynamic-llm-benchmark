"""L1-numeric-001 - Apply a rolling update with scaled delta and additive constant.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 9.
Pattern: prev + delta*c1 + c2  -> AOR=3, CR=5, RSM=1 (total 9).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-numeric-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(6, 12),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "prev":    IdentifierBank(role="single_item"),
        "delta":   IdentifierBank(role="single_item", avoid_collision_with=("prev",)),
        "scale":   IntRange(lo=2, hi=12),
        "bias":    IntRange(lo=1, hi=10),
    },

    body_skeleton="""
def {fn_name}({prev}, {delta}):
    \"\"\"{docstring}\"\"\"
    return {prev} + {delta} * {scale} + {bias}
""",

    oracle=lambda prev, delta, scale, bias: prev + delta * scale + bias,

    docstring_template=DocstringTemplate(
        template="{intro} the {target_word} value by {action_word} a scaled delta and a bias.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Update", "Apply", "Yield", "Calculate"),
            "target_word": ("updated", "adjusted", "refreshed", "revised", "incremented", "shifted"),
            "action_word": ("adding", "summing in", "incorporating", "applying", "combining with"),
        },
    ),

    smoke_test_inputs=(
        {"prev": 10, "delta": 2,  "scale": 3, "bias": 5},
        {"prev": 0,  "delta": 0,  "scale": 1, "bias": 1},
        {"prev": -5, "delta": 7,  "scale": 2, "bias": 3},
    ),
)
