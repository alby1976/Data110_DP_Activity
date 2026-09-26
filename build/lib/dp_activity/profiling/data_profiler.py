"""Create evidence needed before finalizing cleaning and rules.

This module produces evidence tables used to evaluate source structure and refine later
cleaning and classification rules.

Design Pattern:
    Pipes and Filters.

Pattern Rationale:
    Profiling is a read-only pipeline stage that transforms source records into named
    evidence tables without owning persistence.

Typical Usage:
    Pass a raw or cleaned DataFrame to DataProfiler.profile(), then pass its
    named evidence tables to OutputRepository. No network or filesystem access
    occurs during profiling.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype


_TABLE_NAMES = frozenset({
    "summary", "dtypes", "missingness", "permit_uniqueness",
    "duplicate_examples", "date_ranges", "description_examples",
})
_EXAMPLE_LIMIT = 20


class DataProfiler:
    """Profile source structure and important data distributions.

    This class is a read-only Pipes-and-Filters stage that returns evidence tables
    without owning their persistence.
    """

    def profile(self, permits: Any, categorical_columns: list[str]) -> dict[str, Any]:
        """Return named tidy profile tables.

        Args:
            permits: pandas DataFrame with unique string column names. Both raw
                Socrata names and normalized project names are supported.
            categorical_columns: Existing columns with scalar, hashable values
                to count. Repeated names are counted once.

        Returns:
            Names mapped to independent DataFrames: summary (row_count,
            column_count), dtypes (column, dtype), missingness (column,
            missing_count, missing_percentage), permit_uniqueness (column,
            non_missing_count, unique_count, duplicate_row_count,
            duplicate_excess_count), duplicate_examples (column, row_position,
            permit_number), date_ranges (column, valid_count, missing_count,
            invalid_count, min_date, max_date), and description_examples
            (column, row_position, description, character_count). Each requested
            categorical column also names a table with value, count, percentage.

        Raises:
            TypeError: Input is not a DataFrame, column names are not strings,
                categorical_columns is not a list of strings, or selected
                categorical values cannot be counted.
            ValueError: Columns are duplicated, a requested column is absent,
                or its name conflicts with a standard report name.

        Note:
            Percentages use all input rows as the denominator and range from
            zero to 100; empty inputs produce zero missing percentages. Only
            pandas nulls are missing: blank strings remain source evidence.
            PermitNum, permitnum, and permit_number are recognized as identifier
            columns. Duplicate rows count all members of repeated non-null IDs;
            excess counts exclude each ID's first occurrence. Examples use
            zero-based row positions, independent of DataFrame index labels.

            Datetime-typed columns and names ending in "date" after removing
            underscores are profiled as dates. Parseable strings and date objects
            are converted to UTC for comparison; naive dates are treated as UTC
            only for this report. Non-null unparseable values, including numbers
            and blanks, count as invalid. Date interpretation never changes input.

            Duplicate examples are capped at 20 per identifier column. Description
            columns (names ending in "description") contribute their 20 longest
            nonblank strings each, with ties in source order. Categorical counts
            sort by descending frequency, with ties in first-occurrence order.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Permit columns must be unique.")
        if any(not isinstance(column, str) for column in permits.columns):
            raise TypeError("Permit column names must be strings.")
        if not isinstance(categorical_columns, list) or any(
            not isinstance(column, str) for column in categorical_columns
        ):
            raise TypeError("categorical_columns must be a list of strings.")
        for column in categorical_columns:
            if column not in permits.columns:
                raise ValueError(f"Requested categorical column is missing: {column}")
            if column in _TABLE_NAMES:
                raise ValueError(f"Categorical column conflicts with a report name: {column}")

        row_count = len(permits)
        missing = permits.isna().sum()
        reports = {
            "summary": pd.DataFrame([{
                "row_count": row_count, "column_count": len(permits.columns),
            }]),
            "dtypes": pd.DataFrame({
                "column": list(permits.columns),
                "dtype": [str(dtype) for dtype in permits.dtypes],
            }),
            "missingness": pd.DataFrame({
                "column": list(permits.columns),
                "missing_count": missing.to_numpy(copy=True),
                "missing_percentage": (
                    missing.to_numpy(copy=True) * 100 / row_count
                    if row_count else [0.0] * len(permits.columns)
                ),
            }),
        }
        reports["permit_uniqueness"], reports["duplicate_examples"] = _profile_identifiers(permits)
        reports["date_ranges"] = _profile_dates(permits)
        reports["description_examples"] = _profile_descriptions(permits)
        for column in dict.fromkeys(categorical_columns):
            values = permits[column].astype(object).where(permits[column].notna(), pd.NA)
            try:
                for value in values:
                    hash(value)
                counts = values.value_counts(dropna=False, sort=False)
            except TypeError as exc:
                raise TypeError(f"Categorical column '{column}' must contain hashable values.") from exc
            counts = counts.sort_values(ascending=False, kind="stable")
            reports[column] = pd.DataFrame({
                "value": counts.index.to_list(),
                "count": counts.to_numpy(copy=True),
                "percentage": counts.to_numpy(copy=True) * 100 / row_count if row_count else [],
            })
        return reports


