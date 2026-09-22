"""Tests for processing features.

This module verifies the documented contracts and edge cases of the processing features
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

from dp_activity.features.processing_features import add_processing_features


def test_processing_days_flags_valid_negative_and_pending_rows() -> None:
    """Verify that processing days flags valid negative and pending rows."""
    permits = pd.DataFrame(
        {
            "applied_date": pd.to_datetime(["2024-01-01", "2024-01-10", "2024-01-01"]),
            "decision_date": pd.to_datetime(["2024-01-11", "2024-01-09", None]),
        }
    )

    result = add_processing_features(
        permits,
        applied_date_column="applied_date",
        decision_date_column="decision_date",
    )

    assert result["ProcessingDays"].iloc[0] == 10
    assert result["HasValidProcessingDays"].tolist() == [True, False, False]
    assert result["IsPending"].tolist() == [False, False, True]
    assert result["ProcessingDays"].iloc[1] == -1
    assert result["HasNegativeProcessingDays"].tolist() == [False, True, False]
    assert result["IsRightCensored"].tolist() == [False, False, True]
    assert result["FollowUpDays"].iloc[1:].isna().all()


def test_calendar_days_threshold_and_input_preservation() -> None:
    """Count calendar days rather than full elapsed days and preserve row indexes."""
    table = pd.DataFrame({
        "start": ["2024-02-28T23:59:59-07:00", "2024-02-29T12:00:00", "2024-02-29"],
        "end": ["2024-03-01T00:00:00+00:00", "2024-02-29T01:00:00", "2024-03-01"],
    }, index=[2, 2, 1])
    before = table.copy(deep=True)
    result = add_processing_features(table, applied_date_column="start", decision_date_column="end", minimum_days=1)
    assert result["ProcessingDays"].tolist() == [2, 0, 1]
    assert result["HasValidProcessingDays"].tolist() == [True, False, True]
    assert result["FollowUpDays"].tolist() == [2, 0, 1]
    assert_frame_equal(table, before)
    assert result.index.equals(table.index)


def test_invalid_decisions_are_not_pending() -> None:
    """Retain malformed-date evidence when the cleaner replaced values with NaT."""
    table = pd.DataFrame({
        "start": ["2024-01-01"] * 4 + [None, 20240101],
        "end": ["bad", None, " ", None, None, None],
        "end_invalid": [False, True, False, False, False, False],
    })
    result = add_processing_features(table, applied_date_column="start", decision_date_column="end")
    assert result["IsPending"].tolist() == [False, False, True, True, False, False]
    assert result["ProcessingDateInvalid"].tolist() == [True, True, False, False, False, True]
    assert result["ProcessingDays"].isna().all()


def test_observation_end_censors_later_decisions_and_caps_follow_up() -> None:
    """Respect the snapshot horizon without discarding known source durations."""
    table = pd.DataFrame({
        "start": ["2024-01-01"] * 4 + ["2024-01-11"],
        "end": ["2024-01-10", "2024-01-11", None, "bad", None],
    })
    result = add_processing_features(table, applied_date_column="start", decision_date_column="end",
                                     observation_end=date(2024, 1, 10))
    assert result["HasValidProcessingDays"].tolist() == [True, False, False, False, False]
    assert result["IsRightCensored"].tolist() == [False, True, True, False, False]
    assert result["IsPending"].tolist() == [False, False, True, False, False]
    assert result["IsAfterObservationEnd"].tolist() == [False, True, False, False, True]
    assert result["FollowUpDays"].iloc[:3].tolist() == [9, 9, 9]
    assert result["FollowUpDays"].iloc[3:].isna().all()
    assert result["ProcessingDays"].iloc[1] == 10


def test_empty_table_has_stable_types() -> None:
    """Keep feature schemas usable when a selected period contains no records."""
    result = add_processing_features(pd.DataFrame(columns=["start", "end"]),
                                     applied_date_column="start", decision_date_column="end")
    assert result.empty
    assert str(result["ProcessingDays"].dtype) == "Int64"
    assert str(result["FollowUpDays"].dtype) == "Int64"
    assert str(result["IsPending"].dtype) == "bool"


@pytest.mark.parametrize("minimum,exception", [(-1, ValueError), (True, TypeError), (1.5, TypeError)])
def test_invalid_threshold_raises(minimum: object, exception: type[Exception]) -> None:
    """Reject ambiguous or negative configured duration thresholds."""
    with pytest.raises(exception):
        add_processing_features(pd.DataFrame(columns=["start", "end"]),
                                applied_date_column="start", decision_date_column="end", minimum_days=minimum)


def test_invalid_inputs_flags_and_collisions_raise() -> None:
    """Reject unsupported inputs and preserve existing derived evidence."""
    table = pd.DataFrame({"start": ["2024-01-01"], "end": [None]})
    with pytest.raises(TypeError):
        add_processing_features([], applied_date_column="start", decision_date_column="end")
    with pytest.raises(ValueError):
        add_processing_features(table, applied_date_column="missing", decision_date_column="end")
    with pytest.raises(ValueError):
        add_processing_features(table, applied_date_column="start", decision_date_column="start")
    with pytest.raises(ValueError):
        add_processing_features(table.assign(ProcessingDays=0), applied_date_column="start", decision_date_column="end")
    with pytest.raises(ValueError):
        add_processing_features(table.assign(end_invalid="False"), applied_date_column="start", decision_date_column="end")
    with pytest.raises(TypeError):
        add_processing_features(table, applied_date_column="start", decision_date_column="end", observation_end="2024-01-10")
