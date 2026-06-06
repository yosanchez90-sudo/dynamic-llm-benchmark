"""L2-string-001 - Length-gated transform (single decision).

Tier L2: CC=2, AST depth 1. Target mutant band 10-15.
Pattern: if len(s) > n: return len(s) * k; return n
  -> ROR=3 (Gt), BM=2 (n in compare), AOR=1 (*), CR=3 (k), CR=3 (n in return), RSM=2.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-string-001",
    declared_tier="L2",
    declared_ast_depth=1,
    expected_mutant_count=(12, 17),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L2"),
        "s":       IdentifierBank(role="single_item"),
        "limit":   IntRange(lo=3, hi=20),
        "weight":  IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({s}):
    \"\"\"{docstring}\"\"\"
    if len({s}) > {limit}:
        return len({s}) * {weight}
    return {limit}
""",

    oracle=lambda s, limit, weight: len(s) * weight if len(s) > limit else limit,

    docstring_template=DocstringTemplate(
        template="{intro} a {scaled_word} score from the text length once it {exceeds} the {limit}, and a {fixed_word} value {otherwise}.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Yield", "Report", "Emit"),
            "scaled_word": ("weighted", "scaled", "multiplied", "amplified", "boosted", "stretched"),
            "exceeds": ("exceeds", "runs past", "is greater than", "overruns", "tops", "passes"),
            "limit": ("threshold", "cutoff", "cap", "maximum", "ceiling", "bound"),
            "fixed_word": ("fixed", "constant", "preset", "baseline", "steady", "set"),
            "otherwise": ("otherwise", "in every other case", "when it does not", "for the brief case", "below that point"),
        },
    ),

    smoke_test_inputs=(
        {"s": "abc",        "limit": 5, "weight": 2},
        {"s": "a long text", "limit": 5, "weight": 3},
        {"s": "exact",      "limit": 5, "weight": 4},
    ),
)
