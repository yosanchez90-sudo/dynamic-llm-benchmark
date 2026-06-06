"""L2-classifier-001 - Binary threshold classifier (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if x < t: return a; return b
  -> ROR=3 (Lt), BM=2 (threshold), CR (two labels), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-classifier-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(10, 15),

    parameter_spec={
        "fn_name":   IdentifierBank(role="function_L2"),
        "x":         IdentifierBank(role="single_item"),
        "threshold": IntRange(lo=10, hi=90),
        "lo_label":  IntRange(lo=2, hi=5),
        "hi_label":  IntRange(lo=6, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}):
    \"\"\"{docstring}\"\"\"
    if {x} < {threshold}:
        return {lo_label}
    return {hi_label}
""",

    oracle=lambda x, threshold, lo_label, hi_label: lo_label if x < threshold else hi_label,

    docstring_template=DocstringTemplate(
        template="{intro} the {low_word} {outcome} when the value {falls_below} the {limit}, and the {high_word} one {otherwise}.",
        synonyms={
            "intro": ("Return", "Report", "Produce", "Yield", "Assign", "Output", "Emit", "Hand back", "Give"),
            "low_word": ("lower", "first", "smaller", "initial", "bottom", "junior", "minor", "base"),
            "outcome": ("category", "class", "band", "group", "tier", "bracket", "rank", "grade"),
            "falls_below": ("falls below", "is under", "stays beneath", "lies below", "drops under", "sits short of", "comes in under", "dips below"),
            "limit": ("threshold", "cutoff", "boundary", "dividing line", "split point", "pivot", "trigger level", "cut line"),
            "high_word": ("upper", "second", "larger", "alternative", "top", "senior", "greater", "raised"),
            "otherwise": ("otherwise", "in every other case", "for the remaining values", "past that point", "above it", "for higher values", "beyond that"),
        },
    ),

    smoke_test_inputs=(
        {"x": 0,   "threshold": 50, "lo_label": 2, "hi_label": 9},
        {"x": 75,  "threshold": 50, "lo_label": 3, "hi_label": 8},
        {"x": 50,  "threshold": 50, "lo_label": 4, "hi_label": 7},
    ),
)
