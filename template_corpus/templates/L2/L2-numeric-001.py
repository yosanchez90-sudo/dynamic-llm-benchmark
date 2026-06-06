"""L2-numeric-001 - Piecewise transform around zero (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if x < 0: return -x + c; return x + c
  -> ROR=3 (Lt), BM=2 (the 0 in compare), AOR=2 (two +), CR (c twice), RSM=2.
  (the 0 is a compare operand -> BM site, excluded from CR.)
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-numeric-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(12, 17),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "pivot":   IntRange(lo=0, hi=0),
        "shift":   IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    if {x} < {pivot}:
        return -{x} + {shift}
    return {x} + {shift}
""",

    oracle=lambda x, pivot, shift: (-x + shift) if x < pivot else (x + shift),

    docstring_template=DocstringTemplate(
        template="{intro} the {distance_word} of the input from {origin_word}, {raised} by a {fixed_word} amount.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Yield", "Derive", "Emit"),
            "distance_word": ("magnitude", "absolute size", "unsigned size", "reflected size", "folded size", "spread"),
            "origin_word": ("zero", "the origin", "the pivot", "the centre", "the baseline", "the midline"),
            "raised": ("raised", "lifted", "increased", "nudged up", "offset upward", "boosted"),
            "fixed_word": ("fixed", "constant", "preset", "steady", "uniform", "set"),
        },
    ),

    smoke_test_inputs=(
        {"x": -5, "pivot": 0, "shift": 3},
        {"x": 7,  "pivot": 0, "shift": 2},
        {"x": 0,  "pivot": 0, "shift": 4},
    ),
)
