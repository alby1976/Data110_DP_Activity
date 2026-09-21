"""Tests for permit cleaner.

This module verifies the documented contracts and edge cases of the permit cleaner
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

from datetime import date

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from dp_activity.cleaning.permit_cleaner import PermitCleaner


def test_cleaner_maps_columns_trims_text_and_parses_dates() -> None:
    """Verify that cleaner maps columns trims text and parses dates."""
    source = pd.DataFrame(
        {
            "permitnum": [" DP1 "],
            "applieddate": ["2024-08-06T00:00:00.000"],
            "communityname": [" Varsity "],
        }
    )
    cleaner = PermitCleaner(
        {"permitnum": "permit_number", "applieddate": "applied_date", "communityname": "community"},
        ["applied_date"],
    )

    cleaned = cleaner.clean(source)

    assert cleaned.loc[0, "permit_number"] == "DP1"
    assert cleaned.loc[0, "community"] == "Varsity"
    assert pd.api.types.is_datetime64_any_dtype(cleaned["applied_date"])
    assert source.loc[0, "permitnum"] == " DP1 "


def test_cleaning_preserves_evidence_rows_index_and_column_order() -> None:
    """Keep original evidence and duplicate records throughout the filter chain."""
    source = pd.DataFrame({
        "permitnum": [" DP1 ", " DP1 "],
        "category": [" Housing ", ""],
        "description": [" First ", " Second "],
        "landusedistrict": [" R-CG ", " R-CG "],
        "applieddate": ["2024-08-06", "bad"],
        "latitude": ["51.05", "bad"],
    }, index=[10, 10])
    original = source.copy(deep=True)
    cleaner = PermitCleaner({
        "permitnum": "permit_number", "landusedistrict": "land_use_district",
        "applieddate": "applied_date",
    }, ["applied_date"])
    result = cleaner.clean(source)
    normalized = ["permit_number", "category", "description", "land_use_district", "applied_date", "latitude"]
    assert list(result) == normalized + [f"raw_{name}" for name in normalized] + [
        "applied_date_invalid", "latitude_invalid",
    ]
    assert result.index.tolist() == [10, 10]
    assert result["permit_number"].tolist() == ["DP1", "DP1"]
    evidence = result[[f"raw_{name}" for name in normalized]].copy()
    evidence.columns = source.columns
    assert_frame_equal(evidence, original)
    assert_frame_equal(source, original)
    assert_frame_equal(result, cleaner.clean(source))
    result.iloc[0, result.columns.get_loc("description")] = "changed"
    assert_frame_equal(source, original)


def test_text_normalization_handles_mixed_nullable_and_categorical_values() -> None:
    """Normalize strings without converting numbers or structured source cells."""
    source = pd.DataFrame({
        "mixed": [" x ", "\t ", 7, None],
        "nullable": pd.Series([" A ", "", pd.NA, " B "], dtype="string"),
        "category": pd.Categorical([" C ", "", None, " C "]),
        "location": [{"latitude": "51.0"}, None, None, None],
    })
    original = source.copy(deep=True)
    result = PermitCleaner({}, []).clean(source)
    assert result["mixed"].iloc[0] == "x"
    assert pd.isna(result["mixed"].iloc[1])
    assert result["mixed"].iloc[2] == 7
    assert result["nullable"].iloc[0] == "A"
    assert result["nullable"].isna().tolist() == [False, True, True, False]
    assert result["category"].iloc[0] == "C"
    assert result["category"].isna().tolist() == [False, True, True, False]
    assert result["location"].iloc[0] == {"latitude": "51.0"}
    assert_frame_equal(source, original)


def test_date_parsing_keeps_calendar_time_and_flags_only_invalid_values() -> None:
    """Preserve study boundaries and distinguish absent dates from bad evidence."""
    source = pd.DataFrame({"applieddate": [
        "2024-08-05T23:30:00-06:00", "2024-08-06T00:30:00+02:00",
        "2024-02-30", None, "  ", 42, True, date(2024, 2, 29),
        pd.Timestamp("2024-08-06"), "08/06/2024", "9999-01-01",
    ]})
    result = PermitCleaner({"applieddate": "applied_date"}, ["applied_date"]).clean(source)
    assert str(result["applied_date"].dtype) == "datetime64[ns]"
    assert result["applied_date"].iloc[0] == pd.Timestamp("2024-08-05 23:30:00")
    assert result["applied_date"].iloc[1] == pd.Timestamp("2024-08-06 00:30:00")
    assert result["applied_date"].iloc[7] == pd.Timestamp("2024-02-29")
    assert result["applied_date"].iloc[8] == pd.Timestamp("2024-08-06")
    assert result["applied_date_invalid"].tolist() == [
        False, False, True, False, False, True, True, False, False, True, True,
    ]


def test_coordinate_conversion_flags_bad_values_without_range_repair() -> None:
    """Keep missing values and out-of-range evidence distinct from parse failures."""
    source = pd.DataFrame({
        "latitude": [" 51.05 ", "bad", "", None, float("inf"), True, 95],
        "longitude": ["-114.07", "-inf", pd.NA, " ", {}, "0", 0],
    })
    result = PermitCleaner({}, []).clean(source)
    assert str(result["latitude"].dtype) == "float64"
    assert result["latitude"].iloc[0] == pytest.approx(51.05)
    assert result["longitude"].iloc[0] == pytest.approx(-114.07)
    assert result["latitude_invalid"].tolist() == [False, True, False, False, True, True, False]
    assert result["longitude_invalid"].tolist() == [False, True, False, False, True, False, False]
    assert result["latitude"].iloc[6] == 95.0
    assert result["longitude"].iloc[5] == 0.0


def test_empty_frame_retains_typed_dates_and_flags() -> None:
    """Allow empty upstream results to flow through cleaning predictably."""
    source = pd.DataFrame(columns=["applieddate", "latitude"])
    result = PermitCleaner({"applieddate": "applied_date"}, ["applied_date"]).clean(source)
    assert result.empty
    assert str(result["applied_date"].dtype) == "datetime64[ns]"
    assert str(result["latitude"].dtype) == "float64"
    assert result["applied_date_invalid"].dtype == bool
    assert PermitCleaner({}, []).clean(pd.DataFrame()).empty


def test_constructor_copies_configuration_and_ignores_absent_optional_mappings() -> None:
    """Prevent caller configuration changes from silently changing the filter."""
    mapping = {"applieddate": "applied_date", "missing_optional": "optional"}
    dates = ["applied_date", "applied_date"]
    cleaner = PermitCleaner(mapping, dates)
    mapping["applieddate"] = "changed"
    dates.clear()
    result = cleaner.clean(pd.DataFrame({"applieddate": ["2024-01-01"]}))
    assert "applied_date" in result
    assert "optional" not in result
    assert result.columns.tolist().count("applied_date_invalid") == 1


@pytest.mark.parametrize("mapping,dates,error", [
    ([], [], TypeError), ({"a": ""}, [], TypeError), ({1: "a"}, [], TypeError),
    ({"a": "x", "b": "x"}, [], ValueError), ({}, "date", TypeError),
    ({}, [1], TypeError),
])
def test_invalid_configuration_is_rejected(mapping, dates, error) -> None:
    """Fail ambiguous configuration before accepting source data.

    Args:
        mapping: Invalid column mapping or a mapping paired with invalid dates.
        dates: Requested date fields.
        error: Expected exception type.
    """
    with pytest.raises(error):
        PermitCleaner(mapping, dates)


@pytest.mark.parametrize("source,mapping,dates,error", [
    ([], {}, [], TypeError),
    (pd.DataFrame([[1, 2]], columns=["a", "a"]), {}, [], ValueError),
    (pd.DataFrame({1: [1]}), {}, [], TypeError),
    (pd.DataFrame({"a": [1], "b": [2]}), {"a": "b"}, [], ValueError),
    (pd.DataFrame({"category": ["A"]}), {}, ["applied_date"], ValueError),
    (pd.DataFrame({"category": ["A"], "raw_category": ["B"]}), {}, [], ValueError),
    (pd.DataFrame({"applied_date": [None], "applied_date_invalid": [False]}), {}, ["applied_date"], ValueError),
    (pd.DataFrame({"latitude": [1]}), {}, ["latitude"], ValueError),
])
def test_invalid_inputs_cannot_overwrite_evidence(source, mapping, dates, error) -> None:
    """Reject schema conflicts rather than silently replacing source evidence.

    Args:
        source: Invalid input or input with conflicting column names.
        mapping: Column-name translation under test.
        dates: Configured date fields.
        error: Expected exception type.
    """
    with pytest.raises(error):
        PermitCleaner(mapping, dates).clean(source)
