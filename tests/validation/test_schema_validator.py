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
import pytest
from dataclasses import FrozenInstanceError
from functools import partial
from pandas.testing import assert_frame_equal

from dp_activity.validation.schema_validator import SchemaIssue, SchemaValidator


def test_missing_required_column_is_an_error() -> None:
    """Verify that missing required column is an error."""
    table = pd.DataFrame({"permit_number": ["DP1"]})

    issues = SchemaValidator().validate(
        table,
        ["permit_number", "applied_date"],
    )

    assert any(
        issue.column == "applied_date" and issue.severity.lower() == "error"
        for issue in issues
    )


def test_exact_empty_schema_has_no_issues() -> None:
    """Accept schema-only tables without confusing emptiness with missing fields."""
    assert SchemaValidator().validate(pd.DataFrame(columns=["permit_number"]), ["permit_number"]) == []


def test_extra_evidence_is_informational_and_input_is_unchanged() -> None:
    """Retain source evidence and support injection as a configured callable."""
    table = pd.DataFrame({"permit_number": [None, None], "raw_category": ["A", "B"]})
    before = table.copy(deep=True)
    validate = partial(SchemaValidator().validate, required_columns=["permit_number"])
    issues = validate(table)
    assert [(issue.severity, issue.column) for issue in issues] == [("info", "raw_category")]
    assert_frame_equal(table, before)


def test_duplicate_columns_report_once() -> None:
    """Reject ambiguous field selection even when the required name is present."""
    table = pd.DataFrame([[1, 2, 3]], columns=["permit_number"] * 3)
    issues = SchemaValidator().validate(table, ["permit_number"])
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].column == "permit_number"


def test_invalid_labels_and_missing_columns_are_reported_together() -> None:
    """Keep structural and missing-field findings available in one report."""
    table = pd.DataFrame(columns=[None, 1, " ", "AppliedDate"])
    issues = SchemaValidator().validate(table, ["applied_date"])
    assert [(issue.severity, issue.column) for issue in issues] == [
        ("error", None), ("error", None), ("error", None),
        ("error", "applied_date"), ("info", "AppliedDate"),
    ]


@pytest.mark.parametrize("table", [None, {}, [], pd.Series(dtype=object)])
def test_unsupported_table_returns_result(table: object) -> None:
    """Return a table-level finding for unsupported data instead of crashing."""
    issues = SchemaValidator().validate(table, [])
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].column is None


@pytest.mark.parametrize("required", [None, "permit_number", [1]])
def test_invalid_required_column_types_raise(required: object) -> None:
    """Expose malformed schema configuration as a caller error."""
    with pytest.raises(TypeError):
        SchemaValidator().validate(pd.DataFrame(), required)


@pytest.mark.parametrize("required", [[""], [" "], ["permit_number", "permit_number"]])
def test_invalid_required_column_values_raise(required: list[str]) -> None:
    """Reject blank and repeated requirements before inspecting the data."""
    with pytest.raises(ValueError):
        SchemaValidator().validate(pd.DataFrame(), required)


def test_result_is_immutable() -> None:
    """Prevent consumers from changing a recorded validation finding."""
    issue = SchemaIssue("error", "permit_number", "Missing identifier column.")
    with pytest.raises(FrozenInstanceError):
        issue.severity = "info"
