"""Unit tests for the grammar auto-fix rules in engine._grammar_fix.

Run with:  python3 _smoke/test_grammar.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_smoke"))

from engine import (  # noqa: E402
    _grammar_fix,
    _fix_articles,
    _fix_double_articles,
    _fix_double_plurals,
    _fix_double_punctuation,
    _fix_double_spaces,
    _fix_space_before_punctuation,
    _fix_sentence_initial_capital,
    _needs_an,
)


def run(name, fn, cases):
    fail = 0
    for inp, expected in cases:
        got = fn(inp)
        ok = got == expected
        if not ok:
            fail += 1
            print(f"  FAIL [{name}]: {inp!r}")
            print(f"        expected: {expected!r}")
            print(f"        got:      {got!r}")
    if fail == 0:
        print(f"  OK   [{name}] {len(cases)} cases")
    return fail


total_fail = 0

# ---- Rule 1: a/an article agreement ----
total_fail += run("Rule 1 a/an articles", _fix_articles, [
    ("Return a offset.",            "Return an offset."),
    ("Return a increment.",         "Return an increment."),
    ("Return a bias.",              "Return a bias."),
    ("Return an bias.",             "Return a bias."),
    ("A apple.",                    "An apple."),
    ("An banana.",                  "A banana."),
    ("A hour later.",               "An hour later."),
    ("An university lecture.",      "A university lecture."),
    ("Return a fixed scale.",       "Return a fixed scale."),
    ("Compute the sum of an array.", "Compute the sum of an array."),
])

# ---- Rule 2: double articles ----
total_fail += run("Rule 2 double articles", _fix_double_articles, [
    ("Return a a offset.",          "Return a offset."),
    ("Return an a offset.",         "Return a offset."),
    ("Return a an offset.",         "Return an offset."),
    ("Return an an offset.",        "Return an offset."),
    ("A a value.",                  "A value."),
    ("Return a single offset.",     "Return a single offset."),  # no change
])

# ---- Rule 3: double plurals ----
total_fail += run("Rule 3 double plurals", _fix_double_plurals, [
    ("Return the boxeses.",         "Return the boxes."),
    ("Return the classeses.",       "Return the classes."),
    ("Return the dasheses.",        "Return the dashes."),
    ("Return the matcheses.",       "Return the matches."),
    ("Return the buzzeses.",        "Return the buzzes."),
    ("Compute the boxes.",          "Compute the boxes."),     # no change
    ("Return the values.",          "Return the values."),     # no change
    # The ambiguous case (squareses) is NOT auto-fixed; the residual
    # scan reports it as a warning. Confirm the rule does not touch it.
    ("Return the squareses.",       "Return the squareses."),
])

# ---- Rule 4: double punctuation ----
total_fail += run("Rule 4 double punctuation", _fix_double_punctuation, [
    ("Return a value..",            "Return a value."),
    ("Return a value?.",            "Return a value?"),
    ("Return a value!?",            "Return a value!"),
    ("Return a value.",             "Return a value."),
    ("Return a value, and stop.",   "Return a value, and stop."),
])

# ---- Rule 5: double spaces ----
total_fail += run("Rule 5 double spaces", _fix_double_spaces, [
    ("Return  a value.",            "Return a value."),
    ("Return   a   value.",         "Return a value."),
    ("Return a value.",             "Return a value."),
])

# ---- Rule 6: space before punctuation ----
total_fail += run("Rule 6 space before punct", _fix_space_before_punctuation, [
    ("Return a value .",            "Return a value."),
    ("Return a value ,",            "Return a value,"),
    ("Return a value, and stop.",   "Return a value, and stop."),
])

# ---- Rule 7: sentence-initial capital ----
total_fail += run("Rule 7 sentence capital", _fix_sentence_initial_capital, [
    ("return a value.",             "Return a value."),
    ("Return a value.",             "Return a value."),
    ("  return a value.",           "  Return a value."),
    ("",                            ""),
])

# ---- Full pipeline (all rules in order) ----
total_fail += run("Full pipeline _grammar_fix", _grammar_fix, [
    # Combines rule 1 + rule 5
    ("Return  a offset.",                           "Return an offset."),
    # Combines rule 2 + rule 1
    ("Return a an offset.",                         "Return an offset."),
    # Combines rule 7 + rule 1
    ("return a offset.",                            "Return an offset."),
    # Combines rule 6 + rule 4
    ("Return a value ..",                           "Return a value."),
    # Combines rule 5 + rule 6
    ("Return  a value ,",                           "Return a value,"),
    # No-op (clean input)
    ("Return an offset.",                           "Return an offset."),
    # Combination of articles + double spaces
    ("Compute  a apple and an banana.",             "Compute an apple and a banana."),
])

print()
if total_fail == 0:
    print(f"ALL TESTS PASS")
    sys.exit(0)
else:
    print(f"FAILURES: {total_fail}")
    sys.exit(1)
