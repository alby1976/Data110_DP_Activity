"""Tests for classification validator.

This module verifies the documented contracts and edge cases of the classification
validator component.

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
from dataclasses import replace
from functools import partial
from pandas.testing import assert_frame_equal

from dp_activity.classification.rule import ClassificationRule
from dp_activity.classification.classifier import PermitClassifier
from dp_activity.validation.classification_validator import ClassificationValidator


def test_validation_reports_unmatched_records() -> None:
    """Verify that validation reports unmatched records."""
    permits = pd.DataFrame(
        {
            "ClassificationRule": ["HF-001", None],
            "ClassificationNeedsReview": [False, True],
        }
    )

    report = ClassificationValidator().validate(permits, [])

    assert "unmatched_count" in report.columns
    assert int(report["unmatched_count"].sum()) == 1


def _rules() -> list[ClassificationRule]:
    """Provide specific and fallback rules for real classifier integration.

    Returns:
        Rules that deliberately overlap on house descriptions.
    """
    return [ClassificationRule(
        rule_id="R1", rule_group="housing", field="description", match_type="exact",
        match_value="house", include_residential=True, residential_type="House",
        rezoning_relevant=False, priority=1, enabled=True,
        validation_status="validated_sample", notes="",
    ), ClassificationRule(
        rule_id="R2", rule_group="housing", field="description", match_type="contains",
        match_value="house", include_residential=False, residential_type="Review",
        rezoning_relevant=False, priority=2, enabled=True,
        validation_status="fallback", notes="",
    )]


def _classified() -> pd.DataFrame:
    """Produce authentic audit fields on a table with duplicate row indexes.

    Returns:
        One specific match, one fallback, and one unmatched permit.
    """
    return PermitClassifier(_rules(), {"description": "description"}).classify(
        pd.DataFrame({"description": ["house", "warehouse", "shop"]}, index=[4, 4, 9]),
    )


def test_classifier_integration_and_nonmutation() -> None:
    """Keep counts distinct, preserve inputs, and support strategy injection."""
    table = _classified()
    before = table.copy(deep=True)
    validate = partial(ClassificationValidator().validate, rules=_rules())
    report = validate(table)
    row = report.iloc[0]
    assert row["record_count"] == 3
    assert row["matched_count"] == 2
    assert row["unmatched_count"] == 1
    assert row["coverage_percentage"] == pytest.approx(200 / 3)
    assert row["review_count"] == 2
    assert row["fallback_status_count"] == 1
    assert row["overlap_count"] == row["additional_match_count"] == 1
    assert row["inconsistent_audit_count"] == 0
    assert row["status"] == "warn"
    assert_frame_equal(table, before)


def test_intentional_overlap_does_not_fail_or_require_review() -> None:
    """Accept an ordered specific winner over a broad fallback match."""
    row = ClassificationValidator().validate(_classified().iloc[:1], _rules()).iloc[0]
    assert row["status"] == "pass"
    assert row["overlap_count"] == 1
    assert row["review_count"] == 0


def test_unknown_additional_ids_and_disabled_winners_are_failures() -> None:
    """Inspect every recorded ID rather than checking only the winning rule."""
    table = _classified().iloc[:1].copy()
    table["ClassificationMatchedRules"] = [("R1", "UNKNOWN")]
    rules = [replace(_rules()[0], enabled=False), _rules()[1]]
    row = ClassificationValidator().validate(table, rules).iloc[0]
    assert row["unknown_rule_count"] == 1
    assert row["disabled_rule_count"] == 1
    assert row["status"] == "fail"


@pytest.mark.parametrize("column,value", [
    ("ClassificationMatchCount", 99), ("ClassificationConflictCount", 0),
    ("ResidentialType", "Wrong"), ("IncludeResidential", False),
    ("ClassificationNeedsReview", True), ("ValidationStatus", "review"),
    ("ClassificationMatchedRules", ("R2", "R1")),
    ("ClassificationMatchedRules", ("R1", "R1")),
])
def test_inconsistent_audit_fields_fail(column: str, value: object) -> None:
    """Detect wrong outcomes, match totals, precedence, and repeated matches."""
    table = _classified().iloc[:1].copy()
    table[column] = [value]
    row = ClassificationValidator().validate(table, _rules()).iloc[0]
    assert row["inconsistent_audit_count"] == 1
    assert row["status"] == "fail"


def test_minimal_legacy_input_reports_unavailable_metrics() -> None:
    """Report partial coverage without treating absent audit evidence as zero."""
    table = _classified()[["ClassificationRule", "ClassificationNeedsReview"]]
    row = ClassificationValidator().validate(table, _rules()).iloc[0]
    assert row["unmatched_count"] == 1
    assert row["status"] == "fail"
    assert pd.isna(row["overlap_count"])
    assert "ValidationStatus" in row["missing_audit_columns"]


def test_empty_input_has_no_coverage_percentage() -> None:
    """Do not claim full coverage when no permits were evaluated."""
    row = ClassificationValidator().validate(_classified().iloc[:0], _rules()).iloc[0]
    assert row["record_count"] == 0
    assert pd.isna(row["coverage_percentage"])
    assert row["status"] == "warn"


def test_confusion_matrix_uses_only_independent_nonblank_labels() -> None:
    """Use the labelled subset as denominator without repeating summary counts."""
    table = _classified()
    table["human_type"] = ["House", "Commercial", " "]
    report = ClassificationValidator().validate(table, _rules(), audit_label_column="human_type")
    row = report.iloc[0]
    assert row["audit_count"] == 2
    assert row["audit_error_count"] == 1
    assert row["audit_accuracy_percentage"] == 50
    confusion = report.loc[report["report_type"].eq("confusion")]
    assert confusion["record_count"].sum() == 2
    assert confusion["unmatched_count"].isna().all()
    assert set(zip(confusion["expected_type"], confusion["predicted_type"])) == {
        ("House", "House"), ("Commercial", "Review"),
    }


def test_no_audit_labels_means_unknown_accuracy() -> None:
    """Neither rule status nor empty audit samples establishes accuracy."""
    table = _classified()
    table["human_type"] = None
    report = ClassificationValidator().validate(table, _rules(), audit_label_column="human_type")
    assert len(report) == 1
    assert report.iloc[0]["audit_count"] == 0
    assert pd.isna(report.iloc[0]["audit_accuracy_percentage"])


def test_review_and_provisional_status_counts_are_separate() -> None:
    """Track rule evidence statuses independently of the combined review flag."""
    for status in ("review", "provisional"):
        rules = [replace(_rules()[0], validation_status=status)]
        table = PermitClassifier(rules, {"description": "description"}).classify(
            pd.DataFrame({"description": ["house"]}),
        )
        row = ClassificationValidator().validate(table, rules).iloc[0]
        assert row[f"{status}_status_count"] == row["review_count"] == 1
        assert row["inconsistent_audit_count"] == 0


@pytest.mark.parametrize("column,value", [
    ("ClassificationNeedsReview", "False"), ("ClassificationMatchCount", -1),
    ("ClassificationConflictCount", 1.5), ("ClassificationMatchedRules", "R1"),
    ("ClassificationRule", ""),
])
def test_malformed_audit_values_raise(column: str, value: object) -> None:
    """Reject values that cannot support meaningful count and consistency checks."""
    table = _classified().iloc[:1].copy()
    table[column] = [value]
    with pytest.raises(ValueError):
        ClassificationValidator().validate(table, _rules())


def test_invalid_inputs_and_rule_sets_raise() -> None:
    """Reject unsupported tables, duplicate rule IDs, and dependent audit labels."""
    validator = ClassificationValidator()
    with pytest.raises(TypeError):
        validator.validate([], _rules())
    with pytest.raises(TypeError):
        validator.validate(_classified(), ["R1"])
    with pytest.raises(ValueError):
        validator.validate(_classified(), [_rules()[0]] * 2)
    with pytest.raises(ValueError):
        validator.validate(pd.DataFrame(), _rules())
    with pytest.raises(ValueError):
        validator.validate(_classified(), _rules(), audit_label_column="ResidentialType")
    with pytest.raises(ValueError):
        validator.validate(_classified(), _rules(), audit_label_column="missing")
