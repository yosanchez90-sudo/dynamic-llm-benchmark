"""L2-validator-002 - Out-of-range rejection via disjunction (compound decision).

Tier L2: CC=3 (if + BoolOp 'or'), AST depth 1. Target mutant band 10-15.
Pattern: if x < lo or x > hi: return default; return x
  -> ROR=6 (Lt + Gt), BM=4 (lo, hi), LOR=1 (or), RSM=2.
  `default` is a passthrough identifier (no CR) to keep the count in band.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-validator-002",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(10, 15),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "default": IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "lo":      IntRange(lo=2, hi=20),
        "hi":      IntRange(lo=40, hi=90),
    },

    body_skeleton="""
def {fn_name}({x}, {default}):
    \"\"\"{docstring}\"\"\"
    if {x} < {lo} or {x} > {hi}:
        return {default}
    return {x}
""",

    oracle=lambda x, default, lo, hi: default if (x < lo or x > hi) else x,

    docstring_template=DocstringTemplate(
        template="{intro} the {else_word} input when the {primary_word} input {breaks} {either_word} bound, and the input {otherwise}.",
        synonyms={
            "intro": ("Return", "Substitute", "Replace with", "Yield", "Fall back to", "Emit", "Swap in"),
            "else_word": ("fallback", "spare", "reserve", "alternative", "secondary", "standby", "backup"),
            "primary_word": ("primary", "main", "first", "leading", "core", "chief", "given"),
            "breaks": ("breaks", "violates", "breaches", "oversteps", "escapes", "exceeds", "slips past"),
            "either_word": ("either", "one", "any", "a single", "some", "a defined"),
            "otherwise": ("otherwise", "for accepted inputs", "once inside", "while within both", "if it conforms", "for valid inputs"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,  "default": 0, "lo": 10, "hi": 50},
        {"x": 30, "default": 0, "lo": 10, "hi": 50},
        {"x": 99, "default": 1, "lo": 10, "hi": 50},
    ),
)
