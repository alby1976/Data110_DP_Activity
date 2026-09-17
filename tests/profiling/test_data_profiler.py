"""Tests for data profiler.

This module verifies the documented contracts and edge cases of the data profiler
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

import pandas as pd

from conftest import implemented

from dp_activity.profiling.data_profiler import DataProfiler


def test_profile_includes_shape_missingness_and_value_counts() -> None:
    """Verify that profile includes shape missingness and value counts."""
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP2"],
            "category": ["Residential", None],
        }
    )

    profile = implemented(DataProfiler().profile, permits, ["category"])

    assert {"summary", "missingness"}.issubset(profile)
    assert profile["summary"].iloc[0]["row_count"] == 2
    assert "category" in profile
