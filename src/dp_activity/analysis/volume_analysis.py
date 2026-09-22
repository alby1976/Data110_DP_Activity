"""Permit-volume analysis.

This module calculates total and monthly residential permit volumes, including explicit
zero-activity months.

Design Pattern:
    Strategy.

Pattern Rationale:
    It provides the volume-calculation algorithm as an interchangeable pipeline
    analysis.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any
from datetime import date

import pandas as pd

from dp_activity.config import StudyPeriod

from .base import Analysis


class VolumeAnalysis(Analysis):
    """Implement the volume analysis strategy.

    This concrete Strategy lets the pipeline calculate total and monthly residential
    permit activity, including zero-activity months.
    """

    name = "volume"

    def __init__(
        self, periods: list[StudyPeriod] | None = None, *,
        date_column: str = "applied_date", observation_end: date | None = None,
    ) -> None:
        """Configure exposure independently of observed permit counts.

        Args:
            periods: Ordered inclusive study windows. None permits exploratory
                inference from each observed period's first and last months;
                that mode cannot establish exposure days or completeness.
            date_column: Application-date field used with configured windows.
            observation_end: Explicit inclusive source observation horizon,
                required for open-ended windows and used to cap closed windows.

        Raises:
            TypeError: Configuration has unsupported types.
            ValueError: Periods are empty, invalid, overlapping, or unordered.
        """
        if not isinstance(date_column, str) or not date_column.strip():
            raise TypeError("date_column must be a nonblank string.")
        if observation_end is not None and type(observation_end) is not date:
            raise TypeError("observation_end must be a calendar date or None.")
        if periods is not None:
            if not isinstance(periods, list) or any(not isinstance(p, StudyPeriod) for p in periods):
                raise TypeError("periods must be a list of StudyPeriod values.")
            if not periods or len({p.name for p in periods}) != len(periods):
                raise ValueError("Periods must be nonempty and uniquely named.")
            previous = None
            for period in periods:
                if not isinstance(period.name, str) or not period.name.strip():
                    raise ValueError("Period names must be nonblank.")
                if type(period.start) is not date or (period.end is not None and type(period.end) is not date):
                    raise TypeError("Period boundaries must be calendar dates.")
                if period.end is not None and period.end < period.start:
                    raise ValueError("Period end precedes start.")
                if previous is not None and (previous.end is None or period.start <= previous.end):
                    raise ValueError("Periods must be ordered and non-overlapping.")
                previous = period
        self.periods = tuple(periods) if periods is not None else None
        self.date_column = date_column
        self.observation_end = observation_end

    def run(self, permits: Any) -> dict[str, Any]:
        """Calculate total and monthly residential application counts.

        Args:
            permits: DataFrame with Boolean IncludeResidential and Period. With
                configured windows, date_column is required; exploratory mode
                accepts YearMonth or date_column. Missing or out-of-window
                dates must be resolved before aggregation.

        Returns:
            ``permit_volume`` and ``monthly_volume`` DataFrames. PermitCount
            counts included residential rows; AllPermitCount is the denominator
            of all permit rows and ExcludedCount is their difference. Monthly
            tables include zero months, inclusive exposure days, and nullable
            IsPartialMonth. Period tables include zero-month mean/median and
            comparisons of the second period against the first, leaving percent
            change null when the baseline is zero. Later periods are contextual.

        Raises:
            TypeError: Input is not a DataFrame or inclusion is not Boolean.
            ValueError: Fields or dates are unusable, periods mismatch the input,
                or an open-ended period lacks an observation horizon.

        Note:
            Counts represent records, not housing units. Input rows are never
            mutated or silently dropped. Exploratory inferred month ranges are
            labelled as such and have unknown exposure, not assumed full months.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        date_field = self.date_column if self.periods is not None or "YearMonth" not in permits else "YearMonth"
        required = {"Period", "IncludeResidential", date_field}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing volume fields: {sorted(required - set(permits.columns))}")
        inclusion = permits["IncludeResidential"]
        if inclusion.isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(inclusion)):
            raise TypeError("IncludeResidential must contain nonmissing Booleans.")
        if any(not isinstance(value, str) or not value.strip() for value in permits["Period"]):
            raise ValueError("Every record needs a nonblank Period.")
        dates = permits[date_field].map(_calendar_date).astype("datetime64[ns]")
        if dates.isna().any():
            raise ValueError("Volume aggregation requires valid dates for every record.")
        invalid_flag = f"{date_field}_invalid"
        if invalid_flag in permits:
            flag = permits[invalid_flag]
            if not pd.api.types.is_bool_dtype(flag) or flag.isna().any() or flag.any():
                raise ValueError("Resolve invalid date evidence before volume aggregation.")
        working = pd.DataFrame({"Period": permits["Period"].to_numpy(),
                                "Date": dates.to_numpy(), "Included": inclusion.to_numpy()})
        working["YearMonth"] = working["Date"].dt.to_period("M").dt.to_timestamp()
        windows = []
        if self.periods is not None:
            if set(working["Period"]) - {p.name for p in self.periods}:
                raise ValueError("Input contains a period outside the configured analysis windows.")
            for period in self.periods:
                end = period.end
                if self.observation_end is not None:
                    end = min(end, self.observation_end) if end is not None else self.observation_end
                if end is None:
                    raise ValueError("Open-ended volume windows require observation_end.")
                if end < period.start:
                    raise ValueError("Observation horizon precedes a configured study window.")
                windows.append((period.name, pd.Timestamp(period.start), pd.Timestamp(end)))
        else:
            for name in working["Period"].drop_duplicates():
                observed = working.loc[working["Period"].eq(name), "YearMonth"]
                windows.append((name, observed.min(), observed.max()))
        monthly_rows = []
        totals = []
        for name, start, end in windows:
            subset = working.loc[working["Period"].eq(name)]
            if self.periods is not None and not subset["Date"].between(start, end).all():
                raise ValueError(f"Records assigned to {name!r} fall outside its observation window.")
            monthly_counts = []
            for month in pd.date_range(start.to_period("M").to_timestamp(), end.to_period("M").to_timestamp(), freq="MS"):
                rows = subset.loc[subset["YearMonth"].eq(month)]
                included = int(rows["Included"].sum())
                all_count = len(rows)
                days = None
                if self.periods is not None:
                    days = (min(end, month + pd.offsets.MonthEnd(0)) - max(start, month)).days + 1
                monthly_rows.append({
                    "Period": name, "YearMonth": month, "PermitCount": included,
                    "AllPermitCount": all_count, "ExcludedCount": all_count - included,
                    "ResidentialShare": included / all_count if all_count else None,
                    "ExposureDays": days,
                    "IsPartialMonth": days < month.days_in_month if days is not None else None,
                    "WindowSource": "configured" if self.periods is not None else "inferred_observed_months",
                })
                monthly_counts.append(included)
            counts = pd.Series(monthly_counts, dtype="int64")
            total = int(counts.sum())
            totals.append({
                "Period": name, "PermitCount": total, "AllPermitCount": len(subset),
                "ExcludedCount": len(subset) - total,
                "ResidentialShare": total / len(subset) if len(subset) else None,
                "MonthCount": len(counts), "MeanMonthlyCount": counts.mean(), "MedianMonthlyCount": counts.median(),
                "ExposureDays": (end - start).days + 1 if self.periods is not None else None,
                "WindowStart": start, "WindowEnd": end if self.periods is not None else end + pd.offsets.MonthEnd(0),
                "WindowSource": "configured" if self.periods is not None else "inferred_observed_months",
                "BaselinePeriod": None, "AbsoluteChange": None, "PercentChange": None,
            })
        if len(totals) >= 2:
            baseline, comparison = totals[:2]
            change = comparison["PermitCount"] - baseline["PermitCount"]
            comparison.update(BaselinePeriod=baseline["Period"], AbsoluteChange=change,
                              PercentChange=change * 100 / baseline["PermitCount"] if baseline["PermitCount"] else None)
        monthly_columns = ["Period", "YearMonth", "PermitCount", "AllPermitCount", "ExcludedCount",
                           "ResidentialShare", "ExposureDays", "IsPartialMonth", "WindowSource"]
        total_columns = ["Period", "PermitCount", "AllPermitCount", "ExcludedCount", "ResidentialShare",
                         "MonthCount", "MeanMonthlyCount", "MedianMonthlyCount", "ExposureDays",
                         "WindowStart", "WindowEnd", "WindowSource", "BaselinePeriod", "AbsoluteChange", "PercentChange"]
        return {"permit_volume": pd.DataFrame(totals, columns=total_columns).convert_dtypes(),
                "monthly_volume": pd.DataFrame(monthly_rows, columns=monthly_columns).convert_dtypes()}


def _calendar_date(value: Any) -> Any:
    """Interpret a date without shifting its source calendar day.

    Args:
        value: ISO text or a date object.

    Returns:
        Midnight Timestamp, or NaT for unsupported/malformed values.
    """
    if not isinstance(value, (str, date)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    return pd.NaT if pd.isna(parsed) else parsed.tz_localize(None).normalize()
