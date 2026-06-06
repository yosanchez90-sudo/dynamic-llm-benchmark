"""L2-classifier-002 - Two-input comparison classifier (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if a > b: return p; return q  (compares two identifiers; no BM site)
  -> ROR=3 (Gt), CR (two labels), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-classifier-002",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(11, 16),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L2"),
        "a":        IdentifierBank(role="single_item"),
        "b":        IdentifierBank(role="single_item", avoid_collision_with=("a",)),
        "win":      IntRange(lo=2, hi=9),
        "lose":     IntRange(lo=2, hi=9),
        "bonus": IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({a}, {b}):
    \"\"\"{docstring}\"\"\"
    if {a} > {b}:
        return {win} * {bonus}
    return {lose}
""",

    oracle=lambda a, b, win, lose, bonus: win * bonus if a > b else lose,

    docstring_template=DocstringTemplate(
        template="{intro} a {winner_word} {score} when one input {exceeds} the other, and a {loser_word} one {otherwise}.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Yield", "Derive", "Output", "Emit", "Report"),
            "winner_word": ("higher", "leading", "dominant", "winning", "greater", "stronger", "top"),
            "score": ("score", "rating", "tally", "figure", "mark", "reward", "tier"),
            "exceeds": ("exceeds", "is greater than", "outranks", "surpasses", "is larger than", "tops", "beats"),
            "loser_word": ("lower", "trailing", "fallback", "losing", "weaker", "reduced", "spare"),
            "otherwise": ("otherwise", "in the remaining case", "when it does not", "for the remaining inputs", "if it ties or trails"),
        },
    ),

    smoke_test_inputs=(
        {"a": 5, "b": 3, "win": 2, "lose": 4, "bonus": 3},
        {"a": 1, "b": 9, "win": 3, "lose": 5, "bonus": 2},
        {"a": 4, "b": 4, "win": 6, "lose": 2, "bonus": 4},
    ),
)
