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

from conftest import implemented

from dp_activity.features.processing_features import add_processing_features


def test_processing_days_flags_valid_negative_and_pending_rows() -> None:
    """Verify that processing days flags valid negative and pending rows."""
    permits = pd.DataFrame(
        {
            "applied_date": pd.to_datetime(["2024-01-01", "2024-01-10", "2024-01-01"]),
            "decision_date": pd.to_datetime(["2024-01-11", "2024-01-09", None]),
        }
    )

    result = implemented(
        add_processing_features,
        permits,
        applied_date_column="applied_date",
        decision_date_column="decision_date",
    )

    assert result["ProcessingDays"].iloc[0] == 10
    assert result["HasValidProcessingDays"].tolist() == [True, False, False]
    assert result["IsPending"].tolist() == [False, False, True]
