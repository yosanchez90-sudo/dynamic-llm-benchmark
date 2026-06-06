"""L2-select-001 - Conditional selection via ternary expression.

Tier L2: CC=2 (IfExp), AST depth 0 (ternary is an expression, not a
compound statement). Target mutant band 10-15.
Pattern: return a if x > t else b
  -> ROR=3 (Gt), BM=2 (threshold), CR (a, b), RSM=1 (single return).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-select-001",
    declared_tier="L2",
    declared_ast_depth=0,
    expected_mutant_count=(10, 15),

    parameter_spec={
        "fn_name":   IdentifierBank(role="function_L2"),
        "x":         IdentifierBank(role="single_item"),
        "threshold": IntRange(lo=10, hi=80),
        "high_val":  IntRange(lo=6, hi=9),
        "low_val":   IntRange(lo=2, hi=5),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    return {high_val} if {x} > {threshold} else {low_val}
""",

    oracle=lambda x, threshold, high_val, low_val: high_val if x > threshold else low_val,

    docstring_template=DocstringTemplate(
        template="{intro} the {high_word} {choice} above the {limit} and the {low_word} one below it.",
        synonyms={
            "intro": ("Return", "Select", "Choose", "Yield", "Pick", "Take"),
            "high_word": ("upper", "primary", "first", "greater", "preferred", "top"),
            "choice": ("option", "setting", "value", "pick", "reading", "result"),
            "limit": ("cutoff", "threshold", "boundary", "dividing line", "split point", "trigger"),
            "low_word": ("lower", "secondary", "second", "smaller", "fallback", "spare"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,  "threshold": 40, "high_val": 2, "low_val": 9},
        {"x": 90, "threshold": 40, "high_val": 3, "low_val": 8},
        {"x": 40, "threshold": 40, "high_val": 4, "low_val": 7},
    ),
)
