"""Tests for schema validator.

This module verifies the documented contracts and edge cases of the schema validator
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

from dp_activity.validation.schema_validator import SchemaValidator


def test_missing_required_column_is_an_error() -> None:
    """Verify that missing required column is an error."""
    table = pd.DataFrame({"permit_number": ["DP1"]})

    issues = implemented(
        SchemaValidator().validate,
        table,
        ["permit_number", "applied_date"],
    )

    assert any(
        issue.column == "applied_date" and issue.severity.lower() == "error"
        for issue in issues
    )
