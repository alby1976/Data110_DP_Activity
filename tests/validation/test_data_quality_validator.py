"""Tests for data quality validator.

This module verifies the documented contracts and edge cases of the data quality
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

from dp_activity.validation.data_quality_validator import DataQualityValidator


def test_duplicate_permit_numbers_are_reported() -> None:
    """Verify that duplicate permit numbers are reported."""
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP1"],
            "applied_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        }
    )

    results = implemented(DataQualityValidator().validate, permits, {})

    duplicate_check = next(item for item in results if "duplicate" in item.check_name.lower())
    assert duplicate_check.affected_rows == 2
    assert duplicate_check.status.lower() in {"warn", "fail"}
