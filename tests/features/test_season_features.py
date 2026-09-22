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
import pytest
from datetime import date
from pandas.testing import assert_frame_equal

from dp_activity.config import StudyPeriod

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

    result = add_season_features(
        permits,
        date_column="applied_date",
        season_months=months,
        analysis_windows=[],
    )

    assert result["Season"].tolist() == ["Winter", "Winter", "Winter"]
    assert result["SeasonStartDate"].dt.date.nunique() == 1
    assert result.loc[0, "SeasonLabel"] == "Winter 2024–25"


MONTHS = {"Fall": [9, 10, 11], "Winter": [12, 1, 2], "Spring": [3, 4, 5], "Summer": [6, 7, 8]}


def test_leap_winter_calendar_dates_and_nonmutation() -> None:
    """Preserve rows and source dates while handling leap days and offsets."""
    table = pd.DataFrame({"when": ["2024-02-29T23:59:59-07:00", "2024-03-01"]}, index=[8, 8])
    before = table.copy(deep=True)
    result = add_season_features(table, date_column="when", season_months=MONTHS,
                                 analysis_windows=[StudyPeriod("All", date(2023, 1, 1), date(2025, 1, 1))])
    assert result["Season"].tolist() == ["Winter", "Spring"]
    assert result["SeasonEndDate"].iloc[0] == pd.Timestamp("2024-02-29")
    assert result["SeasonSortKey"].tolist() == [202312, 202403]
    assert result["IsCompleteSeason"].tolist() == [True, True]
    assert_frame_equal(table, before)
    assert result.index.equals(table.index)


def test_policy_boundary_splits_summer() -> None:
    """Do not combine adjacent policy windows to claim a complete summer."""
    windows = [StudyPeriod("Before", date(2022, 8, 6), date(2024, 8, 5)),
               StudyPeriod("During", date(2024, 8, 6), date(2026, 8, 3))]
    result = add_season_features(pd.DataFrame({"when": ["2024-08-05", "2024-08-06", "2024-09-01"]}),
                                 date_column="when", season_months=MONTHS, analysis_windows=windows)
    assert result["IsCompleteSeason"].tolist() == [False, False, True]
    assert result["IsPartialSeason"].tolist() == [True, True, False]


def test_open_window_requires_explicit_observation_end() -> None:
    """Avoid using the clock or latest record as evidence of complete exposure."""
    table = pd.DataFrame({"when": ["2026-08-04", "2026-09-01", "2026-12-01"]})
    windows = [StudyPeriod("Post", date(2026, 8, 4), None)]
    result = add_season_features(table, date_column="when", season_months=MONTHS, analysis_windows=windows)
    assert not result["IsCompleteSeason"].iloc[0]
    assert result["IsCompleteSeason"].iloc[1:].isna().all()
    bounded = add_season_features(table, date_column="when", season_months=MONTHS,
                                  analysis_windows=windows, observation_end=date(2026, 11, 30))
    assert bounded["IsCompleteSeason"].iloc[:2].tolist() == [False, True]
    assert pd.isna(bounded["IsCompleteSeason"].iloc[2])


def test_missing_invalid_and_outside_dates() -> None:
    """Keep unusable dates null and distinguish season assignment from exposure."""
    table = pd.DataFrame({"when": [None, "bad", 20240101, "2024-01-01", "2020-01-01"],
                          "when_invalid": [False, False, False, True, False]})
    result = add_season_features(table, date_column="when", season_months=MONTHS,
                                 analysis_windows=[StudyPeriod("Study", date(2024, 1, 1), None)])
    assert result["Season"].iloc[:4].isna().all()
    assert result["Season"].iloc[4] == "Winter"
    assert result["IsCompleteSeason"].isna().all()


def test_empty_table_has_stable_dtypes() -> None:
    """Expose predictable output columns even when no records are available."""
    result = add_season_features(pd.DataFrame({"when": []}), date_column="when",
                                 season_months=MONTHS, analysis_windows=[])
    assert result.empty
    assert str(result["SeasonSortKey"].dtype) == "Int64"
    assert str(result["IsCompleteSeason"].dtype) == "boolean"


@pytest.mark.parametrize("months", [
    {}, {**MONTHS, "Winter": [1, 2, 12]}, {**MONTHS, "Winter": [12, 1, True]},
    {**MONTHS, "Winter": [12, 1]}, {**MONTHS, "Extra": [1, 2, 3]},
])
def test_invalid_season_definitions_raise(months: dict) -> None:
    """Reject ambiguous or incomplete seasonal maps before processing data."""
    with pytest.raises(ValueError):
        add_season_features(pd.DataFrame({"when": []}), date_column="when",
                            season_months=months, analysis_windows=[])


def test_invalid_windows_collisions_and_flags_raise() -> None:
    """Fail explicitly when configuration or input evidence is ambiguous."""
    table = pd.DataFrame({"when": ["2024-01-01"]})
    windows = [StudyPeriod("A", date(2024, 1, 1), None)] * 2
    with pytest.raises(ValueError):
        add_season_features(table, date_column="when", season_months=MONTHS, analysis_windows=windows)
    with pytest.raises(ValueError):
        add_season_features(table.assign(Season="old"), date_column="when", season_months=MONTHS, analysis_windows=[])
    with pytest.raises(ValueError):
        add_season_features(table.assign(when_invalid="False"), date_column="when", season_months=MONTHS, analysis_windows=[])
    with pytest.raises(TypeError):
        add_season_features([], date_column="when", season_months=MONTHS, analysis_windows=[])
