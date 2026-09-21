"""Deterministic cleaning for City development-permit records.

This module standardizes raw City fields and dates while preserving source evidence and
questionable records for review.

Design Pattern:
    Pipes and Filters.

Pattern Rationale:
    The cleaner is a deterministic filter in the larger analysis pipeline. Its
    ordered normalization, text, date, and coordinate steps pass one copied table
    forward without I/O, classification, or record removal. This isolates data
    preparation from later validation and analytical decisions.

Typical Usage:
    Apply these components to a raw snapshot before classification and feature
    derivation.
"""

from __future__ import annotations

from datetime import date
import math
from typing import Any

import pandas as pd


class PermitCleaner:
    """Standardize source permit data without classifying it.

    This class is a deterministic Pipes-and-Filters stage that preserves source
    evidence while applying configured column and date normalization.

    Attributes:
        column_map: Source column names mapped to project-standard names.
        date_columns: Standardized columns that must be parsed as dates.
    """

    def __init__(self, column_map: dict[str, str], date_columns: list[str]) -> None:
        """Configure explicit source mappings and date fields for the filter.

        Args:
            column_map: Source names mapped to unique normalized names. Unmapped
                input columns keep their names; absent source names are ignored.
            date_columns: Normalized date fields required in each input table.

        Raises:
            TypeError: Mapping entries or date-column names are not nonblank strings.
            ValueError: Multiple source names map to the same target name.
        """
        if not isinstance(column_map, dict) or any(
            not isinstance(name, str) or not name.strip()
            for pair in column_map.items() for name in pair
        ):
            raise TypeError("column_map must map nonblank string names to string names.")
        if len(set(column_map.values())) != len(column_map):
            raise ValueError("column_map target names must be unique.")
        if not isinstance(date_columns, list) or any(
            not isinstance(name, str) or not name.strip() for name in date_columns
        ):
            raise TypeError("date_columns must be a list of nonblank strings.")
        self.column_map = dict(column_map)
        self.date_columns = list(dict.fromkeys(date_columns))

    def clean(self, permits: Any) -> Any:
        """Return a cleaned copy and preserve traceability to source values.

        Args:
            permits: pandas DataFrame with unique, nonblank string column names.

        Returns:
            A new DataFrame with the original row order and index. Columns appear
            in source order after renaming, followed by raw_<name> evidence
            columns in the same order, configured <date>_invalid flags, and
            latitude_invalid/longitude_invalid flags for available coordinates.

        Raises:
            TypeError: permits is not a DataFrame or column names are invalid.
            ValueError: Renaming or generated evidence/flag names would collide,
                input columns are duplicated, or a configured date column is absent.

        Note:
            String cells are stripped and blanks become pd.NA. Other source
            values remain unchanged unless they are configured dates or numeric
            coordinates. Raw evidence preserves the original values and types.

            Dates accept ISO-8601 strings and Python/pandas date objects. Invalid
            nonmissing values become NaT with an invalid flag; missing values
            and blanks are not flagged. Parsed dates are timezone-naive and keep
            the source wall-clock time, even when an explicit offset was supplied.
            This supports calendar-date comparisons without shifting study days.

            Coordinates become float64; unparseable values, booleans, and infinity
            become NaN and are flagged. Geographic range checks belong to later
            validation. Duplicates and invalid records are retained. This filter
            expects source data; passing an already-cleaned result is rejected
            when its evidence columns collide.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input column names must be unique.")
        if any(not isinstance(name, str) or not name.strip() for name in permits.columns):
            raise TypeError("Input column names must be nonblank strings.")
        normalized = [self.column_map.get(name, name) for name in permits.columns]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Column mapping would overwrite an existing column.")
        missing_dates = [name for name in self.date_columns if name not in normalized]
        if missing_dates:
            raise ValueError(f"Configured date columns are missing: {missing_dates}")
        coordinates = [name for name in ("latitude", "longitude") if name in normalized]
        if set(coordinates) & set(self.date_columns):
            raise ValueError("Coordinate columns cannot also be configured as dates.")
        evidence_names = [f"raw_{name}" for name in normalized]
        flag_names = [f"{name}_invalid" for name in self.date_columns + coordinates]
        all_names = normalized + evidence_names + flag_names
        if len(set(all_names)) != len(all_names):
            raise ValueError("Generated evidence or invalid-flag names would overwrite a column.")

        cleaned = permits.rename(columns=self.column_map).copy(deep=True)
        evidence = cleaned.copy(deep=True)
        evidence.columns = evidence_names
        cleaned = _normalize_text(cleaned)
        cleaned = pd.concat([cleaned, evidence], axis=1)
        cleaned = _parse_dates(cleaned, self.date_columns)
        cleaned = _parse_coordinates(cleaned, coordinates)
        return cleaned


def _normalize_text(permits: pd.DataFrame) -> pd.DataFrame:
    """Trim string cells on the working copy without coercing other source types.

    Args:
        permits: Private working table passed from the normalization step.

    Returns:
        The working table with stripped text and blanks represented as pd.NA.
    """
    for column in permits.columns:
        values = permits[column]
        if values.map(lambda value: isinstance(value, str)).any():
            permits[column] = values.astype(object).map(
                lambda value: (value.strip() or pd.NA) if isinstance(value, str) else value
            )
    return permits


def _parse_dates(permits: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Parse configured dates and distinguish invalid values from missing values.

    Args:
        permits: Working table after text normalization and evidence preservation.
        columns: Normalized date names selected by configuration.

    Returns:
        Working table with naive datetime64 columns and Boolean invalid flags.
    """
    for column in columns:
        values = permits[column]
        parsed = values.map(_parse_calendar_date).astype("datetime64[ns]")
        permits[column] = parsed
        permits[f"{column}_invalid"] = values.notna() & parsed.isna()
    return permits


def _parse_calendar_date(value: Any) -> Any:
    """Parse one source date without changing its calendar day.

    Args:
        value: ISO string, date object, or malformed/missing source value.

    Returns:
        A timezone-naive Timestamp, or NaT for unsupported or unparseable values.
    """
    if not isinstance(value, (str, date)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    if pd.isna(parsed):
        return pd.NaT
    return parsed.tz_localize(None)


def _parse_coordinates(permits: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert available coordinate fields without inventing replacement values.

    Args:
        permits: Working table after date parsing.
        columns: Available latitude and longitude column names.

    Returns:
        Working table with float coordinates and Boolean invalid flags.
    """
    for column in columns:
        values = permits[column]
        parsed = values.map(_parse_coordinate).astype("float64")
        permits[column] = parsed
        permits[f"{column}_invalid"] = values.notna() & parsed.isna()
    return permits


def _parse_coordinate(value: Any) -> float:
    """Convert a scalar coordinate to a finite number or NaN.

    Args:
        value: Numeric value, numeric text, or missing/malformed source value.

    Returns:
        Finite floating-point coordinate or NaN when conversion is inappropriate.
    """
    if isinstance(value, bool):
        return float("nan")
    try:
        coordinate = float(value)
    except (TypeError, ValueError, OverflowError):
        return float("nan")
    return coordinate if math.isfinite(coordinate) else float("nan")
