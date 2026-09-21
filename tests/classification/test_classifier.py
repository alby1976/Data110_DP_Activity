"""Tests for classifier.

This module verifies the documented contracts and edge cases of the classifier
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

from dataclasses import replace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from conftest import REPOSITORY_ROOT
from dp_activity.classification.classifier import PermitClassifier
from dp_activity.classification.rule import ClassificationRule
from dp_activity.classification.rule_loader import RuleLoader


def test_first_matching_rule_is_recorded() -> None:
    """Verify that first matching rule is recorded."""
    rule = ClassificationRule(
        "HF-001", "HousingForm", "proposedusedescription", "contains", "ROWHOUSE",
        True, "Rowhouse", True, 10, True, "validated_2026_sample", "test",
    )
    permits = pd.DataFrame({"proposed_use_description": ["New rowhouse building"]})
    classifier = PermitClassifier(
        [rule],
        {"proposedusedescription": "proposed_use_description"},
    )

    result = classifier.classify(permits)

    assert result.loc[0, "ClassificationRule"] == "HF-001"
    assert bool(result.loc[0, "IncludeResidential"]) is True
    assert result.loc[0, "ResidentialType"] == "Rowhouse"


@pytest.fixture
def rule() -> ClassificationRule:
    """Return a validated rule for deterministic classification tests.

    Returns:
        An enabled rowhouse rule operating on source description evidence.
    """
    return ClassificationRule(
        "HF-001", "HousingForm", "description", "contains", "ROWHOUSE",
        True, "Rowhouse", True, 10, True, "validated_2026_sample", "test",
    )


def test_chain_orders_rules_and_audits_every_match(rule) -> None:
    """Select the deterministic first handler and retain later conflicting matches.

    Args:
        rule: Baseline rule with highest precedence after tie-breaking.
    """
    later = replace(rule, rule_id="HF-002", residential_type="Other", include_residential=False)
    fallback = replace(rule, rule_id="HF-999", priority=999, match_type="regex", match_value=".+")
    disabled = replace(rule, rule_id="HF-000", priority=0, enabled=False, field="absent")
    source = pd.DataFrame({"description": ["New rowhouse"]})
    result = PermitClassifier([fallback, later, disabled, rule], {"description": "description"}).classify(source)
    row = result.iloc[0]
    assert row["ClassificationRule"] == "HF-001"
    assert row["ResidentialType"] == "Rowhouse"
    assert bool(row["IncludeResidential"]) is True
    assert row["ClassificationMatchCount"] == 3
    assert row["ClassificationConflictCount"] == 2
    assert row["ClassificationMatchedRules"] == ("HF-001", "HF-002", "HF-999")
    assert bool(row["ClassificationNeedsReview"]) is False


def test_real_rules_keep_intentional_fallback_overlap_separate_from_review() -> None:
    """Classify source-like evidence with the actual ordered housing rules."""
    rules = RuleLoader().load(REPOSITORY_ROOT / "config/classification_rules.csv")
    classifier = PermitClassifier(rules, {
        "description": "description", "proposedusedescription": "proposed_use_description",
        "category": "category", "proposedusecode": "proposed_use_code",
        "landusedistrict": "land_use_district",
    })
    result = classifier.classify(pd.DataFrame({
        "description": ["New ROWHOUSE", "", "", None],
        "proposed_use_description": ["ROWHOUSE BUILDING", "", "", None],
        "category": ["Residential - New Single / Semi / Duplex", "Signs", "Unknown", None],
    }))
    assert result["ClassificationRule"].iloc[:3].tolist() == ["HF-001", "HF-900", "HF-999"]
    assert pd.isna(result["ClassificationRule"].iloc[3])
    assert result["IncludeResidential"].tolist() == [True, False, False, False]
    assert result["ClassificationNeedsReview"].tolist() == [False, False, True, True]
    assert result["ClassificationConflictCount"].iloc[0] > 0


@pytest.mark.parametrize("status,review", [
    ("validated_2026_sample", False), ("provisional", True), ("fallback", True), ("review", True),
])
def test_winning_validation_status_controls_review(rule, status, review) -> None:
    """Preserve evidence status rather than treating every matched rule as validated.

    Args:
        rule: Baseline classification rule.
        status: Winning rule's evidence label.
        review: Whether the classification should require review.
    """
    result = PermitClassifier([replace(rule, validation_status=status)], {"description": "description"}).classify(
        pd.DataFrame({"description": ["ROWHOUSE"]})
    )
    assert result.iloc[0]["ValidationStatus"] == status
    assert bool(result.iloc[0]["ClassificationNeedsReview"]) is review


def test_unmatched_and_missing_evidence_remain_reviewable(rule) -> None:
    """Keep absent and unmatched source evidence outside residential totals for review.

    Args:
        rule: Rule that does not match any input row.
    """
    source = pd.DataFrame({"description": [None, pd.NA, " ", "Office"]}, index=[4, 4, 5, 6])
    result = PermitClassifier([rule], {"description": "description"}, "Manual Review").classify(source)
    assert result["ClassificationRule"].isna().all()
    assert result["ValidationStatus"].eq("unmatched").all()
    assert result["ResidentialType"].eq("Manual Review").all()
    assert result["ClassificationNeedsReview"].all()
    assert not result["IncludeResidential"].any()
    assert not result["RezoningRelevant"].any()
    assert result["ClassificationMatchCount"].eq(0).all()
    assert result["ClassificationMatchedRules"].tolist() == [()] * 4
    assert result.index.tolist() == [4, 4, 5, 6]


def test_empty_rule_chain_marks_every_record_unmatched() -> None:
    """Allow a valid file with no enabled rules without losing input records."""
    result = PermitClassifier([], {}).classify(pd.DataFrame(index=[2, 2, 9]))
    assert len(result) == 3
    assert result["ClassificationNeedsReview"].all()
    assert result["ClassificationRule"].isna().all()


def test_case_policy_and_field_map_are_applied(rule) -> None:
    """Read explicitly mapped evidence and pass the configured case policy to rules.

    Args:
        rule: Uppercase rule whose match depends on case policy.
    """
    source = pd.DataFrame({"clean_description": ["rowhouse", "ROWHOUSE"]})
    mapping = {"description": "clean_description"}
    result = PermitClassifier([rule], mapping, case_sensitive=True).classify(source)
    assert result["ClassificationMatchCount"].tolist() == [0, 1]
    assert PermitClassifier([rule], mapping).classify(source)["ClassificationMatchCount"].tolist() == [1, 1]


def test_classification_does_not_mutate_inputs_or_depend_on_caller_list_changes(rule) -> None:
    """Keep source evidence and the assembled chain stable across repeated calls.

    Args:
        rule: Baseline matching rule.
    """
    rules = [rule]
    mapping = {"description": "description"}
    classifier = PermitClassifier(rules, mapping)
    rules.clear()
    mapping.clear()
    source = pd.DataFrame({"description": [" rowhouse ", " rowhouse "], "raw_description": [" X ", " Y "]}, index=[1, 1])
    original = source.copy(deep=True)
    result = classifier.classify(source)
    assert_frame_equal(source, original)
    assert_frame_equal(result[source.columns], original)
    assert_frame_equal(result, classifier.classify(source))
    result.iloc[0, 0] = "changed"
    assert_frame_equal(source, original)


def test_coverage_reconciles_unmatched_periods_and_overlap_counts(rule) -> None:
    """Count every record once while distinguishing overlap rows from extra matches.

    Args:
        rule: First of three matching rules for rowhouse records.
    """
    rules = [rule, replace(rule, rule_id="HF-002"), replace(rule, rule_id="HF-003")]
    classifier = PermitClassifier(rules, {"description": "description"})
    source = pd.DataFrame({
        "description": ["rowhouse", "rowhouse", "office", None],
        "Period": pd.Categorical(["Before", "During", None, "Before"], categories=["Before", "During", "Unused"]),
    }, index=[1, 1, 1, 1])
    classified = classifier.classify(source)
    before = classified.copy(deep=True)
    report = classifier.coverage_report(classified)
    assert report["record_count"].sum() == 4
    assert report["matched_count"].sum() == 2
    assert report["unmatched_count"].sum() == 2
    assert report["conflict_count"].sum() == 2
    assert report["additional_match_count"].sum() == 4
    assert report["record_percentage"].sum() == pytest.approx(100)
    assert len(report) == 4
    assert report["Period"].isna().sum() == 1
    assert_frame_equal(classified, before)
    without_period = classifier.coverage_report(classified.drop(columns="Period"))
    assert "Period" not in without_period
    assert len(without_period) == 2


def test_empty_input_has_stable_audit_and_coverage_schemas(rule) -> None:
    """Return predictable tables when an upstream filter yields no records.

    Args:
        rule: Configured rule whose source column is present but empty.
    """
    classifier = PermitClassifier([rule], {"description": "description"})
    result = classifier.classify(pd.DataFrame(columns=["description", "Period"]))
    assert result.empty
    assert result["IncludeResidential"].dtype == bool
    assert result["ClassificationMatchCount"].dtype == "int64"
    coverage = classifier.coverage_report(result)
    assert coverage.empty
    assert {"Period", "record_count", "unmatched_count", "conflict_count"}.issubset(coverage.columns)


def test_classifier_rejects_invalid_constructor_options(rule) -> None:
    """Reject ambiguous chains and truthy string options at assembly time.

    Args:
        rule: Valid rule duplicated to test audit-ID validation.
    """
    with pytest.raises(ValueError, match="unique"):
        PermitClassifier([rule, rule], {})
    with pytest.raises(TypeError, match="rules"):
        PermitClassifier(["not a rule"], {})
    with pytest.raises(TypeError, match="field_map"):
        PermitClassifier([], {"description": 1})
    with pytest.raises(ValueError, match="blank"):
        PermitClassifier([], {}, unmatched_action=" ")
    with pytest.raises(TypeError, match="case_sensitive"):
        PermitClassifier([], {}, case_sensitive="false")


def test_classifier_rejects_missing_or_conflicting_evidence(rule) -> None:
    """Prevent silent fallback when configuration or input schema is incorrect.

    Args:
        rule: Rule requiring a description field.
    """
    with pytest.raises(ValueError, match="mapping"):
        PermitClassifier([rule], {}).classify(pd.DataFrame({"description": ["rowhouse"]}))
    classifier = PermitClassifier([rule], {"description": "description"})
    with pytest.raises(ValueError, match="Missing input"):
        classifier.classify(pd.DataFrame({"other": [1]}))
    with pytest.raises(ValueError, match="already exist"):
        classifier.classify(pd.DataFrame({"description": ["rowhouse"], "ClassificationRule": ["old"]}))
    with pytest.raises(ValueError, match="unique"):
        classifier.classify(pd.DataFrame([[1, 2]], columns=["description", "description"]))
    with pytest.raises(TypeError, match="DataFrame"):
        classifier.classify([])
    with pytest.raises(ValueError, match="audit columns"):
        classifier.coverage_report(pd.DataFrame({"description": ["rowhouse"]}))
