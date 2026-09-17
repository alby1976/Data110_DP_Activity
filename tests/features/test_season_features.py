"""Tests for season features.

This module verifies the documented contracts and edge cases of the season features
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

from dp_activity.features.season_features import add_season_features


def test_cross_year_winter_uses_december_start() -> None:
    """Verify that cross year winter uses december start."""
    permits = pd.DataFrame(
        {"applied_date": pd.to_datetime(["2024-12-15", "2025-01-10", "2025-02-20"])}
    )
    months = {
        "Fall": [9, 10, 11],
        "Winter": [12, 1, 2],
        "Spring": [3, 4, 5],
        "Summer": [6, 7, 8],
    }

    result = implemented(
        add_season_features,
        permits,
        date_column="applied_date",
        season_months=months,
        analysis_windows=[],
    )

    assert result["Season"].tolist() == ["Winter", "Winter", "Winter"]
    assert result["SeasonStartDate"].dt.date.nunique() == 1
    assert result.loc[0, "SeasonLabel"] == "Winter 2024–25"
