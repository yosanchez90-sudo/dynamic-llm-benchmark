"""L4-bucketize-001 - Guarded three-band tagging pass then a reduce pass.

Tier L4: CC=8 (guard + for + if/elif/elif + for + if). List built then reduced.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, mid, lo):
    if not items:
        return 0
    tags = []
    for x in items:
        if x > hi:
            tags.append(3)
        elif x > mid:
            tags.append(2)
        elif x > lo:
            tags.append(1)
    score = 0
    for tg in tags:
        if tg == 3:
            score += tg
    return score


template = Template(
    template_id="L4-bucketize-001",
    declared_tier="L4",
    declared_ast_depth=4,
    expected_mutant_count=(34, 40),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "tags":    IdentifierBank(role="accumulator"),
        "score":   IdentifierBank(role="accumulator", avoid_collision_with=("tags",)),
        "x":       IdentifierBank(role="single_item"),
        "tg":      IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":      IntRange(lo=30, hi=55),
        "mid":     IntRange(lo=15, hi=25),
        "lo":      IntRange(lo=2, hi=10),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {tags} = []
    for {x} in {items}:
        if {x} > {hi}:
            {tags}.append(3)
        elif {x} > {mid}:
            {tags}.append(2)
        elif {x} > {lo}:
            {tags}.append(1)
    {score} = 0
    for {tg} in {tags}:
        if {tg} == 3:
            {score} += {tg}
    return {score}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} entries into three {band_word}, then {sum_act} the {top_word} band.",
        synonyms={
            "intro": ("Bin", "Bucket", "Classify", "Rank", "Sort", "Split"),
            "band_word": ("tiers", "levels", "brackets", "grades", "bins"),
            "sum_act": ("total", "reward", "bank", "credit", "score"),
            "top_word": ("highest", "upper", "top", "leading", "premier"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],              "hi": 40, "mid": 20, "lo": 5},
        {"items": [45],            "hi": 40, "mid": 20, "lo": 5},
        {"items": [3, 22, 50, 12], "hi": 40, "mid": 20, "lo": 5},
    ),
)
