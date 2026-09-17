"""Tests for volume analysis.

This module verifies the documented contracts and edge cases of the volume analysis
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

from dp_activity.analysis.volume_analysis import VolumeAnalysis


def test_monthly_volume_includes_zero_months() -> None:
    """Verify that monthly volume includes zero months."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True],
            "Period": ["Before", "Before"],
            "YearMonth": pd.to_datetime(["2024-01-01", "2024-03-01"]),
        }
    )

    tables = implemented(VolumeAnalysis().run, permits)

    monthly = tables["monthly_volume"]
    assert monthly.loc[monthly["YearMonth"] == pd.Timestamp("2024-02-01"), "PermitCount"].iloc[0] == 0
