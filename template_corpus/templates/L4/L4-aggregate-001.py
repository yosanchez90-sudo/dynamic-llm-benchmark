"""L4-aggregate-001 - Two sequential loops with a conjunction in the second.

Tier L4: CC=8 (for + if/elif + for + if(and)/elif). Two passes over the input,
state carried between them. Target 25-40 mutants (pre-cap).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo):
    total = 0
    count = 0
    for x in items:
        if x > hi:
            total += x
        elif x == lo:
            count += 1
    adjusted = 0
    for y in items:
        if y > count and y < hi:
            adjusted += y
        elif y == lo:
            adjusted -= 1
    return total + adjusted - count


template = Template(
    template_id="L4-aggregate-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(34, 40),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L4"),
        "items":    IdentifierBank(role="sequence"),
        "total":    IdentifierBank(role="accumulator"),
        "count":    IdentifierBank(role="accumulator", avoid_collision_with=("total",)),
        "adjusted": IdentifierBank(role="accumulator", avoid_collision_with=("total", "count")),
        "x":        IdentifierBank(role="single_item"),
        "y":        IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":       IntRange(lo=20, hi=45),
        "lo":       IntRange(lo=2, hi=12),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {total} = 0
    {count} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {total} += {x}
        elif {x} == {lo}:
            {count} += 1
    {adjusted} = 0
    for {y} in {items}:
        if {y} > {count} and {y} < {hi}:
            {adjusted} += {y}
        elif {y} == {lo}:
            {adjusted} -= 1
    return {total} + {adjusted} - {count}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a {metric_word} from large sums and small {count_word}, {adjust_act} after.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Derive", "Build", "Resolve"),
            "metric_word": ("score", "balance", "figure", "result", "reading"),
            "count_word": ("counts", "tallies", "hits", "marks", "notes"),
            "adjust_act": ("corrected", "tuned", "rebalanced", "offset", "trimmed"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],             "hi": 30, "lo": 5},
        {"items": [35],           "hi": 30, "lo": 5},
        {"items": [3, 40, 5, 28], "hi": 30, "lo": 5},
    ),
)
