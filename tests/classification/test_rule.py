"""Tests for rule.

This module verifies the documented contracts and edge cases of the rule component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

from dataclasses import FrozenInstanceError, asdict, replace

import pandas as pd
import pytest

from dp_activity.classification.rule import ClassificationRule, InvalidRuleError


@pytest.fixture
def contains_rule() -> ClassificationRule:
    """Create a representative contains rule for matcher tests.

    Returns:
        A configured case-insensitive ClassificationRule.
    """
    return ClassificationRule(
        rule_id="HF-001",
        rule_group="HousingForm",
        field="proposedusedescription",
        match_type="contains",
        match_value="ROWHOUSE",
        include_residential=True,
        residential_type="Rowhouse",
        rezoning_relevant=True,
        priority=10,
        enabled=True,
        validation_status="validated_2026_sample",
        notes="test",
    )


def test_contains_match_is_case_insensitive(contains_rule) -> None:
    """Verify that contains match is case insensitive.

    Args:
        contains_rule: Case-insensitive contains-rule fixture.
    """
    assert contains_rule.matches("New Rowhouse Building") is True
    assert contains_rule.matches(None) is False


@pytest.mark.parametrize("match_type,pattern,value,expected", [
    ("exact", " ROWHOUSE ", " rowhouse ", True),
    ("exact", "ROWHOUSE", "New Rowhouse", False),
    ("contains", " rowhouse ", "New ROWHOUSE Building", True),
    ("contains", "ROWHOUSE", "Apartment", False),
    ("starts_with", " row ", " ROWHOUSE building ", True),
    ("starts_with", "ROW", "New Rowhouse", False),
    ("regex", r"\browhouse\b", "New Rowhouse Building", True),
    ("regex", r"\browhouse\b", "Rowhouses", False),
    ("regex", r"^rowhouse$", "New Rowhouse", False),
    ("regex", r"^rowhouse$", " Rowhouse ", True),
    ("regex", r"\S+", "word", True),
    ("regex", " ROWHOUSE ", "New ROWHOUSE Building", True),
    ("regex", " ROWHOUSE ", "ROWHOUSE", False),
    ("exact", "123", 123, True),
    ("contains", "a.b", "aXb", False),
    ("exact", "STRASSE", "Straße", True),
])
def test_matching_operations(contains_rule, match_type, pattern, value, expected) -> None:
    """Evaluate literal and regex semantics against representative source evidence.

    Args:
        contains_rule: Base value object used to construct each specification.
        match_type: Matching operation under test.
        pattern: Literal text or regex pattern defining the rule.
        value: Source scalar to evaluate.
        expected: Expected Boolean matching outcome.
    """
    rule = replace(contains_rule, match_type=match_type, match_value=pattern)
    assert rule.matches(value) is expected


@pytest.mark.parametrize("match_type", ["exact", "contains", "starts_with", "regex"])
def test_case_sensitivity_is_explicit(contains_rule, match_type) -> None:
    """Allow callers to choose case semantics without changing the rule object.

    Args:
        contains_rule: Representative immutable rule.
        match_type: Operation to exercise in both case modes.
    """
    rule = replace(contains_rule, match_type=match_type)
    assert rule.matches("rowhouse") is True
    assert rule.matches("rowhouse", case_sensitive=True) is False
    assert rule.matches("ROWHOUSE", case_sensitive=True) is True


@pytest.mark.parametrize("value", [None, pd.NA, pd.NaT, float("nan"), "", " \t\n"])
def test_missing_and_blank_values_never_match(contains_rule, value) -> None:
    """Prevent catch-all patterns from classifying absent source evidence.

    Args:
        contains_rule: Base rule used for a broad regex specification.
        value: Missing or blank source evidence.
    """
    rule = replace(contains_rule, match_type="regex", match_value=".*")
    assert rule.matches(value) is False


def test_disabled_rules_do_not_match(contains_rule) -> None:
    """Respect rule eligibility even when a caller bypasses the loader.

    Args:
        contains_rule: Otherwise matching rule to disable.
    """
    assert replace(contains_rule, enabled=False).matches("ROWHOUSE") is False


def test_rule_is_an_immutable_value_object(contains_rule) -> None:
    """Keep equality and hashing based on rule data across predicate evaluations.

    Args:
        contains_rule: Representative value object to compare and evaluate.
    """
    identical = ClassificationRule(**asdict(contains_rule))
    before = asdict(contains_rule)
    assert identical == contains_rule
    assert hash(identical) == hash(contains_rule)
    assert len({identical, contains_rule}) == 1
    assert replace(contains_rule, priority=99) != contains_rule
    assert contains_rule.matches("Rowhouse") is True
    assert asdict(contains_rule) == before
    with pytest.raises(FrozenInstanceError):
        contains_rule.priority = 99


@pytest.mark.parametrize("changes,error", [
    ({"match_type": "unknown"}, InvalidRuleError),
    ({"match_type": "regex", "match_value": "["}, InvalidRuleError),
    ({"match_value": " "}, InvalidRuleError),
    ({"rule_id": ""}, InvalidRuleError),
    ({"field": " "}, InvalidRuleError),
    ({"match_value": None}, TypeError),
    ({"notes": []}, TypeError),
    ({"priority": "10"}, TypeError),
    ({"priority": True}, TypeError),
    ({"enabled": "FALSE"}, TypeError),
    ({"include_residential": 1}, TypeError),
    ({"rezoning_relevant": None}, TypeError),
])
def test_invalid_rule_definitions_fail_at_construction(contains_rule, changes, error) -> None:
    """Keep malformed specifications out of the classification chain.

    Args:
        contains_rule: Valid baseline rule.
        changes: Invalid fields to substitute.
        error: Exception type expected for the invalid definition.
    """
    with pytest.raises(error):
        replace(contains_rule, **changes)


@pytest.mark.parametrize("value", [["ROWHOUSE"], {"value": "ROWHOUSE"}, pd.Series(["ROWHOUSE"])])
def test_nonscalar_evidence_is_rejected(contains_rule, value) -> None:
    """Avoid accidental matches against stringified collections.

    Args:
        contains_rule: Rule whose source field should contain one scalar.
        value: Collection supplied instead of source text.
    """
    with pytest.raises(TypeError, match="scalar"):
        contains_rule.matches(value)


def test_case_option_rejects_truthy_strings(contains_rule) -> None:
    """Require a real Boolean to prevent configuration text changing semantics.

    Args:
        contains_rule: Rule used to exercise option validation.
    """
    with pytest.raises(TypeError, match="case_sensitive"):
        contains_rule.matches("ROWHOUSE", case_sensitive="false")
