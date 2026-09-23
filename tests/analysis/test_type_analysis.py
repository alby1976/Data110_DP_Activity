"""Tests for type analysis.

This module verifies the documented contracts and edge cases of the type analysis
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

from dp_activity.analysis.type_analysis import TypeAnalysis


def test_type_share_uses_period_residential_total() -> None:
    """Verify that type share uses period residential total."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True, True],
            "Period": ["Before", "Before", "Before"],
            "ResidentialType": ["Rowhouse", "Rowhouse", "Duplex"],
        }
    )

    table = TypeAnalysis().run(permits)["type_summary"]
    rowhouse = table.loc[table["ResidentialType"] == "Rowhouse"].iloc[0]
    assert rowhouse["TypeShare"] == pytest.approx(2 / 3)


def test_unknown_review_and_excluded_records_preserve_denominator() -> None:
    """Retain included ambiguous types and leave source records unchanged."""
    permits = pd.DataFrame({"Period": ["Before"] * 5,
                            "IncludeResidential": [True, True, True, True, False],
                            "ResidentialType": [None, " ", "Review", "House", "Commercial"]}, index=[1] * 5)
    before = permits.copy(deep=True)
    tables = TypeAnalysis().run(permits)
    summary = tables["type_summary"].set_index("ResidentialType")
    assert summary.loc["Unknown", "PermitCount"] == 2
    assert summary.loc["Review", "TypeShare"] == 0.25
    assert summary["TypeShare"].sum() == 1
    assert "Commercial" not in summary.index
    assert tables["type_period_totals"].iloc[0]["ExcludedCount"] == 1
    assert_frame_equal(permits, before)


def test_zero_fill_changes_and_contextual_period() -> None:
    """Use explicit period order regardless of row order and retain absent types."""
    permits = pd.DataFrame({"Period": ["During", "Before", "Before", "Post"],
                            "IncludeResidential": [True] * 4,
                            "ResidentialType": ["Rowhouse", "House", "House", "House"]})
    summary = TypeAnalysis(["Before", "During", "Post"]).run(permits)["type_summary"]
    during = summary.loc[summary.Period.eq("During")].set_index("ResidentialType")
    assert during.loc["House", "PermitCount"] == 0
    assert during.loc["House", "PercentChange"] == -100
    assert during.loc["House", "ShareChangePercentagePoints"] == -100
    assert during.loc["Rowhouse", "AbsoluteChange"] == 1
    assert pd.isna(during.loc["Rowhouse", "PercentChange"])
    assert summary.loc[summary.Period.eq("Post"), "AbsoluteChange"].isna().all()


def test_empty_residential_period_has_undefined_shares() -> None:
    """Do not turn zero-denominator shares into measured zero percentages."""
    permits = pd.DataFrame({"Period": ["Before", "During"], "IncludeResidential": [False, True],
                            "ResidentialType": ["Commercial", "House"]})
    tables = TypeAnalysis(["Before", "During", "Post"]).run(permits)
    summary = tables["type_summary"]
    assert summary.loc[summary.Period.isin(["Before", "Post"]), "TypeShare"].isna().all()
    assert tables["type_period_totals"].Period.tolist() == ["Before", "During", "Post"]
    assert summary.loc[summary.Period.eq("During"), "ShareChangePercentagePoints"].isna().all()


def test_no_included_types_keeps_period_totals() -> None:
    """Report empty type output without losing period denominators."""
    permits = pd.DataFrame({"Period": ["Before"], "IncludeResidential": [False], "ResidentialType": [None]})
    tables = TypeAnalysis(["Before", "During"]).run(permits)
    assert tables["type_summary"].empty
    assert tables["type_period_totals"].AllPermitCount.tolist() == [1, 0]
    empty = TypeAnalysis(["Before", "During"]).run(permits.iloc[:0])
    assert empty["type_period_totals"].PeriodResidentialCount.tolist() == [0, 0]


def test_inferred_period_order_does_not_claim_comparison() -> None:
    """Avoid assigning baseline semantics to incidental input row order."""
    permits = pd.DataFrame({"Period": ["B", "A"], "IncludeResidential": [True, True], "ResidentialType": ["House", "House"]})
    summary = TypeAnalysis().run(permits)["type_summary"]
    assert summary.AbsoluteChange.isna().all()


@pytest.mark.parametrize("column,value,exception", [
    ("IncludeResidential", "False", TypeError), ("IncludeResidential", None, TypeError),
    ("Period", None, ValueError), ("Period", " ", ValueError),
    ("ResidentialType", 12, TypeError),
])
def test_invalid_input_values_raise(column: str, value: object, exception: type[Exception]) -> None:
    """Reject ambiguous values instead of silently excluding records."""
    permits = pd.DataFrame({"Period": ["A"], "IncludeResidential": [True], "ResidentialType": ["House"]})
    permits[column] = [value]
    with pytest.raises(exception):
        TypeAnalysis().run(permits)


def test_invalid_configuration_and_missing_schema_raise() -> None:
    """Reject duplicate periods, unknown periods, and missing fields."""
    with pytest.raises(ValueError):
        TypeAnalysis(["A", "A"])
    with pytest.raises(TypeError):
        TypeAnalysis("A")
    with pytest.raises(ValueError):
        TypeAnalysis().run(pd.DataFrame())
    with pytest.raises(ValueError):
        TypeAnalysis(["B"]).run(pd.DataFrame({"Period": ["A"], "IncludeResidential": [True], "ResidentialType": ["House"]}))
