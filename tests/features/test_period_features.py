"""Tests for period features.

This module verifies the documented contracts and edge cases of the period features
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

from datetime import date

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from dp_activity.config import StudyPeriod
from dp_activity.features.period_features import add_period_features


def test_period_boundaries_are_inclusive() -> None:
    """Verify that period boundaries are inclusive."""
    permits = pd.DataFrame(
        {"applied_date": pd.to_datetime(["2024-08-05", "2024-08-06", "2026-08-04"])}
    )
    periods = [
        StudyPeriod("Before", date(2022, 8, 6), date(2024, 8, 5)),
        StudyPeriod("During", date(2024, 8, 6), date(2026, 8, 3)),
        StudyPeriod("Early Post-Repeal", date(2026, 8, 4), None),
    ]

    result = add_period_features(
        permits,
        date_column="applied_date",
        periods=periods,
    )

    assert result["Period"].tolist() == ["Before", "During", "Early Post-Repeal"]


def _periods() -> list[StudyPeriod]:
    """Provide the configured policy cutoffs for boundary tests.

    Returns:
        Inclusive Before, During, and open-ended post-repeal periods.
    """
    return [
        StudyPeriod("Before", date(2022, 8, 6), date(2024, 8, 5)),
        StudyPeriod("During", date(2024, 8, 6), date(2026, 8, 3)),
        StudyPeriod("Early Post-Repeal", date(2026, 8, 4), None),
    ]


def test_calendar_boundaries_and_input_preservation() -> None:
    """Include entire final days and preserve repeated index labels and evidence."""
    table = pd.DataFrame({"when": [
        "2022-08-05", "2022-08-06", "2024-08-05T23:59:59-07:00",
        "2024-08-06", "2026-08-03T23:59:59", "2026-08-04", "2030-01-01",
    ]}, index=[1] * 7)
    before = table.copy(deep=True)
    result = add_period_features(table, date_column="when", periods=_periods())
    assert result["Period"].tolist() == [
        "Outside Study Window", "Before", "Before", "During", "During",
        "Early Post-Repeal", "Early Post-Repeal",
    ]
    assert result["PeriodSortKey"].tolist() == [0, 1, 1, 2, 2, 3, 3]
    assert result["Period"].cat.ordered
    assert result["CrossesPeriodBoundary"].isna().all()
    assert_frame_equal(table, before)
    assert result.index.equals(table.index)


def test_missing_invalid_and_cleaner_flags_remain_distinct() -> None:
    """Avoid assigning unknown evidence to the outside-study category."""
    table = pd.DataFrame({"when": [None, " ", "bad", 20240806, pd.NaT],
                          "when_invalid": [False, False, False, False, True]})
    result = add_period_features(table, date_column="when", periods=_periods())
    assert result["Period"].isna().all()
    assert result["PeriodSortKey"].isna().all()
    assert result["PeriodDateMissing"].tolist() == [True, True, False, False, False]
    assert result["PeriodDateInvalid"].tolist() == [False, False, True, True, True]


def test_boundary_crossing_is_nullable_and_does_not_reassign_period() -> None:
    """Audit cross-period decisions while preserving application-based assignment."""
    table = pd.DataFrame({
        "when": ["2024-08-05", "2026-08-03", "2024-08-06", "2024-08-06", None],
        "decision": ["2024-08-06", "2026-08-04", "2024-08-06", "2024-08-05", "2024-08-07"],
    })
    result = add_period_features(table, date_column="when", periods=_periods(), decision_date_column="decision")
    assert result["CrossesPeriodBoundary"].iloc[:3].tolist() == [True, True, False]
    assert result["CrossesPeriodBoundary"].iloc[3:].isna().all()
    assert result["Period"].iloc[0] == "Before"
    assert result["DecisionPeriod"].iloc[0] == "During"


def test_gaps_and_empty_tables() -> None:
    """Treat valid gap dates as outside while keeping empty output schemas stable."""
    periods = [StudyPeriod("A", date(2024, 1, 1), date(2024, 1, 2)),
               StudyPeriod("B", date(2024, 1, 4), date(2024, 1, 5))]
    table = pd.DataFrame({"when": ["2024-01-03", "2024-01-06"]})
    result = add_period_features(table, date_column="when", periods=periods)
    assert result["Period"].tolist() == ["Outside Study Window"] * 2
    empty = add_period_features(table.iloc[:0], date_column="when", periods=periods)
    assert empty.empty
    assert str(empty["PeriodSortKey"].dtype) == "Int64"
    assert str(empty["CrossesPeriodBoundary"].dtype) == "boolean"


@pytest.mark.parametrize("periods", [
    [], list(reversed(_periods())), [_periods()[0], _periods()[0]],
    [StudyPeriod("A", date(2024, 1, 2), date(2024, 1, 1))],
    [StudyPeriod("Outside Study Window", date(2024, 1, 1), None)],
    [StudyPeriod("A", date(2024, 1, 1), None), StudyPeriod("B", date(2024, 2, 1), None)],
])
def test_invalid_period_definitions_raise(periods: list[StudyPeriod]) -> None:
    """Reject ambiguous definitions before classifying records."""
    with pytest.raises(ValueError):
        add_period_features(pd.DataFrame({"when": []}), date_column="when", periods=periods)


def test_invalid_inputs_and_collisions_raise() -> None:
    """Reject unsupported inputs and avoid overwriting existing analytical fields."""
    with pytest.raises(TypeError):
        add_period_features([], date_column="when", periods=_periods())
    with pytest.raises(ValueError):
        add_period_features(pd.DataFrame(), date_column="when", periods=_periods())
    table = pd.DataFrame({"when": ["2024-01-01"], "Period": ["Existing"]})
    with pytest.raises(ValueError):
        add_period_features(table, date_column="when", periods=_periods())
    table = table.drop(columns="Period")
    table["when_invalid"] = "False"
    with pytest.raises(ValueError):
        add_period_features(table, date_column="when", periods=_periods())
