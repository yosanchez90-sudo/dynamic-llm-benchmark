"""L2-flag-001 - Boolean-gated transform via negation (single decision).

Tier L2: CC=2 (if; the 'not' is a UnaryOp and adds no decision point),
AST depth 1. Target mutant band 10-15.
Pattern: if not flag: return default; return x * k + c
  -> LOR=1 (not removal), AOR=2 (*, +), CR (default, k, c), RSM=2.
  This is the corpus's dedicated LOR-not site.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-flag-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(11, 16),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "flag":    IdentifierBank(role="flag"),
        "default": IntRange(lo=2, hi=9),
        "scale":   IntRange(lo=2, hi=9),
        "bias":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}, {flag}):
    \"\"\"{docstring}\"\"\"
    if not {flag}:
        return {default}
    return {x} * {scale} + {bias}
""",

    oracle=lambda x, flag, default, scale, bias: default if not flag else x * scale + bias,

    docstring_template=DocstringTemplate(
        template="{intro} a {fixed_word} value while the {gate_word} stays {off_word}, and {otherwise} a {transform_word} of it.",
        synonyms={
            "intro": ("Return", "Provide", "Produce", "Yield", "Supply", "Emit", "Hand back"),
            "fixed_word": ("fixed", "constant", "preset", "guard", "default", "standby", "safe"),
            "gate_word": ("flag", "switch", "toggle", "gate", "control", "selector", "lever"),
            "off_word": ("clear", "unset", "false", "disabled", "down", "inactive", "lowered"),
            "otherwise": ("otherwise", "once it is set", "when enabled", "on the active path", "if it is raised", "once active"),
            "transform_word": ("scaled, shifted form", "weighted, offset version", "rescaled mix", "linear reshaping", "stretched reading", "boosted figure"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,  "flag": True,  "default": 2, "scale": 3, "bias": 4},
        {"x": 8,  "flag": False, "default": 5, "scale": 2, "bias": 7},
        {"x": 0,  "flag": True,  "default": 9, "scale": 4, "bias": 2},
    ),
)
