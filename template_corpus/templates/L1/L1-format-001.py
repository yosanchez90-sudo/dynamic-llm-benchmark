"""L1-format-001 - Format a scaled float to a fixed-precision string.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 5.
Pattern: format(v*c, '.Nf')  -> AOR=1, CR=3, RSM=1 (total 5).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-format-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(2, 8),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L1"),
        "v":        IdentifierBank(role="single_item"),
        "scale":    IntRange(lo=2, hi=100),
        "decimals": IntRange(lo=2, hi=6),
    },

    body_skeleton="""
def {fn_name}({v}):
    \"\"\"{docstring}\"\"\"
    return format({v} * {scale}, '.{decimals}f')
""",

    oracle=lambda v, scale, decimals: format(v * scale, f'.{decimals}f'),

    docstring_template=DocstringTemplate(
        template="{intro} the scaled value as a fixed-precision {target_form}.",
        synonyms={
            "intro": ("Return", "Format", "Render", "Produce", "Display", "Convert"),
            "target_form": ("string", "decimal", "representation", "text form", "formatted output"),
        },
    ),

    smoke_test_inputs=(
        {"v": 3.14159, "scale": 10, "decimals": 2},
        {"v": 0.0,     "scale": 5,  "decimals": 4},
        {"v": -2.5,    "scale": 4,  "decimals": 3},
    ),
)
