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
    assert summary["ExcludedCount"] == 1
    assert pd.isna(summary["ReviewCount"])


def _permits() -> pd.DataFrame:
    """Build an auditable sample with review flags and missing group labels.

    Returns:
        Records with a Before relevance share of one half and During of two thirds.
    """
    return pd.DataFrame({
        "Period": ["During", "Before", "Before", "During", "During", "Post", "During"],
        "IncludeResidential": [True] * 6 + [False],
        "RezoningRelevant": [True, True, False, True, False, True, True],
        "ClassificationNeedsReview": [True, False, True, False, True, False, True],
        "ClassificationRule": ["A", "A", None, "A", " ", "B", "Excluded"],
        "ResidentialType": ["Rowhouse", "Rowhouse", "Review", "Duplex", None, "Rowhouse", "Commercial"],
        "land_use_district": ["R-CG", "R-CG", None, "R-CG", " ", "R-G", "Commercial"],
    })


def test_comparisons_review_and_input_preservation() -> None:
    """Use explicit period order, retain review uncertainty, and leave input intact."""
    permits = _permits()
    original = permits.copy(deep=True)
    summary = RezoningAnalysis(["Before", "During", "Post"]).run(permits)["rezoning_summary"].set_index("Period")
    assert summary.loc["During", "ResidentialCount"] == 3
    assert summary.loc["During", "RezoningRelevantCount"] == 2
    assert summary.loc["During", "NotRezoningRelevantCount"] == 1
    assert summary.loc["During", "ReviewCount"] == 2
    assert summary.loc["During", "RelevantReviewCount"] == 1
    assert summary.loc["During", "BaselineRelevantCount"] == 1
    assert summary.loc["During", "AbsoluteChange"] == 1
    assert summary.loc["During", "PercentChange"] == 100
    assert summary.loc["During", "ShareChangePercentagePoints"] == pytest.approx(100 / 6)
    assert pd.isna(summary.loc["Before", "AbsoluteChange"])
    assert pd.isna(summary.loc["Post", "AbsoluteChange"])
    assert pd.isna(summary.loc["Post", "BaselinePeriod"])
    pd.testing.assert_frame_equal(permits, original)


def test_audit_breakdowns_reconcile_with_missing_groups() -> None:
    """Reconcile each audit independently without losing unlabeled records."""
    permits = _permits()
    permits.index = [5] * len(permits)
    result = RezoningAnalysis(["Before", "During", "Post"], district_column="land_use_district").run(permits)
    summary = result["rezoning_summary"].set_index("Period")
    for key, label in (("rezoning_rule_summary", "ClassificationRule"),
                       ("rezoning_type_summary", "ResidentialType"),
                       ("rezoning_district_summary", "LandUseDistrict")):
        audit = result[key]
        for count in ("ResidentialCount", "RezoningRelevantCount", "NotRezoningRelevantCount", "ReviewCount"):
            assert audit.groupby("Period")[count].sum().to_dict() == summary[count].to_dict()
        assert audit[label].isna().any()
        assert "Excluded" not in audit[label].dropna().tolist()
    district = result["rezoning_district_summary"]
    assert district.loc[district["Period"].eq("During") & district["LandUseDistrict"].eq("R-CG"), "RezoningRelevantShare"].item() == 1


@pytest.mark.parametrize("empty_baseline", [False, True])
def test_zero_baseline_and_empty_periods(empty_baseline: bool) -> None:
    """Leave undefined changes and shares null instead of inventing percentages.

    Args:
        empty_baseline: Whether the baseline lacks all residential records.
    """
    permits = pd.DataFrame({"Period": ["Before", "During"],
                            "IncludeResidential": [not empty_baseline, True],
                            "RezoningRelevant": [False, True]})
    summary = RezoningAnalysis(["Before", "During", "Post"]).run(permits)["rezoning_summary"].set_index("Period")
    assert summary.loc["During", "AbsoluteChange"] == 1
    assert pd.isna(summary.loc["During", "PercentChange"])
    if empty_baseline:
        assert pd.isna(summary.loc["During", "ShareChangePercentagePoints"])
    else:
        assert summary.loc["During", "ShareChangePercentagePoints"] == 100
    assert summary.loc["Post", "ResidentialCount"] == 0
    assert pd.isna(summary.loc["Post", "RezoningRelevantShare"])


def test_inferred_periods_do_not_imply_comparisons() -> None:
    """Avoid inventing a before/during comparison from arbitrary input order."""
    result = RezoningAnalysis().run(_permits())["rezoning_summary"]
    assert result["Period"].tolist() == ["During", "Before", "Post"]
    assert result["AbsoluteChange"].isna().all()


@pytest.mark.parametrize("configured", [False, True])
def test_empty_input_has_stable_schemas(configured: bool) -> None:
    """Retain configured periods and optional audit schemas with no records.

    Args:
        configured: Whether explicit empty periods should appear in the summary.
    """
    result = RezoningAnalysis(["Before", "During"] if configured else None).run(_permits().iloc[:0])
    summary = result["rezoning_summary"]
    assert len(summary) == (2 if configured else 0)
    assert "RezoningRelevantShare" in summary
    assert summary["ResidentialCount"].sum() == 0
    assert summary["RezoningRelevantShare"].isna().all()
    assert result["rezoning_rule_summary"].empty
    assert "ClassificationRule" in result["rezoning_rule_summary"]


@pytest.mark.parametrize("field,value,exception", [
    ("IncludeResidential", "TRUE", TypeError), ("IncludeResidential", None, TypeError),
    ("RezoningRelevant", None, TypeError), ("RezoningRelevant", "Review", TypeError),
    ("RezoningRelevant", 1, TypeError), ("ClassificationNeedsReview", None, TypeError),
    ("Period", None, ValueError), ("Period", "Outside", ValueError),
    ("ClassificationRule", 42, TypeError), ("ResidentialType", ["House"], TypeError),
    ("land_use_district", 1, TypeError),
])
def test_invalid_inputs(field: str, value: object, exception: type[Exception]) -> None:
    """Reject malformed flags and audit fields without guessing classifications.

    Args:
        field: Field to corrupt in one included record.
        value: Invalid value for the field.
        exception: Expected exception type.
    """
    row = _permits().iloc[0].to_dict()
    row[field] = value
    with pytest.raises(exception):
        RezoningAnalysis(["Before", "During"], district_column="land_use_district").run(pd.DataFrame([row]))


def test_configuration_and_schema_errors() -> None:
    """Require unambiguous schemas and study labels before aggregation."""
    for periods in ([], ["Before", "Before"], [" "]):
        with pytest.raises(ValueError):
            RezoningAnalysis(periods)
    with pytest.raises(TypeError):
        RezoningAnalysis("Before")
    with pytest.raises(TypeError):
        RezoningAnalysis(district_column=" ")
    with pytest.raises(TypeError):
        RezoningAnalysis().run([])
    with pytest.raises(ValueError):
        RezoningAnalysis().run(_permits().drop(columns="RezoningRelevant"))
    with pytest.raises(ValueError):
        RezoningAnalysis().run(pd.DataFrame([[1, 2]], columns=["Period", "Period"]))
