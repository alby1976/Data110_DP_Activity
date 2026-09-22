"""Application-to-decision processing-time features.

This module derives processing durations, validity indicators, and right-censoring flags
without performing input/output.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A deterministic table transformation derives processing duration and validity flags
    without performing I/O.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from __future__ import annotations

from typing import Any
from datetime import date

import pandas as pd


def add_processing_features(
    permits: Any,
    *,
    applied_date_column: str,
    decision_date_column: str,
    minimum_days: int = 0,
    observation_end: date | None = None,
) -> Any:
    """Add ProcessingDays and validity/censoring flags.

    Args:
        permits: DataFrame-like table of permit records.
        applied_date_column: Name of the cleaned application-date column.
        decision_date_column: Name of the cleaned decision-date column.
        minimum_days: Nonnegative minimum duration allowed in summaries.
        observation_end: Optional inclusive observation date supplied by the
            caller. No current date or latest-record date is inferred.

    Returns:
        Copy with nullable integer ProcessingDays and FollowUpDays; Boolean
        HasValidProcessingDays, HasNegativeProcessingDays, IsPending,
        IsRightCensored, ProcessingDateMissing, ProcessingDateInvalid, and
        IsAfterObservationEnd. Signed durations retain negative evidence;
        summaries must filter HasValidProcessingDays. FollowUpDays uses a valid
        decision or, for censored records, the explicit observation end.

    Raises:
        TypeError: Input, field names, threshold, or observation date has the
            wrong type.
        ValueError: Required columns are absent, generated names collide,
            columns are ambiguous, or cleaner invalid flags are malformed.

    Note:
        Dates use source calendar days, preserving timezone wall-clock dates.
        Numeric epochs are invalid; cleaner invalid flags remain authoritative.
        IsPending is an analytical proxy for a valid application with a genuinely
        missing decision, not an official permit status. Malformed decisions
        are not pending. With observation_end, later decisions are censored and
        later applications are excluded from validity/follow-up. Without it,
        missing decisions are provisionally censored but their follow-up is
        unknown. No rows are dropped, inputs changed, or files accessed.
    """
    if not isinstance(permits, pd.DataFrame):
        raise TypeError("permits must be a pandas DataFrame.")
    if not permits.columns.is_unique or any(
        not isinstance(name, str) or not name.strip() for name in permits.columns
    ):
        raise ValueError("Input columns must be unique nonblank strings.")
    for name in (applied_date_column, decision_date_column):
        if not isinstance(name, str) or not name.strip():
            raise TypeError("Date column names must be nonblank strings.")
        if name not in permits:
            raise ValueError(f"Missing date column: {name}")
    if applied_date_column == decision_date_column:
        raise ValueError("Application and decision fields must be distinct.")
    if type(minimum_days) is not int:
        raise TypeError("minimum_days must be an integer.")
    if minimum_days < 0:
        raise ValueError("minimum_days cannot be negative.")
    if observation_end is not None and type(observation_end) is not date:
        raise TypeError("observation_end must be a calendar date or None.")
    outputs = {"ProcessingDays", "FollowUpDays", "HasValidProcessingDays",
               "HasNegativeProcessingDays", "IsPending", "IsRightCensored",
               "ProcessingDateMissing", "ProcessingDateInvalid", "IsAfterObservationEnd"}
    if outputs & set(permits.columns):
        raise ValueError("Processing feature columns would overwrite existing data.")
    applied, applied_missing, applied_invalid = _dates(permits, applied_date_column)
    decision, decision_missing, decision_invalid = _dates(permits, decision_date_column)
    duration = (decision - applied).dt.days.astype("Int64")
    negative = duration.lt(0).fillna(False).astype(bool)
    valid = duration.ge(minimum_days).fillna(False).astype(bool)
    eligible = applied.notna()
    after = pd.Series(False, index=permits.index)
    later_decision = pd.Series(False, index=permits.index)
    if observation_end is not None:
        cutoff = pd.Timestamp(observation_end)
        after = applied.gt(cutoff) | decision.gt(cutoff)
        eligible &= applied.le(cutoff)
        later_decision = decision.gt(cutoff)
        valid &= ~after
    pending = eligible & decision_missing
    censored = eligible & (decision_missing | later_decision)
    follow_up = duration.where(applied.notna() & decision.notna() & ~negative).copy()
    if observation_end is not None:
        follow_up = follow_up.where(eligible)
        follow_up.loc[censored] = (cutoff - applied).dt.days.astype("Int64").loc[censored]
    result = permits.copy(deep=True)
    result["ProcessingDays"] = duration
    result["HasValidProcessingDays"] = valid
    result["HasNegativeProcessingDays"] = negative
    result["IsPending"] = pending
    result["IsRightCensored"] = censored
    result["FollowUpDays"] = follow_up
    result["ProcessingDateMissing"] = applied_missing | decision_missing
    result["ProcessingDateInvalid"] = applied_invalid | decision_invalid
    result["IsAfterObservationEnd"] = after
    return result


def _dates(table: pd.DataFrame, column: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Interpret calendar dates and retain cleaner evidence of invalid values.

    Args:
        table: Input table, which is never modified.
        column: Date field to inspect.

    Returns:
        Parsed dates, genuine-missing mask, and invalid-value mask.

    Raises:
        ValueError: An existing invalid flag contains missing/non-Boolean values.
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
    """Parse ISO or date values without shifting their calendar day.

    Args:
        value: Source date value; numeric epochs are unsupported.

    Returns:
        Midnight Timestamp or NaT for missing/malformed values.
    """
    if not isinstance(value, (str, date)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    return pd.NaT if pd.isna(parsed) else parsed.tz_localize(None).normalize()
