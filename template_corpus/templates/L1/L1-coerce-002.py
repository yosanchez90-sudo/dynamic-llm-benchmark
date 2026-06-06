"""L1-coerce-002 - Compute the new principal after one period of integer interest.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 8.
Pattern: p + p * r // c  -> AOR=4, CR=3, RSM=1 (total 8).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-coerce-002",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(5, 11),

    parameter_spec={
        "fn_name":   IdentifierBank(role="function_L1"),
        "principal": IdentifierBank(role="single_item"),
        "rate":      IdentifierBank(role="single_item", avoid_collision_with=("principal",)),
        "divisor":   IntRange(lo=50, hi=200),
    },

    body_skeleton="""
def {fn_name}({principal}, {rate}):
    \"\"\"{docstring}\"\"\"
    return {principal} + {principal} * {rate} // {divisor}
""",

    oracle=lambda principal, rate, divisor: principal + principal * rate // divisor,

    docstring_template=DocstringTemplate(
        template="{intro} the {result_word} after one period of integer interest at the given rate.",
        synonyms={
            "intro": ("Return", "Compute", "Calculate", "Determine", "Produce", "Yield"),
            "result_word": ("balance", "principal", "amount", "value", "total", "accumulated sum"),
        },
    ),

    smoke_test_inputs=(
        {"principal": 1000, "rate": 5,  "divisor": 100},
        {"principal": 500,  "rate": 10, "divisor": 100},
        {"principal": 0,    "rate": 5,  "divisor": 100},
    ),
)
