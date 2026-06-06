"""L2-validator-001 - Guard clause then linear transform (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if x < floor: return default; return x * k + c
  -> ROR=3 (Lt), BM=2 (floor), AOR=2 (*, +), CR (scale, bias), RSM=2.
  `default` is a passthrough identifier (no CR) to keep the count in band.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-validator-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(12, 17),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L2"),
        "x":        IdentifierBank(role="single_item"),
        "default":  IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "floor":    IntRange(lo=1, hi=20),
        "scale":    IntRange(lo=2, hi=9),
        "bias":     IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}, {default}):
    \"\"\"{docstring}\"\"\"
    if {x} < {floor}:
        return {default}
    return {x} * {scale} + {bias}
""",

    oracle=lambda x, default, floor, scale, bias: default if x < floor else x * scale + bias,

    docstring_template=DocstringTemplate(
        template="{intro} the {fallback_word} input when the first {falls_below} the {limit}, and {otherwise} a {transform_word} of it.",
        synonyms={
            "intro": ("Return", "Provide", "Produce", "Yield", "Supply", "Output", "Emit"),
            "fallback_word": ("secondary", "alternative", "spare", "reserve", "backup", "standby"),
            "falls_below": ("falls below", "is under", "stays beneath", "lies below", "drops under", "sits short of"),
            "limit": ("floor", "lower bound", "minimum", "base level", "lower limit", "cutoff"),
            "otherwise": ("otherwise", "in every other case", "for valid inputs", "for the remaining inputs", "above that point"),
            "transform_word": ("scaled, shifted form", "weighted, offset version", "rescaled mix", "linear reshaping", "stretched and shifted reading"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,  "default": 1, "floor": 10, "scale": 3, "bias": 4},
        {"x": 50, "default": 2, "floor": 10, "scale": 2, "bias": 7},
        {"x": 10, "default": 3, "floor": 10, "scale": 4, "bias": 2},
    ),
)
