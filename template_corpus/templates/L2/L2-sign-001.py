"""L2-sign-001 - Three-way sign classification around zero (if/elif/else).

Tier L2: CC=3, AST depth 2. Target mutant band 10-15.
Pattern: if x > 0: return pos; elif x < 0: return neg; return 0
  -> ROR=6 (Gt + Lt), BM=4 (the two literal 0 compare operands),
     CR=1 (the 0 in 'return 0'), RSM=3.
  pos/neg are passthrough identifiers (no CR) to keep the count in band.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-sign-001",
    declared_tier="L2",
    declared_ast_depth=2,
    expected_mutant_count=(11, 16),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "x":       IdentifierBank(role="single_item"),
        "pos":     IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "neg":     IdentifierBank(role="single_item", avoid_collision_with=("x", "pos")),
    },

    body_skeleton="""
def {fn_name}({x}, {pos}, {neg}):
    \"\"\"{docstring}\"\"\"
    if {x} > 0:
        return {pos}
    elif {x} < 0:
        return {neg}
    return 0
""",

    oracle=lambda x, pos, neg: pos if x > 0 else neg if x < 0 else 0,

    docstring_template=DocstringTemplate(
        template="{intro} a {pos_word} flag above zero, the {neg_word} one below, and {zero_word} {otherwise}.",
        synonyms={
            "intro": ("Return", "Report", "Produce", "Yield", "Signal", "Emit"),
            "pos_word": ("positive", "upward", "rising", "high", "plus", "raised"),
            "neg_word": ("negative", "downward", "falling", "low", "minus", "dropped"),
            "zero_word": ("a neutral code", "a flat reading", "no offset", "a null mark", "a centred code"),
            "otherwise": ("otherwise", "at the origin", "when neither holds", "for a flat input", "right at the centre"),
        },
    ),

    smoke_test_inputs=(
        {"x": 7,  "pos": 1, "neg": -1},
        {"x": -3, "pos": 1, "neg": -1},
        {"x": 0,  "pos": 1, "neg": -1},
    ),
)
