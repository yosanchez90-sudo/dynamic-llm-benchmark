"""L4-orchestrate-001 - Guarded nested pair pass plus a conjunction reduce pass.

Tier L4: CC=10 (guard + for/for + if/elif + for + if(and)/elif). LOR via 'and'/'not'.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo):
    if not items:
        return 0
    win = 0
    for x in items:
        for y in items:
            if x + y > hi:
                win += x
            elif x == y:
                win += 1
    flow = 0
    for z in items:
        if z > lo and z < hi:
            flow += z
        elif z == hi:
            flow -= 1
    return win + flow


template = Template(
    template_id="L4-orchestrate-001",
    declared_tier="L4",
    declared_ast_depth=4,
    expected_mutant_count=(35, 41),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "win":     IdentifierBank(role="accumulator"),
        "flow":    IdentifierBank(role="accumulator", avoid_collision_with=("win",)),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "z":       IdentifierBank(role="single_item", avoid_collision_with=("x", "y")),
        "hi":      IntRange(lo=25, hi=50),
        "lo":      IntRange(lo=2, hi=12),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {win} = 0
    for {x} in {items}:
        for {y} in {items}:
            if {x} + {y} > {hi}:
                {win} += {x}
            elif {x} == {y}:
                {win} += 1
    {flow} = 0
    for {z} in {items}:
        if {z} > {lo} and {z} < {hi}:
            {flow} += {z}
        elif {z} == {hi}:
            {flow} -= 1
    return {win} + {flow}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} a pair-driven {metric_word}, then {merge_act} a mid-band flow.",
        synonyms={
            "intro": ("Orchestrate", "Compute", "Drive", "Coordinate", "Build", "Resolve"),
            "metric_word": ("score", "tally", "figure", "result", "reading"),
            "merge_act": ("layers on", "folds in", "merges", "blends", "adds"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],             "hi": 30, "lo": 5},
        {"items": [18],           "hi": 30, "lo": 5},
        {"items": [4, 28, 18, 5], "hi": 30, "lo": 5},
    ),
)
