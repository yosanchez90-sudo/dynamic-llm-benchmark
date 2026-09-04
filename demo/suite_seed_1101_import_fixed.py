"""suite_seed_1101.py, repaired to use seed 4207's function name.

Every occurrence of `validate_input` is renamed to `categorise_value`
(seed 4207's name for the same template) -- not just the import line.
Python has no partial import, so every call site has to follow the import
or the suite raises NameError at collection time, which would be another
exec-gate failure rather than the baseline-gate failure this file exists
to show.

The assertions are otherwise untouched -- still written for seed 1101's
ceiling of 66. Seed 4207's ceiling is 36, so `categorise_value(66)` returns
36, not 66, and `categorise_value(100)` returns 36, not 66. Two of the four
assertions now assert a value the function does not return.

That is the point: renaming concedes the identifier for free, and the suite
still fails -- on the constants, not the name.
"""
from under_test import categorise_value


def test_zero():
    assert categorise_value(0) == 0


def test_below_ceiling():
    assert categorise_value(10) == 10


def test_at_ceiling():
    assert categorise_value(66) == 66


def test_well_above_ceiling():
    assert categorise_value(100) == 66
