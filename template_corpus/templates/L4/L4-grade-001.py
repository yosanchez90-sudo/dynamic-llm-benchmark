"""L4-grade-001 - Guarded three-way grading pass then a two-way scoring pass.

Tier L4: CC=8 (guard + for + if/elif + for + if/elif). Builds a list in pass one,
reduces it in pass two. Target 25-40 mutants (pre-cap).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, t1, t2, base):
    if not items:
        return base
    grades = []
    for x in items:
        if x > t2:
            grades.append(3)
        elif x > t1:
            grades.append(2)
        else:
            grades.append(1)
    score = 0
    for g in grades:
        if g == 3:
            score += g
        elif g == 1:
            score -= 1
    return score


template = Template(
    template_id="L4-grade-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(37, 43),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "grades":  IdentifierBank(role="accumulator"),
        "score":   IdentifierBank(role="accumulator", avoid_collision_with=("grades",)),
        "x":       IdentifierBank(role="single_item"),
        "g":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "t1":      IntRange(lo=5, hi=15),
        "t2":      IntRange(lo=20, hi=40),
        "base":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return {base}
    {grades} = []
    for {x} in {items}:
        if {x} > {t2}:
            {grades}.append(3)
        elif {x} > {t1}:
            {grades}.append(2)
        else:
            {grades}.append(1)
    {score} = 0
    for {g} in {grades}:
        if {g} == 3:
            {score} += {g}
        elif {g} == 1:
            {score} -= 1
    return {score}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} entries into three {grade_word}, {sum_act} the strong and {drop_act} the weak.",
        synonyms={
            "intro": ("Sort", "Grade", "Bin", "Rank", "Bucket", "Map"),
            "grade_word": ("bands", "tiers", "levels", "classes", "grades"),
            "sum_act": ("reward", "credit", "bank", "boost", "total"),
            "drop_act": ("penalise", "dock", "discount", "trim", "cut"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],             "t1": 10, "t2": 30, "base": 4},
        {"items": [25],           "t1": 10, "t2": 30, "base": 4},
        {"items": [5, 12, 35, 8], "t1": 10, "t2": 30, "base": 4},
    ),
)
