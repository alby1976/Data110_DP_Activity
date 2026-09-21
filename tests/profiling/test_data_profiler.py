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
import pytest
from pandas.testing import assert_frame_equal

from dp_activity.profiling.data_profiler import DataProfiler


def test_profile_includes_shape_missingness_and_value_counts() -> None:
    """Verify that profile includes shape missingness and value counts."""
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP2"],
            "category": ["Residential", None],
        }
    )

    profile = DataProfiler().profile(permits, ["category"])

    assert {"summary", "missingness"}.issubset(profile)
    assert profile["summary"].iloc[0]["row_count"] == 2
    assert "category" in profile
    assert profile["summary"].iloc[0]["column_count"] == 2
    missing = profile["missingness"].set_index("column")
    assert missing.loc["category", "missing_count"] == 1
    assert missing.loc["category", "missing_percentage"] == 50.0
    assert profile["dtypes"].set_index("column").loc["category", "dtype"] == "object"
    assert profile["category"]["count"].tolist() == [1, 1]
    assert profile["category"]["percentage"].tolist() == [50.0, 50.0]


@pytest.mark.parametrize("column", ["PermitNum", "permitnum", "permit_number"])
def test_identifier_duplicates_exclude_missing_values(column) -> None:
    """Distinguish duplicate membership, excess rows, and missing identifiers.

    Args:
        column: Raw, published, or normalized identifier name.
    """
    permits = pd.DataFrame({column: ["DP1", None, "DP1", "DP2", pd.NA, "DP1"]}, index=[7] * 6)
    result = DataProfiler().profile(permits, [])
    assert result["permit_uniqueness"].iloc[0].to_dict() == {
        "column": column, "non_missing_count": 4, "unique_count": 2,
        "duplicate_row_count": 3, "duplicate_excess_count": 2,
    }
    assert result["duplicate_examples"]["row_position"].tolist() == [0, 2, 5]
    assert result["duplicate_examples"]["permit_number"].tolist() == ["DP1"] * 3


def test_duplicate_examples_are_bounded_but_counts_are_complete() -> None:
    """Keep review tables small without undercounting repeated source records."""
    result = DataProfiler().profile(pd.DataFrame({"permitnum": ["DP1"] * 25}), [])
    assert len(result["duplicate_examples"]) == 20
    assert result["permit_uniqueness"].iloc[0]["duplicate_row_count"] == 25
    assert result["permit_uniqueness"].iloc[0]["duplicate_excess_count"] == 24


def test_date_ranges_distinguish_invalid_missing_and_valid_values() -> None:
    """Profile mixed date formats without interpreting numeric values as epochs."""
    permits = pd.DataFrame({
        "AppliedDate": ["2024-01-01", "2024-01-02T02:00:00+02:00", "bad", None, "", 42],
        "decision_date": [None] * 6,
        "observed_at": pd.to_datetime(["2024-02-01"] * 6, utc=True),
        "category": ["not a date"] * 6,
    })
    result = DataProfiler().profile(permits, [])["date_ranges"].set_index("column")
    assert set(result.index) == {"AppliedDate", "decision_date", "observed_at"}
    assert result.loc["AppliedDate", "valid_count"] == 2
    assert result.loc["AppliedDate", "missing_count"] == 1
    assert result.loc["AppliedDate", "invalid_count"] == 3
    assert result.loc["AppliedDate", "min_date"] == pd.Timestamp("2024-01-01", tz="UTC")
    assert result.loc["AppliedDate", "max_date"] == pd.Timestamp("2024-01-02", tz="UTC")
    assert result.loc["decision_date", "missing_count"] == 6
    assert result.loc["decision_date", "invalid_count"] == 0
    assert pd.isna(result.loc["decision_date", "min_date"])
    assert result.loc["observed_at", "valid_count"] == 6


