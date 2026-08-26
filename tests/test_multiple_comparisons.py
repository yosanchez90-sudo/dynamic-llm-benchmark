"""Unit tests for src/Analysis/multiple_comparisons.py's Holm-Bonferroni
step-down correction."""
from __future__ import annotations

import math

import pytest

from src.Analysis.multiple_comparisons import holm_bonferroni


def test_known_example_matches_hand_computation():
    # p = [0.01, 0.02, 0.03, 0.04, 0.05], m=5.
    # sorted multipliers (m-i): 5,4,3,2,1 -> 0.05,0.08,0.09,0.08,0.05
    # running max (monotonic enforcement): 0.05, 0.08, 0.09, 0.09, 0.09
    p = [0.01, 0.02, 0.03, 0.04, 0.05]
    adjusted = holm_bonferroni(p)
    assert adjusted == pytest.approx([0.05, 0.08, 0.09, 0.09, 0.09])


def test_order_preserved_not_sorted():
    p = [0.05, 0.01, 0.03]
    adjusted = holm_bonferroni(p)
    # index 1 (0.01) is the smallest -> multiplier 3 -> 0.03
    # index 2 (0.03) is the middle -> multiplier 2 -> 0.06, running max stays 0.06
    # index 0 (0.05) is the largest -> multiplier 1 -> 0.05, running max stays 0.06
    assert adjusted == pytest.approx([0.06, 0.03, 0.06])


def test_single_pvalue_unchanged():
    # A family of one is a no-op. Multiplier is (1-0)=1.
    assert holm_bonferroni([0.03]) == pytest.approx([0.03])


def test_clips_to_one():
    p = [0.5, 0.6, 0.7]
    adjusted = holm_bonferroni(p)
    assert all(a <= 1.0 for a in adjusted)


def test_nan_passed_through_and_excluded_from_correction():
    p = [0.01, float("nan"), 0.02]
    adjusted = holm_bonferroni(p)
    assert math.isnan(adjusted[1])
    # only the two real p-values (0.01, 0.02) form the family, m=2
    assert adjusted[0] == pytest.approx(0.02)  # (2-0)*0.01
    assert adjusted[2] == pytest.approx(0.02)  # (2-1)*0.02, running max unchanged


def test_all_nan_returns_all_nan():
    p = [float("nan"), float("nan")]
    adjusted = holm_bonferroni(p)
    assert all(math.isnan(a) for a in adjusted)


def test_empty_list():
    assert holm_bonferroni([]) == []