def _profile_identifiers(permits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Measure identifier duplication without counting missing IDs as duplicates.

    Args:
        permits: Source table whose identifier values remain unchanged.

    Returns:
        Per-column uniqueness counts and bounded duplicate row examples.
    """
    summaries = []
    examples = []
    for column in permits.columns:
        if column.lower().replace("_", "") not in {"permitnum", "permitnumber"}:
            continue
        values = permits[column].reset_index(drop=True)
        present = values.dropna()
        duplicated = values.notna() & values.duplicated(keep=False)
        summaries.append({
            "column": column, "non_missing_count": len(present),
            "unique_count": present.nunique(), "duplicate_row_count": int(duplicated.sum()),
            "duplicate_excess_count": int(present.duplicated().sum()),
        })
        for position in values.index[duplicated][:_EXAMPLE_LIMIT]:
            examples.append({
                "column": column, "row_position": position, "permit_number": values.iloc[position],
            })
    return (
        pd.DataFrame(summaries, columns=[
            "column", "non_missing_count", "unique_count", "duplicate_row_count",
            "duplicate_excess_count",
        ]),
        pd.DataFrame(examples, columns=["column", "row_position", "permit_number"]),
    )


def _profile_dates(permits: pd.DataFrame) -> pd.DataFrame:
    """Compare source date coverage while separating missing and invalid values.

    Args:
        permits: Raw or cleaned table to inspect without modifying its date fields.

    Returns:
        Counts and UTC bounds for each recognized date column; NaT for absent bounds.
    """
    rows = []
    for column in permits.columns:
        values = permits[column]
        if not (
            column.lower().replace("_", "").endswith("date")
            or is_datetime64_any_dtype(values.dtype)
        ):
            continue
        eligible = values.map(lambda value: isinstance(value, (str, date)))
        parsed = pd.to_datetime(values.where(eligible), format="mixed", errors="coerce", utc=True)
        rows.append({
            "column": column, "valid_count": int(parsed.notna().sum()),
            "missing_count": int(values.isna().sum()),
            "invalid_count": int((values.notna() & parsed.isna()).sum()),
            "min_date": parsed.min(), "max_date": parsed.max(),
        })
    return pd.DataFrame(rows, columns=[
        "column", "valid_count", "missing_count", "invalid_count", "min_date", "max_date",
    ])


def _profile_descriptions(permits: pd.DataFrame) -> pd.DataFrame:
    """Select longest source descriptions for bounded manual rule review.

    Args:
        permits: Source table containing optional description fields.

    Returns:
        Up to 20 nonblank descriptions per field, retaining original text and positions.
    """
    examples = []
    for column in permits.columns:
        if not column.lower().replace("_", "").endswith("description"):
            continue
        candidates = [
            {"column": column, "row_position": position,
             "description": value, "character_count": len(value)}
            for position, value in enumerate(permits[column])
            if isinstance(value, str) and value.strip()
        ]
        candidates.sort(key=lambda item: -item["character_count"])
        examples.extend(candidates[:_EXAMPLE_LIMIT])
    return pd.DataFrame(examples, columns=[
        "column", "row_position", "description", "character_count",
    ])
