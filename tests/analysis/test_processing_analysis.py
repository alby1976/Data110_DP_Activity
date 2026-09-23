"""Tests for processing analysis.

This module verifies the documented contracts and edge cases of the processing analysis
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

from dp_activity.analysis.processing_analysis import ProcessingAnalysis
from dp_activity.features.processing_features import add_processing_features


def test_invalid_processing_rows_are_excluded_but_counted() -> None:
    """Verify that invalid processing rows are excluded but counted."""
    permits = pd.DataFrame(
        {
            "Period": ["Before", "Before", "Before"],
            "IncludeResidential": [True, True, True],
            "HasValidProcessingDays": [True, False, False],
            "ProcessingDays": [10, -1, None],
            "IsPending": [False, False, True],
            "IsRightCensored": [False, False, True],
        }
    )

    tables = ProcessingAnalysis().run(permits)

    summary = tables["processing_summary"].iloc[0]
    assert summary["ValidCount"] == 1
    assert summary["MedianProcessingDays"] == 10
    assert summary["PendingCount"] == 1
    assert summary["InvalidCount"] == 2
    assert summary["RightCensoredCount"] == 1


def _permits() -> pd.DataFrame:
    """Provide residential and excluded records with known duration statistics.

    Returns:
        Feature-enriched sample whose valid residential durations are 0, 10, 20, 30.
    """
    return pd.DataFrame({
        "Period": ["Before"] * 7,
        "IncludeResidential": [True] * 6 + [False],
        "HasValidProcessingDays": [True] * 4 + [False, False, True],
        "ProcessingDays": pd.array([0, 10, 20, 30, -1, None, 1000], dtype="Int64"),
        "IsPending": [False] * 5 + [True, False],
        "IsRightCensored": [False] * 5 + [True, False],
        "ResidentialType": ["House", "House", "Review", None, "House", " ", "Other"],
        "community": ["A", "A", None, " ", "B", "B", "Excluded"],
    })


def test_statistics_denominators_and_input_preservation() -> None:
    """Verify exact quartiles and exclusion of nonresidential duration outliers."""
    permits = _permits()
    original = permits.copy(deep=True)
    result = ProcessingAnalysis(period_order=["Before", "During"]).run(permits)
    before = result["processing_summary"].iloc[0]
    assert before["TotalCount"] == 6
    assert before["ValidCount"] == 4
    assert before["InvalidCount"] == 2
    assert before["ValidShare"] == pytest.approx(4 / 6)
    assert before["MeanProcessingDays"] == 15
    assert before["MedianProcessingDays"] == 15
    assert before["Q1ProcessingDays"] == 7.5
    assert before["Q3ProcessingDays"] == 22.5
    assert before["IQRProcessingDays"] == 15
    assert pd.isna(before["MissingDateCount"])
    totals = result["processing_period_totals"].iloc[0]
    assert totals["AllPermitCount"] == 7
    assert totals["PeriodResidentialCount"] == 6
    assert totals["ExcludedCount"] == 1
    empty = result["processing_summary"].iloc[1]
    assert empty["ValidCount"] == 0
    assert pd.isna(empty["MedianProcessingDays"])
    assert pd.isna(empty["ValidShare"])
    pd.testing.assert_frame_equal(permits, original)


def test_group_breakdowns_reconcile_and_keep_missing_labels() -> None:
    """Keep Unknown and Review types and missing communities in subgroup counts."""
    permits = _permits()
    permits.index = [2] * len(permits)
    result = ProcessingAnalysis(community_column="community").run(permits)
    types = result["processing_type_summary"].set_index("ResidentialType")
    assert types["TotalCount"].sum() == 6
    assert types["ValidCount"].sum() == 4
    assert types.loc["Unknown", "TotalCount"] == 2
    assert types.loc["Review", "MedianProcessingDays"] == 20
    community = result["processing_community_summary"]
    assert community["TotalCount"].sum() == 6
    assert community.loc[community["Community"].isna(), "TotalCount"].item() == 2
    assert "Excluded" not in community["Community"].dropna().tolist()


def test_real_feature_flags_respect_horizon_and_minimum_days() -> None:
    """Retain censoring, date errors, and short intervals as overlapping audits."""
    from datetime import date

    permits = pd.DataFrame({
        "Period": ["During"] * 7, "IncludeResidential": [True] * 7,
        "applied": ["2024-01-01"] * 6 + ["2024-02-01"],
        "decision": ["2024-01-11", "2024-01-02", None, "bad", "2023-12-31", "2024-02-01", None],
    })
    features = add_processing_features(permits, applied_date_column="applied",
                                       decision_date_column="decision", minimum_days=5,
                                       observation_end=date(2024, 1, 31))
    row = ProcessingAnalysis().run(features)["processing_summary"].iloc[0]
    assert row["ValidCount"] == 1
    assert row["MedianProcessingDays"] == 10
    assert row["InvalidCount"] == 6
    assert row["PendingCount"] == 1
    assert row["RightCensoredCount"] == 2
    assert row["NegativeCount"] == 1
    assert row["MissingDateCount"] == 2
    assert row["InvalidDateCount"] == 1
    assert row["AfterObservationEndCount"] == 2


@pytest.mark.parametrize("mode", ["empty", "excluded", "invalid"])
def test_no_valid_population(mode: str) -> None:
    """Distinguish no eligible durations from zero-day decisions.

    Args:
        mode: Empty input, excluded input, or residential input with no valid days.
    """
    permits = _permits()
    if mode == "empty":
        permits = permits.iloc[:0]
    elif mode == "excluded":
        permits["IncludeResidential"] = False
    else:
        permits["HasValidProcessingDays"] = False
    result = ProcessingAnalysis(["Before"]).run(permits)
    row = result["processing_summary"].iloc[0]
    assert row["ValidCount"] == 0
    assert pd.isna(row["MeanProcessingDays"])
    assert pd.isna(row["Q1ProcessingDays"])
    assert pd.isna(row["IQRProcessingDays"])
    assert row["TotalCount"] == (6 if mode == "invalid" else 0)


@pytest.mark.parametrize("field,value,exception", [
    ("IncludeResidential", "TRUE", TypeError),
    ("IsPending", None, TypeError),
    ("IsRightCensored", 1, TypeError),
    ("HasValidProcessingDays", "true", TypeError),
    ("Period", None, ValueError),
    ("Period", "Outside", ValueError),
    ("ProcessingDays", "10", TypeError),
    ("ProcessingDays", float("inf"), TypeError),
    ("ProcessingDays", True, TypeError),
    ("ProcessingDays", -1, ValueError),
    ("ProcessingDays", None, ValueError),
    ("IsPending", True, ValueError),
    ("IsRightCensored", True, ValueError),
    ("ResidentialType", 42, TypeError),
])
def test_invalid_evidence(field: str, value: object, exception: type[Exception]) -> None:
    """Reject malformed or contradictory evidence before calculating statistics.

    Args:
        field: Input column being corrupted.
        value: Invalid or contradictory value.
        exception: Required exception type.
    """
    values = _permits().iloc[0].to_dict()
    values[field] = value
    with pytest.raises(exception):
        ProcessingAnalysis(["Before"]).run(pd.DataFrame([values]))


def test_schema_and_configuration_validation() -> None:
    """Fail clearly on missing fields and ambiguous study configuration."""
    with pytest.raises(TypeError):
        ProcessingAnalysis().run([])
    with pytest.raises(ValueError):
        ProcessingAnalysis().run(_permits().drop(columns="IsRightCensored"))
    with pytest.raises(ValueError):
        ProcessingAnalysis().run(pd.DataFrame([[1, 2]], columns=["Period", "Period"]))
    for periods in ([], ["Before", "Before"], [" "]):
        with pytest.raises(ValueError):
            ProcessingAnalysis(periods)
    with pytest.raises(TypeError):
        ProcessingAnalysis("Before")
    with pytest.raises(TypeError):
        ProcessingAnalysis(community_column=" ")


def test_empty_unconfigured_input_retains_schemas() -> None:
    """Return empty tables with stable columns when no periods can be inferred."""
    result = ProcessingAnalysis().run(_permits().iloc[:0])
    assert result["processing_summary"].empty
    assert "MedianProcessingDays" in result["processing_summary"]
    assert "AllPermitCount" in result["processing_period_totals"]
    assert "ResidentialType" in result["processing_type_summary"]
