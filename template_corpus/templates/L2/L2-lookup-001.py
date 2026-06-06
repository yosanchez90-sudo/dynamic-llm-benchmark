"""L2-lookup-001 - Discrete lookup table via equality chain (if/elif/else).

Tier L2: CC=3, AST depth 2. Target mutant band 10-15.
Pattern: if x == k1: return a; elif x == k2: return b; return fallback
  -> ROR=2 (two Eq), BM=4 (k1, k2 in compares), CR (a, b), RSM=3.
  `fallback` is a passthrough identifier (no CR) to hold the count in band.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


template = Template(
    template_id="L2-lookup-001",
    declared_tier="L2",
    declared_ast_depth=2,
    expected_mutant_count=(12, 17),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L2"),
        "x":        IdentifierBank(role="single_item"),
        "fallback": IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "key1":     IntRange(lo=1, hi=4),
        "key2":     IntRange(lo=5, hi=9),
        "hit1":     IntRange(lo=2, hi=9),
        "hit2":     IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({x}, {fallback}):
    \"\"\"{docstring}\"\"\"
    if {x} == {key1}:
        return {hit1}
    elif {x} == {key2}:
        return {hit2}
    return {fallback}
""",

    oracle=lambda x, fallback, key1, key2, hit1, hit2: (
        hit1 if x == key1 else hit2 if x == key2 else fallback
    ),

    docstring_template=DocstringTemplate(
        template="{intro} a {coded_word} {result} for {either_word} known key, and the {else_word} input for anything else.",
        synonyms={
            "intro": ("Return", "Map", "Look up", "Yield", "Resolve", "Emit"),
            "coded_word": ("dedicated", "mapped", "specific", "assigned", "preset", "reserved"),
            "result": ("code", "label", "token", "output", "reading", "tag"),
            "either_word": ("each", "either", "every", "a matching", "any listed", "a registered"),
            "else_word": ("fallback", "spare", "reserve", "alternative", "secondary", "standby"),
        },
    ),

    smoke_test_inputs=(
        {"x": 2, "fallback": 0, "key1": 2, "key2": 7, "hit1": 3, "hit2": 8},
        {"x": 7, "fallback": 0, "key1": 2, "key2": 7, "hit1": 4, "hit2": 6},
        {"x": 5, "fallback": 1, "key1": 2, "key2": 7, "hit1": 2, "hit2": 9},
    ),
)
