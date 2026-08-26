"""Holm-Bonferroni step-down correction for multiple comparisons.

PROJECT_BRIEF.md Sec 3.1: "Corrections: Holm-Bonferroni within each RQ
family." Implemented here as a single shared utility so every RQ family
that runs more than one significance test within itself applies the same
procedure, instead of each script re-deriving it, or, as was actually
the case until 2026-08-04, not applying it anywhere at all
(analysis/HYPOTHESIS_COVERAGE_AUDIT.md found zero uses of any
multiple-testing correction anywhere in this project's history).
"""
from __future__ import annotations

import numpy as np


def holm_bonferroni(p_values: list[float]) -> list[float]:
    """Holm's step-down adjustment. Returns adjusted p-values in the same
    order as the input (not sorted). Each is directly comparable to the
    original alpha (e.g. 0.05), same convention as
    statsmodels.stats.multitest.multipletests(method="holm") (not used
    directly since statsmodels is not a project dependency, see
    analysis/H4_DESIGN_MEMO.md for why adding it is a live decision, not
    assumed here).

    Procedure: sort ascending, multiply the i-th smallest (0-indexed i, m
    total) by (m - i), enforce monotonicity via a running maximum (Holm's
    adjusted p-values must be non-decreasing in sorted order), clip to
    1.0. NaN p-values (e.g. a pair that couldn't be computed, n<2) are
    passed through unadjusted and excluded from the correction entirely --
    they were never a computed null-hypothesis test to correct.
    """
    p_arr = np.asarray(p_values, dtype=float)
    valid_mask = ~np.isnan(p_arr)
    m = int(valid_mask.sum())
    adjusted = p_arr.copy()
    if m == 0:
        return adjusted.tolist()

    valid_idx = np.where(valid_mask)[0]
    valid_p = p_arr[valid_idx]
    order = np.argsort(valid_p)
    sorted_p = valid_p[order]

    holm_p = np.empty(m, dtype=float)
    running_max = 0.0
    for i in range(m):
        candidate = (m - i) * sorted_p[i]
        running_max = max(running_max, candidate)
        holm_p[i] = min(running_max, 1.0)

    unsorted_holm = np.empty(m, dtype=float)
    unsorted_holm[order] = holm_p
    adjusted[valid_idx] = unsorted_holm
    return adjusted.tolist()