def test_categorical_counts_include_nulls_preserve_blanks_and_stable_ties() -> None:
    """Return observed categories with a single null bucket and all-row percentages."""
    permits = pd.DataFrame({"category": ["B", "A", None, "B", "A", float("nan"), "", " "]})
    result = DataProfiler().profile(permits, ["category", "category"])["category"]
    assert result["value"].iloc[:2].tolist() == ["B", "A"]
    assert pd.isna(result["value"].iloc[2])
    assert result["value"].iloc[3:].tolist() == ["", " "]
    assert result["count"].tolist() == [2, 2, 2, 1, 1]
    assert result["percentage"].sum() == pytest.approx(100.0)


def test_description_review_preserves_text_and_limits_longest_examples() -> None:
    """Provide bounded review evidence with stable ties and original row positions."""
    descriptions = ["xx", "yy", " ", None] + ["z" * size for size in range(3, 25)]
    permits = pd.DataFrame({"ProposedUseDescription": descriptions, "description": [None] * 26})
    result = DataProfiler().profile(permits, [])["description_examples"]
    assert len(result) == 20
    assert result["character_count"].tolist() == list(range(24, 4, -1))
    assert result.iloc[0]["row_position"] == 25
    ties = DataProfiler().profile(pd.DataFrame({"description": [" ab ", " cd ", None]}), [])
    assert ties["description_examples"]["description"].tolist() == [" ab ", " cd "]
    assert ties["description_examples"]["row_position"].tolist() == [0, 1]


@pytest.mark.parametrize("with_columns", [True, False])
def test_empty_inputs_keep_report_schemas(with_columns) -> None:
    """Return exportable empty reports without divide-by-zero errors.

    Args:
        with_columns: Whether the empty frame retains known source columns.
    """
    permits = pd.DataFrame(columns=["permitnum", "applieddate", "category"] if with_columns else [])
    result = DataProfiler().profile(permits, ["category"] if with_columns else [])
    assert result["summary"].iloc[0]["row_count"] == 0
    assert result["summary"].iloc[0]["column_count"] == len(permits.columns)
    assert result["missingness"]["missing_percentage"].eq(0).all()
    assert list(result["duplicate_examples"]) == ["column", "row_position", "permit_number"]
    assert "invalid_count" in result["date_ranges"]
    assert result["description_examples"].empty
    if with_columns:
        assert result["category"].empty
        assert list(result["category"]) == ["value", "count", "percentage"]


def test_profile_is_deterministic_and_does_not_mutate_source() -> None:
    """Keep the profiling filter reusable without changing its upstream table."""
    permits = pd.DataFrame({
        "permitnum": ["DP1", "DP1"], "applieddate": ["bad", "2024-01-01"],
        "description": [" Original ", "Other"], "category": ["A", None],
    }, index=[5, 5])
    original = permits.copy(deep=True)
    profiler = DataProfiler()
    first = profiler.profile(permits, ["category"])
    second = profiler.profile(permits, ["category"])
    assert_frame_equal(permits, original)
    for name in first:
        assert isinstance(first[name], pd.DataFrame)
        assert_frame_equal(first[name], second[name])
    first["description_examples"].loc[0, "description"] = "Changed"
    assert_frame_equal(permits, original)
    assert second["description_examples"].iloc[0]["description"] == " Original "


@pytest.mark.parametrize("permits,categories,error", [
    ([], [], TypeError),
    (pd.DataFrame([[1, 2]], columns=["a", "a"]), [], ValueError),
    (pd.DataFrame({1: ["A"]}), [], TypeError),
    (pd.DataFrame({"category": ["A"]}), "category", TypeError),
    (pd.DataFrame({"category": ["A"]}), [1], TypeError),
    (pd.DataFrame({"category": ["A"]}), ["missing"], ValueError),
    (pd.DataFrame({"summary": ["A"]}), ["summary"], ValueError),
    (pd.DataFrame({"category": [["A"]]}), ["category"], TypeError),
])
def test_invalid_inputs_raise_clear_errors(permits, categories, error) -> None:
    """Reject ambiguous input rather than silently producing misleading reports.

    Args:
        permits: Invalid source or source paired with invalid options.
        categories: Requested categorical fields.
        error: Expected exception type for the contract violation.
    """
    with pytest.raises(error):
        DataProfiler().profile(permits, categories)
