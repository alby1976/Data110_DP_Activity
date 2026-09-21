"""Tests for rule loader.

This module verifies the documented contracts and edge cases of the rule loader
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

import csv
from pathlib import Path

import pytest

from conftest import REPOSITORY_ROOT

from dp_activity.classification.rule import ClassificationRule, InvalidRuleError
from dp_activity.classification.rule_loader import RuleLoader


def test_rules_are_enabled_unique_and_sorted() -> None:
    """Verify that rules are enabled unique and sorted."""
    rules = RuleLoader().load(REPOSITORY_ROOT / "config/classification_rules.csv")
    assert rules[0].rule_id == "HF-001"
    assert len({rule.rule_id for rule in rules}) == len(rules)
    assert [(rule.priority, rule.rule_id) for rule in rules] == sorted(
        (rule.priority, rule.rule_id) for rule in rules
    )
    assert all(rule.enabled for rule in rules)


@pytest.fixture
def rule_row() -> dict[str, str]:
    """Return valid CSV cells for one housing-form rule.

    Returns:
        A fresh row mapping for each test to customize.
    """
    return {
        "RuleID": "HF-001", "RuleGroup": "HousingForm", "Field": "description",
        "MatchType": "contains", "MatchValue": "ROWHOUSE", "IncludeResidential": "TRUE",
        "ResidentialType": "Rowhouse", "RezoningRelevant": "TRUE", "Priority": "10",
        "Enabled": "TRUE", "ValidationStatus": "provisional", "Notes": "",
    }


def _write_rules(path: Path, rows: list[dict[str, str]], headers: list[str]) -> Path:
    """Write a small rule fixture using standard CSV quoting.

    Args:
        path: Temporary output location.
        rows: Rule definitions to serialize.
        headers: Ordered CSV column names, including deliberate schema errors.

    Returns:
        Path to the UTF-8 CSV fixture.
    """
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_loader_converts_types_filters_and_breaks_priority_ties(tmp_path, rule_row) -> None:
    """Create typed value objects and sort enabled rules independently of file order.

    Args:
        tmp_path: Isolated fixture directory.
        rule_row: Valid CSV row to customize.
    """
    rows = [
        dict(rule_row, RuleID="HF-003", Priority="10"),
        dict(rule_row, RuleID="HF-002", Priority="10"),
        dict(rule_row, RuleID="HF-000", Priority="-1", Enabled="FALSE"),
        dict(rule_row, RuleID="HF-001", Priority="+2", IncludeResidential="FALSE", MatchValue="Signs"),
    ]
    path = _write_rules(tmp_path / "rules.csv", rows, list(rule_row))
    before = path.read_bytes()
    rules = RuleLoader().load(path)
    assert [rule.rule_id for rule in rules] == ["HF-001", "HF-002", "HF-003"]
    assert isinstance(rules[0], ClassificationRule)
    assert rules[0].priority == 2
    assert rules[0].include_residential is False
    assert rules[0].rezoning_relevant is True
    assert rules[0].notes == ""
    assert rules[0].matches("New Signs") is True
    assert rules == RuleLoader().load(path)
    assert path.read_bytes() == before


def test_normalization_preserves_quoted_regex_and_multiline_notes(tmp_path, rule_row) -> None:
    """Keep significant regex text while accepting BOMs, aliases, and padded headers.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Valid row to adapt to regex matching.
    """
    row = dict(rule_row, Field=" proposed_use_description ", MatchType="regex",
               MatchValue=r" ROW(HOUSE|HOME),? ", Notes="Quoted, explanation\nSecond line")
    padded = {f" {name} ": value for name, value in row.items()}
    padded["Extra"] = "ignored"
    path = _write_rules(tmp_path / "rules.csv", [padded], list(padded))
    rule = RuleLoader().load(path)[0]
    assert rule.field == "proposedusedescription"
    assert rule.match_value == row["MatchValue"]
    assert rule.notes == row["Notes"]
    assert rule.matches("New ROWHOUSE, Building") is True


@pytest.mark.parametrize("column,value", [
    ("RuleID", " "), ("RuleGroup", ""), ("MatchValue", ""),
    ("ResidentialType", ""), ("Field", "unknown"),
    ("MatchType", "glob"), ("ValidationStatus", "approved"),
    ("Priority", "1.5"), ("Priority", "1e2"), ("Priority", "1_000"),
    ("IncludeResidential", "yes"), ("IncludeResidential", "1"),
    ("RezoningRelevant", "false"), ("Enabled", "0"),
])
def test_invalid_cells_report_source_location(tmp_path, rule_row, column, value) -> None:
    """Reject malformed definitions with enough context to fix the CSV.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Valid row used as a baseline.
        column: Column to invalidate.
        value: Invalid cell value.
    """
    path = _write_rules(tmp_path / "rules.csv", [dict(rule_row, **{column: value})], list(rule_row))
    with pytest.raises(InvalidRuleError, match=column) as error:
        RuleLoader().load(path)
    assert "rules.csv: line 2:" in str(error.value)


@pytest.mark.parametrize("enabled", ["TRUE", "FALSE"])
def test_invalid_regex_is_rejected_even_in_disabled_rows(tmp_path, rule_row, enabled) -> None:
    """Validate dormant definitions before they can be enabled in a later run.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Baseline rule definition.
        enabled: Eligibility state for the invalid regex rule.
    """
    row = dict(rule_row, MatchType="regex", MatchValue="[", Enabled=enabled)
    path = _write_rules(tmp_path / "rules.csv", [row], list(row))
    with pytest.raises(InvalidRuleError, match="invalid regex"):
        RuleLoader().load(path)


def test_duplicate_ids_include_disabled_rows(tmp_path, rule_row) -> None:
    """Keep audit identifiers unique across the complete rule file.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Definition duplicated with a disabled state.
    """
    path = _write_rules(tmp_path / "rules.csv", [rule_row, dict(rule_row, Enabled="FALSE")], list(rule_row))
    with pytest.raises(InvalidRuleError, match="Duplicate RuleID"):
        RuleLoader().load(path)


@pytest.mark.parametrize("changed", [
    {"IncludeResidential": "FALSE"}, {"ResidentialType": "Other"},
    {"RezoningRelevant": "FALSE"}, {"ValidationStatus": "review"},
])
def test_enabled_conflicts_use_normalized_conditions(tmp_path, rule_row, changed) -> None:
    """Reject contradictory outcomes even when equivalent conditions differ in case.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: First rule in the conflicting pair.
        changed: Conflicting analytical or audit outcome for the second rule.
    """
    first = dict(rule_row, Field="proposedusedescription")
    second = dict(first, RuleID="HF-002", Field="proposed_use_description", MatchValue=" rowhouse ", **changed)
    path = _write_rules(tmp_path / "rules.csv", [first, second], list(rule_row))
    with pytest.raises(InvalidRuleError, match="Conflicting outcomes"):
        RuleLoader().load(path)


def test_disabled_conflicts_and_distinct_regexes_are_allowed(tmp_path, rule_row) -> None:
    """Avoid treating inactive outcomes or regex escape case as identical conditions.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Valid starting rule.
    """
    rows = [rule_row, dict(rule_row, RuleID="HF-002", Enabled="FALSE", IncludeResidential="FALSE"),
            dict(rule_row, RuleID="HF-003", MatchType="regex", MatchValue=r"\s"),
            dict(rule_row, RuleID="HF-004", MatchType="regex", MatchValue=r"\S", IncludeResidential="FALSE")]
    path = _write_rules(tmp_path / "rules.csv", rows, list(rule_row))
    assert len(RuleLoader().load(path)) == 3


@pytest.mark.parametrize("schema_error", ["missing", "duplicate", "short", "long", "quoting", "empty"])
def test_invalid_csv_structure_is_rejected(tmp_path, rule_row, schema_error) -> None:
    """Reject ambiguous CSV shapes rather than silently shifting or losing cells.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Baseline definition providing the valid schema.
        schema_error: Structural corruption to introduce.
    """
    headers = list(rule_row)
    if schema_error == "missing":
        headers.remove("Notes")
    elif schema_error == "duplicate":
        headers.append("RuleID")
    path = _write_rules(tmp_path / "rules.csv", [rule_row], headers)
    if schema_error in {"short", "long", "quoting"}:
        row = list(rule_row.values())
        body = ",".join(row[:-1] if schema_error == "short" else row + ["extra"])
        if schema_error == "quoting":
            body = '"unterminated'
        path.write_text(",".join(headers) + "\n" + body, encoding="utf-8")
    elif schema_error == "empty":
        path.write_text("", encoding="utf-8")
    with pytest.raises(InvalidRuleError):
        RuleLoader().load(path)


def test_no_enabled_rules_and_missing_files(tmp_path, rule_row) -> None:
    """Distinguish valid empty rule sets from absent input files.

    Args:
        tmp_path: Temporary fixture directory.
        rule_row: Valid definition to disable.
    """
    path = _write_rules(tmp_path / "rules.csv", [], list(rule_row))
    assert RuleLoader().load(path) == []
    _write_rules(path, [dict(rule_row, Enabled="FALSE")], list(rule_row))
    assert RuleLoader().load(path) == []
    with pytest.raises(FileNotFoundError):
        RuleLoader().load(tmp_path / "missing.csv")
