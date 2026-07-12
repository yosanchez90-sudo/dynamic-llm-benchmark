"""L4-merge-001 - Accumulate in pass one, classify with a conjunction in pass two.

Tier L4: CC=8 (for + if/elif + for + if(and)/elif). LOR via 'and'.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo, mid):
    total = 0
    for x in items:
        if x > hi:
            total += x
        elif x < lo:
            total += 1
    tag = 0
    for y in items:
        if y > mid and y < hi:
            tag += y
        elif y == lo:
            tag -= 1
    return total + tag


template = Template(
    template_id="L4-merge-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(35, 41),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "total":   IdentifierBank(role="accumulator"),
        "tag":     IdentifierBank(role="accumulator", avoid_collision_with=("total",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":      IntRange(lo=25, hi=50),
        "lo":      IntRange(lo=2, hi=10),
        "mid":     IntRange(lo=12, hi=22),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {total} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {total} += {x}
        elif {x} < {lo}:
            {total} += 1
    {tag} = 0
    for {y} in {items}:
        if {y} > {mid} and {y} < {hi}:
            {tag} += {y}
        elif {y} == {lo}:
            {tag} -= 1
    return {total} + {tag}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} a {sum_word} of the extremes, then {merge_act} a {mid_word} tag.",
        synonyms={
            "intro": ("Build", "Compute", "Produce", "Derive", "Form", "Assemble"),
            "sum_word": ("total", "aggregate", "sum", "tally", "figure"),
            "merge_act": ("folds in", "merges", "layers on", "blends", "adds"),
            "mid_word": ("mid-band", "middle", "central", "interior", "in-range"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],              "hi": 30, "lo": 5, "mid": 15},
        {"items": [18],            "hi": 30, "lo": 5, "mid": 15},
        {"items": [5, 35, 18, 2],  "hi": 30, "lo": 5, "mid": 15},
    ),
)
