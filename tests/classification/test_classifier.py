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

import pandas as pd

from conftest import implemented

from dp_activity.classification.classifier import PermitClassifier
from dp_activity.classification.rule import ClassificationRule


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

    result = implemented(classifier.classify, permits)

    assert result.loc[0, "ClassificationRule"] == "HF-001"
    assert bool(result.loc[0, "IncludeResidential"]) is True
    assert result.loc[0, "ResidentialType"] == "Rowhouse"
