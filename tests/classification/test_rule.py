import pytest

from conftest import implemented

from dp_activity.classification.rule import ClassificationRule


@pytest.fixture
def contains_rule() -> ClassificationRule:
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
    assert implemented(contains_rule.matches, "New Rowhouse Building") is True
    assert implemented(contains_rule.matches, None) is False

