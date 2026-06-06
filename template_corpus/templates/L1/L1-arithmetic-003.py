"""L1-arithmetic-003 - Compute total cost minus a per-unit discount.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 7.
Pattern: price*qty - qty*c  -> AOR=3, CR=3, RSM=1 (total 7).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L1-arithmetic-003",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(4, 10),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L1"),
        "price":    IdentifierBank(role="single_item"),
        "qty":      IdentifierBank(role="single_item", avoid_collision_with=("price",)),
        "discount": IntRange(lo=1, hi=15),
    },

    body_skeleton="""
def {fn_name}({price}, {qty}):
    \"\"\"{docstring}\"\"\"
    return {price} * {qty} - {qty} * {discount}
""",

    oracle=lambda price, qty, discount: price * qty - discount * qty,

    docstring_template=DocstringTemplate(
        template="{intro} the {target_word} after applying a per-unit {discount_word}.",
        synonyms={
            "intro": ("Return", "Compute", "Calculate", "Determine", "Produce", "Evaluate"),
            "target_word": ("total cost", "net amount", "final price", "billed total", "settled amount", "payable sum"),
            "discount_word": ("discount", "reduction", "rebate", "markdown", "concession", "deduction"),
        },
    ),

    smoke_test_inputs=(
        {"price": 10, "qty": 5, "discount": 2},
        {"price": 0,  "qty": 0, "discount": 1},
        {"price": 25, "qty": 3, "discount": 5},
    ),
)
