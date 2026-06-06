"""L2-range-002 - Band membership via conjunction (single compound decision).

Tier L2: CC=3 (if + BoolOp 'and'), AST depth 1. Target mutant band 10-15.
Pattern: if x >= lo and x <= hi: return x; return default
  -> ROR=6 (GtE + LtE), BM=4 (lo, hi), LOR=1 (and), RSM=2.
  `default` is a passthrough identifier (no CR) to keep the count in band.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-range-002",
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
    if {x} >= {lo} and {x} <= {hi}:
        return {x}
    return {default}
""",

    oracle=lambda x, default, lo, hi: x if (x >= lo and x <= hi) else default,

    docstring_template=DocstringTemplate(
        template="{intro} the input {unchanged} when it {sits_within} {both_word} bounds together, and the {else_word} input {otherwise}.",
        synonyms={
            "intro": ("Return", "Accept", "Pass", "Yield", "Keep", "Emit"),
            "unchanged": ("unchanged", "as-is", "untouched", "verbatim", "intact", "as given"),
            "sits_within": ("sits within", "lies inside", "falls within", "stays between", "is bounded by", "rests inside"),
            "both_word": ("both", "the two", "its", "each of its", "the pair of"),
            "else_word": ("fallback", "spare", "reserve", "alternative", "secondary", "standby"),
            "otherwise": ("otherwise", "in every other case", "for out-of-band inputs", "once it strays", "past the limits"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,  "default": 0, "lo": 10, "hi": 50},
        {"x": 30, "default": 0, "lo": 10, "hi": 50},
        {"x": 99, "default": 1, "lo": 10, "hi": 50},
    ),
)
