"""Policy-period features based on the configured primary date.

This module assigns policy periods and boundary-audit fields from the configured primary
date.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A side-effect-free transformation adds period fields to a table, making the rule
    deterministic, composable, and easy to test at boundaries.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from __future__ import annotations

from typing import Any
from datetime import date, datetime

import pandas as pd

from dp_activity.config import StudyPeriod

_OUTSIDE = "Outside Study Window"


def add_period_features(
    permits: Any,
    *,
    date_column: str,
    periods: list[Any],
    decision_date_column: str | None = "decision_date",
) -> Any:
    """Add Period and policy-boundary audit fields.

    Args:
        permits: DataFrame-like table of permit records.
        date_column: Name of the cleaned date column used to derive features.
        periods: Ordered, non-overlapping policy-period definitions.
            Inclusive endpoints use source calendar dates. Only the final
            period may be open-ended; gaps are allowed.
        decision_date_column: Optional decision field for boundary auditing.
            If absent or None, decision-derived values remain unknown.

    Returns:
        A copy with ordered categorical ``Period`` and ``DecisionPeriod``;
        nullable integer ``PeriodSortKey`` (configured periods numbered from
        one, outside numbered zero); Boolean ``PeriodDateMissing`` and
        ``PeriodDateInvalid``; and nullable Boolean ``CrossesPeriodBoundary``.
        Missing/invalid dates have no assigned period, rather than being placed
        outside the study. Crossing is true only when a nonnegative application-
        to-decision interval spans a configured period start or exclusive end.

    Raises:
        TypeError: Input, column arguments, or period definitions have wrong types.
        ValueError: Required columns are absent, names collide, periods are
            unordered/overlapping, labels repeat, or invalid flags are malformed.

    Note:
        This functional filter has no I/O or clock dependency. It preserves
        every input row and its index. ISO strings and date objects are accepted;
        offsets retain wall-clock dates. Numeric epochs are invalid. Existing
        cleaner ``<column>_invalid`` flags take precedence over parsed values.
        A decision preceding the application leaves crossing unknown.
    """
    if not isinstance(permits, pd.DataFrame):
        raise TypeError("permits must be a pandas DataFrame.")
    for name in (date_column, decision_date_column):
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise TypeError("Date column names must be nonblank strings.")
    if date_column is None or date_column not in permits:
        raise ValueError("The primary date column is required.")
    if not permits.columns.is_unique or any(
        not isinstance(name, str) or not name.strip() for name in permits.columns
    ):
        raise ValueError("Input columns must have unique nonblank string names.")
    outputs = {"Period", "DecisionPeriod", "PeriodSortKey", "PeriodDateMissing",
               "PeriodDateInvalid", "CrossesPeriodBoundary"}
    if outputs & set(permits.columns):
        raise ValueError("Period feature columns would overwrite existing data.")
    if not isinstance(periods, list) or any(not isinstance(p, StudyPeriod) for p in periods):
        raise TypeError("periods must be a list of StudyPeriod objects.")
    if not periods:
        raise ValueError("At least one study period is required.")
    labels = [p.name for p in periods]
    if any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("Period labels must be nonblank strings.")
    if len(set(labels)) != len(labels) or _OUTSIDE in labels:
        raise ValueError("Period labels must be unique and not use the outside label.")
    bounds = []
    for index, period in enumerate(periods):
        if type(period.start) is not date or (period.end is not None and type(period.end) is not date):
            raise TypeError("Period endpoints must be calendar dates.")
        start = pd.Timestamp(period.start)
        end = pd.Timestamp(period.end) if period.end is not None else None
        if end is not None and end < start:
            raise ValueError("Period end must not precede its start.")
        if index and (bounds[-1][1] is None or start <= bounds[-1][1]):
            raise ValueError("Periods must be ordered and non-overlapping.")
        bounds.append((start, end))

    applied, missing, invalid = _dates(permits, date_column)
    decision = pd.Series(pd.NaT, index=permits.index, dtype="datetime64[ns]")
    if decision_date_column is not None and decision_date_column in permits:
        decision, _, _ = _dates(permits, decision_date_column)
    result = permits.copy(deep=True)
    categories = [_OUTSIDE, *labels]
    for name, dates in (("Period", applied), ("DecisionPeriod", decision)):
        assigned = pd.Series(pd.NA, index=permits.index, dtype="string")
        assigned.loc[dates.notna()] = _OUTSIDE
        for label, (start, end) in zip(labels, bounds):
            mask = dates.ge(start)
            if end is not None:
                mask &= dates.le(end)
            assigned.loc[mask] = label
        result[name] = pd.Categorical(assigned, categories=categories, ordered=True)
    sort_keys = {label: index for index, label in enumerate(categories)}
    result["PeriodSortKey"] = result["Period"].astype("string").map(sort_keys).astype("Int64")
    result["PeriodDateMissing"] = missing
    result["PeriodDateInvalid"] = invalid
    eligible = applied.notna() & decision.notna() & decision.ge(applied)
    crossing = pd.Series(pd.NA, index=permits.index, dtype="boolean")
    crossing.loc[eligible] = False
    for start, end in bounds:
        boundaries = [start] + ([end + pd.Timedelta(1, unit="D")] if end is not None else [])
        for boundary in boundaries:
            crossing.loc[eligible & applied.lt(boundary) & decision.ge(boundary)] = True
    result["CrossesPeriodBoundary"] = crossing
    return result


def _dates(table: pd.DataFrame, column: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Separate missing and invalid dates while honoring cleaner evidence.

    Args:
        table: Input table whose values must remain unchanged.
        column: Date field to interpret.

    Returns:
        Calendar dates, genuine-missing mask, and invalid-value mask.

    Raises:
        ValueError: An existing invalid flag is not a nonmissing Boolean column.
    """
    values = table[column]
    missing = values.isna() | values.map(lambda v: isinstance(v, str) and not v.strip())
    parsed = values.map(_calendar_date).astype("datetime64[ns]")
    invalid = ~missing & parsed.isna()
    flag = f"{column}_invalid"
    if flag in table:
        if not pd.api.types.is_bool_dtype(table[flag]) or table[flag].isna().any():
            raise ValueError(f"{flag} must contain nonmissing Booleans.")
        invalid |= table[flag]
    return parsed.mask(invalid), missing & ~invalid, invalid


def _calendar_date(value: Any) -> Any:
    """Interpret an ISO value without shifting its calendar day.

    Args:
        value: Source ISO string or date object.

    Returns:
        Midnight Timestamp, or NaT for unsupported/malformed values.
    """
    if not isinstance(value, (str, date, datetime)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    return pd.NaT if pd.isna(parsed) else parsed.tz_localize(None).normalize()
