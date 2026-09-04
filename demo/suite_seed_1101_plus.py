"""Hand-written test suite for L2-clamp-001, seed 1101.

The function under test:

    def validate_input(elem):
        if elem > 66:
            return 66
        return elem

Which mutants this kills, which it leaves alive, and why, is recorded in
demo/README.md -- verified by executing every mutant, not by inspection.
"""
from under_test import validate_input


def test_zero():
    assert validate_input(0) == 0


def test_below_ceiling():
    assert validate_input(10) == 10


def test_at_ceiling():
    assert validate_input(66) == 66


def test_well_above_ceiling():
    assert validate_input(100) == 66


def test_first_value_past_the_ceiling():
    assert validate_input(67) == 66
