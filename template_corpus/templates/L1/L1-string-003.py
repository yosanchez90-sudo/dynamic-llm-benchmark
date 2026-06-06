"""L1-string-003 - Centre a string in a padded field and append a suffix.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 5.
Pattern: s.center(c, pad) + suffix  -> AOR=1, CR=3, RSM=1 (total 5).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank, StringChoice,
)


template = Template(
    template_id="L1-string-003",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(2, 8),

    parameter_spec={
        "fn_name":  IdentifierBank(role="function_L1"),
        "text":     IdentifierBank(role="single_item"),
        "width":    IntRange(lo=8, hi=24),
        "pad_char": StringChoice(values=("-", "*", "=", ".", " ")),
        "suffix":   StringChoice(values=("!", "?", "...", ":")),
    },

    body_skeleton="""
def {fn_name}({text}):
    \"\"\"{docstring}\"\"\"
    return {text}.center({width}, "{pad_char}") + "{suffix}"
""",

    oracle=lambda text, width, pad_char, suffix: text.center(width, pad_char) + suffix,

    docstring_template=DocstringTemplate(
        template="{intro} the string {centre_word} in a fixed-width field with a suffix appended.",
        synonyms={
            "intro": ("Return", "Format", "Compose", "Build", "Construct", "Produce"),
            "centre_word": ("centred", "centre-padded", "balanced", "horizontally aligned", "evenly padded"),
        },
    ),

    smoke_test_inputs=(
        {"text": "hi",     "width": 10, "pad_char": "-", "suffix": "!"},
        {"text": "title",  "width": 12, "pad_char": "*", "suffix": "?"},
        {"text": "",       "width": 8,  "pad_char": " ", "suffix": ":"},
    ),
)
