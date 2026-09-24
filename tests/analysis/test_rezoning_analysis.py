"""Tests for rezoning analysis.

This module verifies the documented contracts and edge cases of the rezoning analysis
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

from dp_activity.analysis.rezoning_analysis import RezoningAnalysis


def test_rezoning_share_uses_all_residential_permits() -> None:
    """Verify that rezoning share uses all residential permits."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True, True, False],
            "Period": ["During"] * 4,
            "RezoningRelevant": [True, True, False, True],
            "ClassificationRule": ["A", "A", "B", "C"],
            "ResidentialType": ["Rowhouse", "Duplex", "Apartment", "Commercial"],
        }
    )

    summary = RezoningAnalysis().run(permits)["rezoning_summary"].iloc[0]

    assert summary["RezoningRelevantShare"] == pytest.approx(2 / 3)


def test_unknown_review_and_audit_breakdowns_preserve_denominator() -> None:
    """Keep unknown and reviewed records in period-wide audit denominators."""
    permits = pd.DataFrame({
        "Period": ["Before"] * 4 + ["During"],
        "IncludeResidential": [True, True, True, False, False],
        "RezoningRelevant": pd.array([True, False, None, True, False], dtype="boolean"),
        "ClassificationNeedsReview": pd.array([True, False, True, False, False], dtype="boolean"),
        "ClassificationRule": [" A ", "B", None, "C", "C"],
        "ResidentialType": ["Rowhouse", "Duplex", " ", "Office", "Office"],
        "land_use_district": ["R-CG", "R-CG", None, "C", "C"],
    }, index=[4, 4, 8, 9, 10])
    original = permits.copy(deep=True)
    result = RezoningAnalysis().run(permits)
    summary = result["rezoning_summary"].set_index("Period")
    before = summary.loc["Before"]
    assert before["PeriodResidentialCount"] == 3
    assert before["AllPermitCount"] == 4
    assert before["ExcludedCount"] == 1
    assert before["ReviewCount"] == 2
    for field in ("RezoningRelevantCount", "NotRezoningRelevantCount", "UnknownRelevanceCount"):
        assert before[field] == 1
    for field in ("RezoningRelevantShare", "NotRezoningRelevantShare", "UnknownRelevanceShare"):
        assert before[field] == pytest.approx(1 / 3)
        assert pd.isna(summary.loc["During", field])
    for key in ("rezoning_by_rule", "rezoning_by_type", "rezoning_by_district"):
        table = result[key]
        assert table["GroupResidentialCount"].sum() == 3
        assert table["PeriodResidentialCount"].eq(3).all()
        assert table["RezoningRelevantShare"].sum() == pytest.approx(1 / 3)
        assert table["UnknownRelevanceCount"].sum() == 1
    assert set(result["rezoning_by_rule"]["ClassificationRule"]) == {"A", "B", "Unknown"}
    pd.testing.assert_frame_equal(permits, original)


@pytest.mark.parametrize("review", [None, [pd.NA]])
def test_unavailable_review_is_not_reported_as_zero(review: list | None) -> None:
    """Distinguish missing review evidence from a known absence of reviews."""
    permits = pd.DataFrame({"Period": ["Before"], "IncludeResidential": [True],
                            "RezoningRelevant": [True]})
    if review is not None:
        permits["ClassificationNeedsReview"] = pd.array(review, dtype="boolean")
    row = RezoningAnalysis().run(permits)["rezoning_summary"].iloc[0]
    assert pd.isna(row["ReviewCount"])
    assert row["RezoningRelevantShare"] == 1


def test_empty_input_retains_output_schema() -> None:
    """Return usable empty tables when no period has observed records."""
    result = RezoningAnalysis().run(pd.DataFrame(columns=[
        "Period", "IncludeResidential", "RezoningRelevant", "ResidentialType",
    ]))
    assert set(result) == {"rezoning_summary", "rezoning_by_type"}
    for table in result.values():
        assert table.empty
        assert "PeriodResidentialCount" in table
        assert "RezoningRelevantShare" in table


@pytest.mark.parametrize("field,value,error", [
    ("IncludeResidential", "True", TypeError),
    ("IncludeResidential", None, TypeError),
    ("RezoningRelevant", 1, TypeError),
    ("ClassificationNeedsReview", "False", TypeError),
    ("Period", " ", ValueError),
    ("Period", None, ValueError),
    ("ResidentialType", 12, TypeError),
    ("ClassificationRule", 12, TypeError),
    ("land_use_district", 12, TypeError),
])
def test_invalid_values_are_rejected(field: str, value: object, error: type[Exception]) -> None:
    """Reject ambiguous flags and labels instead of silently changing counts."""
    permits = pd.DataFrame({"Period": ["Before"], "IncludeResidential": [True],
                            "RezoningRelevant": [True]})
    permits[field] = value
    with pytest.raises(error):
        RezoningAnalysis().run(permits)


def test_invalid_tables_are_rejected() -> None:
    """Report missing and duplicate columns before attempting aggregation."""
    with pytest.raises(TypeError):
        RezoningAnalysis().run([])
    with pytest.raises(ValueError, match="Missing"):
        RezoningAnalysis().run(pd.DataFrame())
    with pytest.raises(ValueError, match="unique"):
        RezoningAnalysis().run(pd.DataFrame(columns=["Period", "Period"]))
