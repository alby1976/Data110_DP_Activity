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

import pytest

from conftest import implemented

from dp_activity.classification.rule import ClassificationRule


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
    assert implemented(contains_rule.matches, "New Rowhouse Building") is True
    assert implemented(contains_rule.matches, None) is False
