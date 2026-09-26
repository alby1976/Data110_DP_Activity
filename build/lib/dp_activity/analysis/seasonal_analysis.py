"""Seasonal permit analysis.

This module separates complete-season comparisons from partial-season context to avoid
misleading exposure comparisons.

Design Pattern:
    Strategy.

Pattern Rationale:
    It encapsulates complete- and partial-season comparisons behind the shared Analysis
    contract.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any
from datetime import date

import pandas as pd

from dp_activity.config import StudyPeriod
from dp_activity.features.season_features import add_season_features

from .base import Analysis
from .processing_analysis import ProcessingAnalysis
from .volume_analysis import VolumeAnalysis


class SeasonalAnalysis(Analysis):
    """Implement the seasonal analysis strategy.

    This concrete Strategy lets the pipeline separate complete-season headline
    comparisons from partial-season context.
    """

    name = "seasonal"

    def __init__(
        self, periods: list[StudyPeriod] | None = None, *,
        season_months: dict[str, list[int]] | None = None,
        date_column: str = "applied_date", observation_end: date | None = None,
    ) -> None:
        """Configure calendar exposure independently of observed applications.

        Args:
            periods: Inclusive study windows. None summarizes observed seasons
                only, without inferring zero-activity seasons or exposure.
            season_months: Labels mapped to three consecutive months, partitioning
                the year. Defaults to meteorological seasons.
            date_column: Application-date field for exposure and month checks.
            observation_end: Explicit inclusive cutoff, required for open windows.

        Raises:
            TypeError: Configuration types are unsupported.
            ValueError: Windows or season definitions are invalid.
        """
        self.volume = VolumeAnalysis(periods, date_column=date_column, observation_end=observation_end)
        self.periods = list(periods) if periods is not None else None
        self.date_column = date_column
        self.observation_end = observation_end
        definitions = season_months if season_months is not None else {
            "Winter": [12, 1, 2], "Spring": [3, 4, 5],
            "Summer": [6, 7, 8], "Fall": [9, 10, 11],
        }
        # Validate through the feature contract to keep one season definition.
        add_season_features(pd.DataFrame({date_column: pd.Series(dtype="object")}),
                            date_column=date_column, season_months=definitions,
                            analysis_windows=self.periods or [], observation_end=observation_end)
        self.season_months = {label: list(months) for label, months in definitions.items()}

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare seasonality without disguising partial exposure.

        Args:
            permits: DataFrame with Period, Boolean IncludeResidential, Season,
                SeasonStartDate, and nullable Boolean IsCompleteSeason. Configured
                windows require the application-date column. Optional processing
                features enable per-season duration summaries.

        Returns:
            ``seasonal_summary`` contains period/season-instance counts and
            nullable exposure. ``complete_seasons``, ``partial_seasons``, and
            ``unknown_seasons`` partition it by IsCompleteSeason. Configured
            windows include zero-activity seasons; exploratory mode reports
            observed instances only. Optional ``seasonal_monthly_volume`` and
            ``calendar_month_summary`` support like-month inspection when dates
            exist, separating complete-month counts from partial/unknown exposure.
            Optional processing statistics use the ProcessingAnalysis contract.
            DP_Rate30 is residential PermitCount / ExposureDays * 30, null for
            unknown or nonpositive exposure. Calendar-month rates use pooled
            counts and exposure rather than averaging individual monthly rates.

        Raises:
            TypeError: Table, flags, or configuration types are unsupported.
            ValueError: Season fields are missing, inconsistent, or disagree
                with configured dates/windows; open windows lack a cutoff.

        Note:
            Counts are residential application records, not dwellings. Complete
            seasons are eligible for comparison but contextual policy periods
            remain contextual. Normalizing days does not remove seasonality or
            establish causality. Records are never mutated, dropped, or deduplicated.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        fields = ["Period", "IncludeResidential", "Season", "SeasonStartDate", "IsCompleteSeason"]
        if not set(fields).issubset(permits.columns):
            raise ValueError("Missing required seasonal fields.")
        for field in ("Period", "Season"):
            if any(not isinstance(v, str) or not v.strip() for v in permits[field]):
                raise ValueError(f"{field} requires nonblank labels.")
        for field in ("IncludeResidential", "IsCompleteSeason"):
            if len(permits) and not pd.api.types.is_bool_dtype(permits[field]):
                raise TypeError(f"{field} must have Boolean dtype.")
        if permits["IncludeResidential"].isna().any():
            raise ValueError("Residential inclusion cannot be missing.")
        working = permits.copy(deep=True).reset_index(drop=True)
        dates = working["SeasonStartDate"]
        if any(not isinstance(v, (str, date)) for v in dates):
            raise ValueError("Season starts must be valid calendar dates.")
        starts = pd.to_datetime(dates, format="ISO8601", errors="coerce")
        if starts.isna().any() or starts.dt.tz is not None or not starts.eq(starts.dt.normalize()).all():
            raise ValueError("Season starts must be timezone-free calendar dates.")
        working["SeasonStartDate"] = starts
        for label, start in zip(working["Season"], starts):
            if label not in self.season_months or start.day != 1 or start.month != self.season_months[label][0]:
                raise ValueError("Season label and start date disagree with season definitions.")
        if "IsPartialSeason" in working:
            partial = working["IsPartialSeason"]
            complete = working["IsCompleteSeason"].astype("boolean")
            if (len(working) and not pd.api.types.is_bool_dtype(partial)):
                raise TypeError("IsPartialSeason must have Boolean dtype.")
            if not partial.astype("boolean").equals(~complete):
                raise ValueError("Partial and complete season flags disagree.")
        results = {}
        if self.periods is not None or self.date_column in working:
            monthly = self.volume.run(working)["monthly_volume"]
            results["seasonal_monthly_volume"] = monthly
            results["calendar_month_summary"] = _calendar_months(monthly)
            expected = add_season_features(
                working[[self.date_column]], date_column=self.date_column,
                season_months=self.season_months, analysis_windows=self.periods or [],
                observation_end=self.observation_end,
            )
            for field in ("Season", "SeasonStartDate"):
                if not working[field].astype("string").equals(expected[field].astype("string")):
                    raise ValueError(f"{field} disagrees with application dates.")
            if self.periods is not None and not working["IsCompleteSeason"].astype("boolean").equals(expected["IsCompleteSeason"]):
                raise ValueError("Completeness flags disagree with configured exposure.")
        keys = ["Period", "SeasonStartDate"]
        for _, group in working.groupby(keys, observed=True, sort=False):
            if group["Season"].nunique() != 1 or group["IsCompleteSeason"].nunique(dropna=False) != 1:
                raise ValueError("A period/season instance has inconsistent labels or completeness.")
        slots = []
        if self.periods is not None:
            for period in self.periods:
                end = period.end
                if self.observation_end is not None:
                    end = min(end, self.observation_end) if end is not None else self.observation_end
                # VolumeAnalysis has already validated the effective window.
                calendar = pd.DataFrame({self.date_column: pd.date_range(period.start, end)})
                calendar = add_season_features(calendar, date_column=self.date_column,
                                              season_months=self.season_months,
                                              analysis_windows=self.periods, observation_end=self.observation_end)
                for start, group in calendar.groupby("SeasonStartDate", sort=True):
                    slots.append((period.name, group["Season"].iloc[0], start,
                                  group["IsCompleteSeason"].iloc[0], len(group)))
        else:
            for period in working["Period"].drop_duplicates():
                for start, group in working.loc[working["Period"].eq(period)].groupby("SeasonStartDate", sort=True):
                    slots.append((period, group["Season"].iloc[0], start, group["IsCompleteSeason"].iloc[0], None))
        processing_fields = {"ProcessingDays", "HasValidProcessingDays", "IsPending", "IsRightCensored"}
        has_processing = bool(processing_fields & set(working.columns))
        processor = ProcessingAnalysis()
        processing_columns = []
        if has_processing:
            processing_columns = processor.run(working)["processing_summary"].columns.drop("Period").tolist()
        rows = []
        for period, label, start, complete, exposure in slots:
            subset = working.loc[working["Period"].eq(period) & working["SeasonStartDate"].eq(start)]
            count = int(subset["IncludeResidential"].sum())
            row = {"Period": period, "Season": label, "SeasonStartDate": start,
                   "SeasonEndDate": start + pd.DateOffset(months=3) - pd.Timedelta(1, unit="D"),
                   "IsCompleteSeason": complete, "ExposureDays": exposure,
                   "WindowSource": "configured" if self.periods is not None else "observed_seasons",
                   "PermitCount": count, "AllPermitCount": len(subset), "ExcludedCount": len(subset) - count}
            if has_processing:
                stats = ProcessingAnalysis([period]).run(subset)["processing_summary"].iloc[0]
                row.update(stats.drop(labels="Period").to_dict())
            rows.append(row)
        columns = ["Period", "Season", "SeasonStartDate", "SeasonEndDate", "IsCompleteSeason",
                   "ExposureDays", "WindowSource", "PermitCount", "AllPermitCount", "ExcludedCount"]
        columns += processing_columns
        summary = pd.DataFrame(rows, columns=columns).convert_dtypes()
        exposure = summary["ExposureDays"].astype("Float64")
        summary["DP_Rate30"] = summary["PermitCount"].astype("Float64").div(exposure.where(exposure.gt(0))) * 30
        summary["IsCompleteSeason"] = summary["IsCompleteSeason"].astype("boolean")
        results.update(seasonal_summary=summary,
                       complete_seasons=summary.loc[summary["IsCompleteSeason"].fillna(False)].copy(),
                       partial_seasons=summary.loc[summary["IsCompleteSeason"].eq(False).fillna(False)].copy(),
                       unknown_seasons=summary.loc[summary["IsCompleteSeason"].isna()].copy())
        return results


def _calendar_months(monthly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate like calendar months without treating partial exposure as complete.

    Args:
        monthly: VolumeAnalysis month table, including zero months when configured.

    Returns:
        Period/month counts with complete-month means and exposure-status counts.
        ExposureDays sums all grouped exposure only when every month is known.
        DP_Rate30 divides pooled counts by pooled positive exposure, otherwise null.
    """
    rows = []
    if not monthly.empty:
        working = monthly.assign(CalendarMonth=monthly["YearMonth"].dt.month)
        for (period, month), group in working.groupby(["Period", "CalendarMonth"], sort=False, observed=True):
            full = group.loc[group["IsPartialMonth"].eq(False).fillna(False)]
            exposure = group["ExposureDays"].sum() if group["ExposureDays"].notna().all() else None
            rows.append({"Period": period, "CalendarMonth": month,
                         "PermitCount": int(group["PermitCount"].sum()), "MonthCount": len(group),
                         "ExposureDays": exposure,
                         "DP_Rate30": int(group["PermitCount"].sum()) / exposure * 30
                         if exposure is not None and exposure > 0 else None,
                         "CompleteMonthCount": len(full),
                         "PartialMonthCount": int(group["IsPartialMonth"].astype("boolean").fillna(False).sum()),
                         "UnknownMonthCount": int(group["IsPartialMonth"].isna().sum()),
                         "CompleteMonthPermitCount": int(full["PermitCount"].sum()),
                         "MeanCompleteMonthlyCount": full["PermitCount"].mean() if len(full) else None})
    return pd.DataFrame(rows, columns=["Period", "CalendarMonth", "PermitCount", "MonthCount", "ExposureDays", "DP_Rate30",
                                      "CompleteMonthCount", "PartialMonthCount", "UnknownMonthCount",
                                      "CompleteMonthPermitCount", "MeanCompleteMonthlyCount"]).convert_dtypes()
