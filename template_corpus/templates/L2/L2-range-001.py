"""L2-range-001 - Membership test via chained comparison (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if lo <= x <= hi: return inside; return outside
  Chained compare is one Compare node with two ops (no BoolOp) -> CC=2.
  -> ROR=6 (two ops), BM=4 (lo, hi), CR (inside, outside), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-range-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(13, 18),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "lo":      IntRange(lo=2, hi=20),
        "hi":      IntRange(lo=40, hi=90),
        "inside":  IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    if {lo} <= {x} <= {hi}:
        return {inside}
    return {x}
""",

    oracle=lambda x, lo, hi, inside: inside if lo <= x <= hi else x,

    docstring_template=DocstringTemplate(
        template="{intro} a {marker_word} for values that {sit_within} the {span_word}, and the value itself {otherwise}.",
        synonyms={
            "intro": ("Return", "Report", "Produce", "Yield", "Signal", "Emit"),
            "marker_word": ("fixed code", "sentinel", "flag figure", "in-range token", "marker", "set value"),
            "sit_within": ("sit within", "lie inside", "fall between", "stay within", "land in", "rest inside"),
            "span_word": ("permitted band", "accepted range", "valid window", "allowed interval", "safe zone", "approved span"),
            "otherwise": ("otherwise", "when they do not", "past either edge", "outside it", "beyond the bounds"),
        },
    ),

    smoke_test_inputs=(
        {"x": 5,  "lo": 10, "hi": 50, "inside": 2},
        {"x": 30, "lo": 10, "hi": 50, "inside": 3},
        {"x": 99, "lo": 10, "hi": 50, "inside": 4},
    ),
)
