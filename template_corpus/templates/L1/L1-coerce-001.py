"""L1-coerce-001 - Convert a Celsius temperature to Fahrenheit using integer arithmetic.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 14 (HIGH).

Updated pattern to keep in band: c * 2 + 32  -> AOR=2, CR=3, RSM=1 (total 6).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-coerce-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(3, 9),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "c":       IdentifierBank(role="single_item"),
        "scale":   IntRange(lo=2, hi=5),
        "offset":  IntRange(lo=10, hi=50),
    },

    body_skeleton="""
def {fn_name}({c}):
    \"\"\"{docstring}\"\"\"
    return {c} * {scale} + {offset}
""",

    oracle=lambda c, scale, offset: c * scale + offset,

    docstring_template=DocstringTemplate(
        template="{intro} a {kind_word} {action_word} of the input using a fixed scale and offset.",
        synonyms={
            "intro": ("Return", "Convert", "Translate", "Yield", "Transform", "Produce", "Calculate"),
            "kind_word": ("linear", "scaled", "affine", "weighted", "proportional", "shifted"),
            "action_word": ("conversion", "transformation", "mapping", "rescaling", "translation"),
        },
    ),

    smoke_test_inputs=(
        {"c": 0,   "scale": 2, "offset": 32},
        {"c": 100, "scale": 3, "offset": 10},
        {"c": -40, "scale": 4, "offset": 20},
    ),
)
