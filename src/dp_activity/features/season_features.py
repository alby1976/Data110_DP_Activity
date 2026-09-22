"""Meteorological season fields, including cross-year winters.

This module derives meteorological seasons, including winters that cross calendar years
and season-completeness flags.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A pure transformation owns the cross-year season algorithm so it composes cleanly
    with other feature stages.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from __future__ import annotations

from typing import Any
from datetime import date

import pandas as pd

from dp_activity.config import StudyPeriod


def add_season_features(
    permits: Any,
    *,
    date_column: str,
    season_months: dict[str, list[int]],
    analysis_windows: list[Any],
    observation_end: date | None = None,
) -> Any:
    """Add season name, start date, label, sort key, and completeness flag.

    Args:
        permits: DataFrame-like table of permit records.
        date_column: Name of the cleaned date column used to derive features.
        season_months: Labels mapped to three consecutive months in seasonal
            order (for example, Winter: [12, 1, 2]). All months must occur once.
        analysis_windows: Ordered, non-overlapping inclusive StudyPeriod values.
            An empty list permits season assignment but leaves completeness unknown.
        observation_end: Optional inclusive snapshot observation date. Caps closed
            windows and supplies an upper bound for an open-ended window.

    Returns:
        A copy with string Season and SeasonLabel, datetime SeasonStartDate and
        SeasonEndDate, nullable integer SeasonSortKey (YYYYMM), and nullable
        Boolean IsCompleteSeason and IsPartialSeason. Missing/invalid dates have
        null features. Dates outside supplied windows have unknown completeness.
        A season is complete only if it fits within the individual policy window
        containing the record, capped by observation_end when supplied.

    Raises:
        TypeError: Arguments have unsupported types.
        ValueError: Columns collide, season months do not partition the year,
            windows overlap, or cleaner invalid flags are malformed.

    Note:
        This deterministic filter preserves rows, index, and source fields and
        performs no I/O. ISO dates retain their wall-clock calendar day. Cleaner
        invalid flags take precedence. An unbounded season's completeness is
        unknown unless its start already precedes its policy window, proving
        partial exposure. No current-date or latest-record assumption is made.
    """
    if not isinstance(permits, pd.DataFrame):
        raise TypeError("permits must be a pandas DataFrame.")
    if not isinstance(date_column, str) or not date_column.strip():
        raise TypeError("date_column must be a nonblank string.")
    if not permits.columns.is_unique or any(
        not isinstance(name, str) or not name.strip() for name in permits.columns
    ):
        raise ValueError("Input column names must be unique nonblank strings.")
    if date_column not in permits:
        raise ValueError(f"Missing date column: {date_column}")
    output_names = {"Season", "SeasonLabel", "SeasonStartDate", "SeasonEndDate",
                    "SeasonSortKey", "IsCompleteSeason", "IsPartialSeason"}
    if output_names & set(permits.columns):
        raise ValueError("Season features would overwrite existing columns.")
    if not isinstance(season_months, dict):
        raise TypeError("season_months must be a dictionary.")
    month_map = {}
    for label, months in season_months.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Season labels must be nonblank strings.")
        if not isinstance(months, list) or len(months) != 3:
            raise ValueError("Each season must contain three ordered months.")
        if any(type(month) is not int or not 1 <= month <= 12 for month in months):
            raise ValueError("Months must be integers from 1 through 12.")
        if months != [((months[0] - 1 + offset) % 12) + 1 for offset in range(3)]:
            raise ValueError("Season months must be consecutive in seasonal order.")
        for month in months:
            if month in month_map:
                raise ValueError("Each month must belong to exactly one season.")
            month_map[month] = (label, months[0])
    if set(month_map) != set(range(1, 13)):
        raise ValueError("Season definitions must cover all twelve months.")
    if not isinstance(analysis_windows, list) or any(
        not isinstance(window, StudyPeriod) for window in analysis_windows
    ):
        raise TypeError("analysis_windows must be a list of StudyPeriod objects.")
    if observation_end is not None and type(observation_end) is not date:
        raise TypeError("observation_end must be a calendar date or None.")
    cutoff = pd.Timestamp(observation_end) if observation_end is not None else None
    bounds = []
    for window in analysis_windows:
        if type(window.start) is not date or (window.end is not None and type(window.end) is not date):
            raise TypeError("Study endpoints must be calendar dates.")
        start = pd.Timestamp(window.start)
        end = pd.Timestamp(window.end) if window.end is not None else None
        if end is not None and end < start:
            raise ValueError("Study window ends before it starts.")
        if bounds and (bounds[-1][1] is None or start <= bounds[-1][1]):
            raise ValueError("Study windows must be ordered and non-overlapping.")
        bounds.append((start, end))

    dates = permits[date_column].map(_calendar_date).astype("datetime64[ns]")
    flag = f"{date_column}_invalid"
    if flag in permits:
        if not pd.api.types.is_bool_dtype(permits[flag]) or permits[flag].isna().any():
            raise ValueError(f"{flag} must contain nonmissing Booleans.")
        dates = dates.mask(permits[flag])
    values: dict[str, list[Any]] = {name: [] for name in output_names}
    for timestamp in dates:
        row = dict.fromkeys(output_names, pd.NA)
        row["SeasonStartDate"] = row["SeasonEndDate"] = pd.NaT
        if pd.notna(timestamp):
            label, start_month = month_map[timestamp.month]
            year = timestamp.year - int(timestamp.month < start_month)
            start = pd.Timestamp(year=year, month=start_month, day=1)
            end = start + pd.DateOffset(months=3) - pd.Timedelta(1, unit="D")
            year_label = str(year) if end.year == year else f"{year}–{end.year % 100:02d}"
            row.update(Season=label, SeasonLabel=f"{label} {year_label}",
                       SeasonStartDate=start, SeasonEndDate=end,
                       SeasonSortKey=year * 100 + start_month)
            for window_start, window_end in bounds:
                if timestamp < window_start or (window_end is not None and timestamp > window_end):
                    continue
                effective_end = window_end
                if cutoff is not None:
                    effective_end = min(window_end, cutoff) if window_end is not None else cutoff
                if cutoff is not None and timestamp > cutoff:
                    break
                if start < window_start:
                    row["IsCompleteSeason"] = False
                elif effective_end is not None:
                    row["IsCompleteSeason"] = end <= effective_end
                if row["IsCompleteSeason"] is not pd.NA:
                    row["IsPartialSeason"] = not row["IsCompleteSeason"]
                break
        for name in output_names:
            values[name].append(row[name])
    result = permits.copy(deep=True)
    for name, dtype in {
        "Season": "string", "SeasonStartDate": "datetime64[ns]",
        "SeasonEndDate": "datetime64[ns]", "SeasonLabel": "string",
        "SeasonSortKey": "Int64", "IsCompleteSeason": "boolean", "IsPartialSeason": "boolean",
    }.items():
        result[name] = pd.array(values[name], dtype=dtype)
    return result


def _calendar_date(value: Any) -> Any:
    """Parse a calendar date without shifting timezone offsets.

    Args:
        value: ISO date string or date object; numeric epochs are unsupported.

    Returns:
        Midnight Timestamp or NaT for missing or malformed values.
    """
    if not isinstance(value, (str, date)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    return pd.NaT if pd.isna(parsed) else parsed.tz_localize(None).normalize()
