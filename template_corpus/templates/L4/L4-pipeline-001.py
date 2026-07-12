"""L4-pipeline-001 - Two-phase pipeline: nested pair-flagging then a filter pass.

Tier L4: CC=9 (guard + for/for + if/elif + for + if/elif). Multiple interacting
loops, two accumulators carried between phases. Target 25-40 mutants (pre-cap).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo, base):
    if not items:
        return base
    flagged = 0
    for x in items:
        for y in items:
            if x + y > hi:
                flagged += 1
            elif x - y == lo:
                flagged += 2
    total = 0
    for z in items:
        if z > flagged:
            total += z
        elif z == lo:
            total -= 1
    return total + flagged


template = Template(
    template_id="L4-pipeline-001",
    declared_tier="L4",
    declared_ast_depth=4,
    expected_mutant_count=(35, 41),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "flagged": IdentifierBank(role="accumulator"),
        "total":   IdentifierBank(role="accumulator", avoid_collision_with=("flagged",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "z":       IdentifierBank(role="single_item", avoid_collision_with=("x", "y")),
        "hi":      IntRange(lo=15, hi=40),
        "lo":      IntRange(lo=2, hi=12),
        "base":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {base}
    {flagged} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} + {y} > {hi}:
                {flagged} += 1
            elif {x} - {y} == {lo}:
                {flagged} += 2
    {total} = 0
    for {z} in {items}:
        if {z} > {flagged}:
            {total} += {z}
        elif {z} == {lo}:
            {total} -= 1
    return {total} + {flagged}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a two-phase {metric_word}: {flag_act} pairs, then {fold_act} the survivors.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Derive", "Build", "Evaluate"),
            "metric_word": ("score", "tally", "figure", "result", "reading"),
            "flag_act": ("flag", "rank", "weigh", "rate", "mark"),
            "fold_act": ("fold in", "accumulate", "combine", "reduce", "merge"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "hi": 25, "lo": 5, "base": 3},
        {"items": [10],          "hi": 25, "lo": 5, "base": 3},
        {"items": [4, 18, 30, 2], "hi": 25, "lo": 5, "base": 3},
    ),
)
