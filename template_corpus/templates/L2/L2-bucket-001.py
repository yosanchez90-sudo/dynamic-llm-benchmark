"""L2-bucket-001 - Pivot comparison into three outcomes (two sequential ifs).

Tier L2: CC=3, AST depth 1. Target mutant band 10-15.
Pattern: if x > pivot: return above; if x == pivot: return equal; return pivot
  Compares two identifiers (x, pivot) so no BM site on the conditions.
  -> ROR=4 (Gt + Eq), CR (above, equal), RSM=3.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-bucket-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(10, 15),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "pivot":   IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "above":   IntRange(lo=2, hi=9),
        "equal":   IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}, {pivot}):
    \"\"\"{docstring}\"\"\"
    if {x} > {pivot}:
        return {above}
    if {x} == {pivot}:
        return {equal}
    return {pivot}
""",

    oracle=lambda x, pivot, above, equal: (
        above if x > pivot else equal if x == pivot else pivot
    ),

    docstring_template=DocstringTemplate(
        template="{intro} {above_code} above the {pivot_word}, {equal_code} alongside it, and that value below.",
        synonyms={
            "intro": ("Return", "Report", "Produce", "Yield", "Signal", "Emit"),
            "above_code": ("a high tag", "an upper score", "a top mark", "a raised token", "a plus label", "an over code"),
            "pivot_word": ("pivot", "reference", "midpoint", "anchor", "benchmark", "datum"),
            "equal_code": ("a level flag", "an even rating", "a tie value", "a match cue", "a centre note", "a steady reading"),
        },
    ),

    smoke_test_inputs=(
        {"x": 9, "pivot": 5, "above": 2, "equal": 3},
        {"x": 5, "pivot": 5, "above": 4, "equal": 7},
        {"x": 1, "pivot": 5, "above": 8, "equal": 6},
    ),
)
