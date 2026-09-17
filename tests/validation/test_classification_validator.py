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

from conftest import implemented

from dp_activity.validation.classification_validator import ClassificationValidator


def test_validation_reports_unmatched_records() -> None:
    """Verify that validation reports unmatched records."""
    permits = pd.DataFrame(
        {
            "ClassificationRule": ["HF-001", None],
            "ClassificationNeedsReview": [False, True],
        }
    )

    report = implemented(ClassificationValidator().validate, permits, [])

    assert "unmatched_count" in report.columns
    assert int(report["unmatched_count"].sum()) == 1
