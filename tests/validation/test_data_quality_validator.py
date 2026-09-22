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
import pytest
from dataclasses import FrozenInstanceError
from functools import partial
from pandas.testing import assert_frame_equal

from dp_activity.validation.data_quality_validator import DataQualityValidator, QualityCheckResult


def test_duplicate_permit_numbers_are_reported() -> None:
    """Verify that duplicate permit numbers are reported."""
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP1"],
            "applied_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        }
    )

    results = DataQualityValidator().validate(permits, {})

    duplicate_check = next(item for item in results if "duplicate" in item.check_name.lower())
    assert duplicate_check.affected_rows == 2
    assert duplicate_check.status.lower() in {"warn", "fail"}


def _valid_table() -> pd.DataFrame:
    """Build a small permit table covering all default check prerequisites.

    Returns:
        Two valid records with a nondefault index and boundary coordinates.
    """
    return pd.DataFrame({
        "permit_number": ["DP1", "DP2"],
        "applied_date": ["2024-01-01", "2024-01-02"],
        "decision_date": ["2024-01-01", "2024-01-03"],
        "community": ["A", "B"],
        "latitude": [0, 90], "longitude": [0, -180],
    }, index=[7, 7])


def test_valid_data_passes_without_mutation() -> None:
    """Support injected strategy calls and preserve even duplicated row indexes."""
    table = _valid_table()
    before = table.copy(deep=True)
    validate = partial(DataQualityValidator().validate, settings={})
    results = validate(table)
    assert results and all(result.status == "pass" for result in results)
    assert_frame_equal(table, before)


def test_missing_identifiers_are_not_duplicate_groups() -> None:
    """Count blank/null identifiers separately from repeated actual identifiers."""
    table = pd.DataFrame({"permit_number": [None, None, " ", "DP1", "DP1", "DP2"]})
    results = {r.check_name: r for r in DataQualityValidator().validate(table, {})}
    assert results["missing_permit_number"].affected_rows == 3
    assert results["duplicate_permit_number"].affected_rows == 2
    assert results["duplicate_permit_number"].status == "fail"
    relaxed = {r.check_name: r for r in DataQualityValidator().validate(
        table, {"require_unique_permit_number": False},
    )}
    assert relaxed["duplicate_permit_number"].status == "warn"


def test_invalid_dates_missing_decisions_and_negative_durations() -> None:
    """Keep invalid evidence separate from pending decisions and negative intervals."""
    table = pd.DataFrame({
        "applied_date": ["2024-01-03", "bad", None, "2024-01-03", "2024-01-03"],
        "decision_date": ["2024-01-02", "2024-01-04", None, None, " "],
        "decision_date_invalid": [False, False, False, True, False],
    })
    results = {r.check_name: r for r in DataQualityValidator().validate(table, {})}
    assert results["invalid_applied_date"].affected_rows == 1
    assert results["missing_applied_date"].affected_rows == 1
    assert results["invalid_decision_date"].affected_rows == 1
    assert results["missing_decision_date"].affected_rows == 2
    assert results["negative_processing_days"].affected_rows == 1


def test_numeric_dates_are_invalid_and_offsets_keep_calendar_time() -> None:
    """Reject numeric epochs and avoid shifting application days across offsets."""
    table = pd.DataFrame({
        "applied_date": [20240101, "2024-01-01T23:00:00-07:00"],
        "decision_date": [None, "2024-01-02T01:00:00+00:00"],
    })
    results = {r.check_name: r for r in DataQualityValidator().validate(table, {})}
    assert results["invalid_applied_date"].affected_rows == 1
    assert results["negative_processing_days"].affected_rows == 0


def test_geography_counts_rows_once_and_preserves_invalid_flags() -> None:
    """Distinguish absent coordinates from invalid values replaced by cleaning."""
    table = pd.DataFrame({
        "community": [" ", None, "A", "B", "C", "D"],
        "latitude": [None, 91, float("inf"), True, 0, None],
        "longitude": [None, 181, "bad", 0, 0, 0],
        "latitude_invalid": [False, False, False, False, False, True],
    })
    results = {r.check_name: r for r in DataQualityValidator().validate(table, {})}
    assert results["missing_community"].affected_rows == 2
    assert results["missing_coordinates"].affected_rows == 1
    assert results["invalid_coordinates"].affected_rows == 4


def test_warning_options_disable_only_their_checks() -> None:
    """Do not require optional geography when its checks are disabled."""
    table = _valid_table().drop(columns=["community", "latitude", "longitude"])
    results = DataQualityValidator().validate(table, {
        "warn_on_missing_community": False,
        "warn_on_missing_coordinates": False,
        "warn_on_negative_processing_days": False,
    })
    assert all(r.status == "pass" for r in results)
    assert not any("coordinates" in r.check_name or "negative" in r.check_name for r in results)


def test_missing_columns_fail_instead_of_silently_passing() -> None:
    """Report unavailable prerequisites without assigning invented affected counts."""
    results = DataQualityValidator().validate(pd.DataFrame(), {})
    assert results and all(r.status == "fail" and r.affected_rows == 0 for r in results)


@pytest.mark.parametrize("reference,status", [("2024-01-04", "pass"), ("2024-01-05", "warn")])
def test_freshness_boundary_uses_explicit_reference(reference: str, status: str) -> None:
    """Make snapshot freshness deterministic and inclusive of the age limit."""
    results = {r.check_name: r for r in DataQualityValidator().validate(_valid_table(), {
        "max_data_age_days": 2, "reference_date": reference, "minimum_row_count": 2,
    })}
    assert results["data_freshness"].status == status
    assert results["minimum_row_count"].status == "pass"


def test_empty_snapshot_cannot_pass_configured_size_and_freshness() -> None:
    """Report failures for empty data even though zero records are affected."""
    results = {r.check_name: r for r in DataQualityValidator().validate(_valid_table().iloc[:0], {
        "minimum_row_count": 1, "max_data_age_days": 7, "reference_date": "2024-01-03",
    })}
    assert results["minimum_row_count"].status == "fail"
    assert results["data_freshness"].status == "fail"


@pytest.mark.parametrize("settings,exception", [
    ({"require_unique_permit_number": "false"}, TypeError),
    ({"minimum_row_count": True}, TypeError),
    ({"max_data_age_days": 1.5}, TypeError),
    ({"minimum_row_count": -1}, ValueError),
    ({"max_data_age_days": 2}, ValueError),
    ({"max_data_age_days": 2, "reference_date": "bad"}, ValueError),
])
def test_invalid_options_raise(settings: dict, exception: type[Exception]) -> None:
    """Reject ambiguous configuration before performing any checks."""
    with pytest.raises(exception):
        DataQualityValidator().validate(_valid_table(), settings)


def test_malformed_inputs_and_flags_raise() -> None:
    """Reject unsupported structures and truthy strings masquerading as flags."""
    with pytest.raises(TypeError):
        DataQualityValidator().validate([], {})
    with pytest.raises(TypeError):
        DataQualityValidator().validate(_valid_table(), None)
    with pytest.raises(ValueError):
        DataQualityValidator().validate(pd.DataFrame(columns=["a", "a"]), {})
    table = _valid_table()
    table["applied_date_invalid"] = "False"
    with pytest.raises(ValueError):
        DataQualityValidator().validate(table, {})


def test_quality_result_is_immutable() -> None:
    """Keep recorded findings stable for downstream reporting."""
    result = QualityCheckResult("example", "pass", 0, "No findings.")
    with pytest.raises(FrozenInstanceError):
        result.status = "fail"
