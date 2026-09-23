"""Tests for geography analysis.

This module verifies the documented contracts and edge cases of the geography analysis
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

from dp_activity.analysis.geography_analysis import GeographyAnalysis


def test_small_baseline_is_flagged_not_deleted() -> None:
    """Verify that small baseline is flagged not deleted."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True] * 4,
            "Period": ["Before", "During", "During", "During"],
            "Community": ["Varsity"] * 4,
            "Ward": [1] * 4,
        }
    )

    analysis = GeographyAnalysis(minimum_baseline_count=5)
    community = analysis.run(permits)["community_summary"]

    assert community.loc[community["Community"] == "Varsity", "SmallBaselineWarning"].iloc[0]


def test_comparisons_missing_geography_and_denominators() -> None:
    """Keep missing locations in totals and avoid misleading zero-base changes."""
    permits = pd.DataFrame({
        "IncludeResidential": [True] * 7 + [False],
        "Period": ["During", "Before", "During", "Before", "During", "During", "Post", "During"],
        "Community": ["A", "A", "A", None, " ", "New", "A", "Excluded"],
        "Ward": [1, 1, 1, None, None, 2, 1, 3],
    })
    original = permits.copy(deep=True)
    result = GeographyAnalysis(2, period_order=["Before", "During", "Post"]).run(permits)
    community = result["community_summary"]
    during = community.loc[community["Period"].eq("During")].set_index("Community")
    assert during.loc["A", "PermitCount"] == 2
    assert during.loc["A", "AbsoluteChange"] == 1
    assert during.loc["A", "PercentChange"] == 100
    assert during.loc["A", "PermitShare"] == 0.5
    assert during.loc["New", "BaselinePermitCount"] == 0
    assert pd.isna(during.loc["New", "PercentChange"])
    assert during.loc["New", "SmallBaselineWarning"]
    assert community.loc[community["Period"].eq("Post"), "AbsoluteChange"].isna().all()
    assert "Excluded" not in community["Community"].dropna().tolist()
    for key in ("community_summary", "ward_summary"):
        table = result[key]
        assert table.groupby("Period")["PermitCount"].sum().to_dict() == {"Before": 2, "During": 4, "Post": 1}
        assert table.loc[table["Period"].eq("During") & table["IsMissingGeography"], "PermitCount"].item() == 1
    totals = result["geography_period_totals"].set_index("Period")
    assert totals.loc["During", "AllPermitCount"] == 5
    assert totals.loc["During", "ExcludedCount"] == 1
    assert totals.loc["During", "MissingCommunityCount"] == 1
    assert totals.loc["During", "MissingWardCount"] == 1
    pd.testing.assert_frame_equal(permits, original)


def test_zero_counts_threshold_and_real_unknown_label() -> None:
    """Retain disappearing places and distinguish missing from named Unknown."""
    permits = pd.DataFrame({"IncludeResidential": [True, True], "Period": ["Before"] * 2,
                            "Community": ["Unknown", None], "Ward": ["1", None]})
    result = GeographyAnalysis(1).run(permits)
    table = result["community_summary"]
    during = table.loc[table["Period"].eq("During")]
    assert len(during) == 2
    assert during["PermitCount"].eq(0).all()
    assert during["PercentChange"].eq(-100).all()
    assert during["PermitShare"].isna().all()
    assert not during["SmallBaselineWarning"].any()
    assert during["IsMissingGeography"].sum() == 1


@pytest.mark.parametrize("excluded_only", [False, True])
def test_empty_residential_population(excluded_only: bool) -> None:
    """Return stable schemas and period totals even without included records.

    Args:
        excluded_only: Whether to retain one excluded input record.
    """
    permits = pd.DataFrame({"IncludeResidential": [False], "Period": ["Before"],
                            "Community": ["A"], "Ward": [1]})
    if not excluded_only:
        permits = permits.iloc[:0]
    result = GeographyAnalysis(5).run(permits)
    assert result["community_summary"].empty
    assert "SmallBaselineWarning" in result["ward_summary"]
    totals = result["geography_period_totals"]
    assert totals["PeriodResidentialCount"].sum() == 0
    assert totals["ExcludedCount"].sum() == int(excluded_only)


@pytest.mark.parametrize("threshold,exception", [(-1, ValueError), (True, TypeError), (1.5, TypeError)])
def test_invalid_threshold(threshold: object, exception: type[Exception]) -> None:
    """Reject thresholds that cannot represent a minimum record count.

    Args:
        threshold: Invalid configuration value.
        exception: Expected validation exception.
    """
    with pytest.raises(exception):
        GeographyAnalysis(threshold)


@pytest.mark.parametrize("field,value,exception", [
    ("IncludeResidential", "TRUE", TypeError),
    ("IncludeResidential", None, TypeError),
    ("Period", "Outside", ValueError),
    ("Period", None, ValueError),
    ("Community", ["A"], TypeError),
])
def test_invalid_records(field: str, value: object, exception: type[Exception]) -> None:
    """Fail visibly rather than silently excluding unusable records.

    Args:
        field: Input field to replace.
        value: Invalid field value.
        exception: Expected validation exception.
    """
    values = {"IncludeResidential": True, "Period": "Before", "Community": "A", "Ward": 1}
    values[field] = value
    with pytest.raises(exception):
        GeographyAnalysis(5).run(pd.DataFrame([values]))


def test_configured_fields_and_period_labels() -> None:
    """Use cleaner field names and explicit ordering rather than row order."""
    permits = pd.DataFrame({"IncludeResidential": [True, True], "Period": ["Later", "Earlier"],
                            "community": ["A", "A"], "ward": ["1", "1"]})
    result = GeographyAnalysis(5, period_order=["Earlier", "Later"],
                               community_column="community", ward_column="ward").run(permits)
    table = result["community_summary"]
    assert table["Period"].tolist() == ["Earlier", "Later"]
    assert table.iloc[1]["AbsoluteChange"] == 0


@pytest.mark.parametrize("periods", [[], ["Before"], ["Before", "Before"], ["Before", " "]])
def test_invalid_period_configuration(periods: list[str]) -> None:
    """Require an unambiguous primary comparison.

    Args:
        periods: Invalid ordered study labels.
    """
    with pytest.raises(ValueError):
        GeographyAnalysis(5, period_order=periods)


def test_missing_and_duplicate_columns() -> None:
    """Reject schema ambiguity before attempting aggregation."""
    analysis = GeographyAnalysis(5)
    with pytest.raises(ValueError, match="Missing geography fields"):
        analysis.run(pd.DataFrame({"Period": ["Before"]}))
    with pytest.raises(ValueError, match="unique"):
        analysis.run(pd.DataFrame([[1, 2]], columns=["Ward", "Ward"]))
    with pytest.raises(TypeError, match="DataFrame"):
        analysis.run([])
