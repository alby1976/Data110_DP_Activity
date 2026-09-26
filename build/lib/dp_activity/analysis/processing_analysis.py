"""Processing-time analysis.

This module summarizes valid application-to-decision durations while retaining counts
for invalid and right-censored records.

Design Pattern:
    Strategy.

Pattern Rationale:
    It encapsulates processing-time calculations behind the common Analysis interface so
    duration logic can evolve independently.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any
from math import isfinite
from numbers import Real

import pandas as pd

from .base import Analysis


class ProcessingAnalysis(Analysis):
    """Implement the processing analysis strategy.

    This concrete Strategy lets the pipeline summarize valid processing durations while
    reporting invalid and right-censored records.
    """

    name = "processing"

    def __init__(
        self, period_order: list[str] | None = None, *, community_column: str | None = None,
    ) -> None:
        """Configure period coverage and an optional community breakdown.

        Args:
            period_order: Unique nonblank study labels in output order. None
                reports observed periods in input order. Explicit labels retain
                empty periods; no automatic before/during change is calculated.
            community_column: Source community field for an additional summary.
                None disables the community breakdown.

        Raises:
            TypeError: Configuration types are unsupported.
            ValueError: Period labels are empty, blank, or duplicated.
        """
        if period_order is not None:
            if not isinstance(period_order, list) or any(not isinstance(p, str) for p in period_order):
                raise TypeError("period_order must be a list of strings.")
            if not period_order or any(not p.strip() for p in period_order) or len(set(period_order)) != len(period_order):
                raise ValueError("Period order must contain unique nonblank labels.")
        if community_column is not None and (not isinstance(community_column, str) or not community_column.strip()):
            raise TypeError("community_column must be a nonblank string or None.")
        self.period_order = tuple(period_order) if period_order is not None else None
        self.community_column = community_column

    def run(self, permits: Any) -> dict[str, Any]:
        """Summarize valid application-to-decision intervals.

        Args:
            permits: DataFrame with Period, IncludeResidential, ProcessingDays,
                HasValidProcessingDays, IsPending, and IsRightCensored. Flags
                must be nonmissing Booleans. Optional ResidentialType enables a
                type breakdown. Optional date-quality flags supply audit counts.

        Returns:
            ``processing_summary`` has residential TotalCount, ValidCount,
            InvalidCount (all ineligible durations, including pending/censored),
            PendingCount, RightCensoredCount, fractional ValidShare, median,
            mean, Q1, Q3, and IQR in days. Quartiles use linear interpolation.
            Empty valid populations have null statistics and zero valid counts.
            ``processing_period_totals`` adds AllPermitCount,
            PeriodResidentialCount, and ExcludedCount (nonresidential records).
            Optional ``processing_type_summary`` and
            ``processing_community_summary`` contain observed residential groups
            only. Unknown/blank types become Unknown; missing communities remain
            null. Audit counts are null if their source flags are unavailable.

        Raises:
            TypeError: Table, flags, durations, or grouping labels are unsupported.
            ValueError: Columns/periods are unusable or valid-duration flags
                contradict durations, pending, censoring, or date-quality flags.

        Note:
            Input is not mutated or deduplicated. Exclusion reasons can overlap
            and must not be added together. Pending is an analytical proxy, not
            an official status. These are observed valid-duration summaries,
            not survival estimates or minimum-follow-up-adjusted comparisons.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        flags = ["IncludeResidential", "HasValidProcessingDays", "IsPending", "IsRightCensored"]
        required = {"Period", "ProcessingDays", *flags}
        if self.community_column is not None:
            required.add(self.community_column)
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing processing fields: {sorted(required - set(permits.columns))}")
        audit_flags = {"NegativeCount": "HasNegativeProcessingDays",
                       "MissingDateCount": "ProcessingDateMissing",
                       "InvalidDateCount": "ProcessingDateInvalid",
                       "AfterObservationEndCount": "IsAfterObservationEnd"}
        for flag in flags + [f for f in audit_flags.values() if f in permits]:
            if permits[flag].isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(permits[flag])):
                raise TypeError(f"{flag} must contain nonmissing Booleans.")
        if any(not isinstance(p, str) or not p.strip() for p in permits["Period"]):
            raise ValueError("Every record needs a nonblank Period.")
        periods = list(self.period_order) if self.period_order is not None else list(permits["Period"].drop_duplicates())
        if set(permits["Period"]) - set(periods):
            raise ValueError("Input contains periods outside period_order.")
        durations = permits["ProcessingDays"]
        if any(not isinstance(v, Real) or isinstance(v, bool) or not isfinite(v)
               for v in durations.dropna()):
            raise TypeError("ProcessingDays must contain finite numbers or missing values.")
        valid = permits["HasValidProcessingDays"].astype(bool)
        if (valid & (durations.isna() | durations.lt(0))).any():
            raise ValueError("Valid processing rows require nonnegative durations.")
        for flag in ["IsPending", "IsRightCensored", *audit_flags.values()]:
            if flag in permits and (valid & permits[flag]).any():
                raise ValueError(f"Valid processing rows contradict {flag}.")
        if (permits["IsPending"].astype(bool) & ~permits["IsRightCensored"].astype(bool)).any():
            raise ValueError("Pending rows must also be right-censored.")
        included = permits.loc[permits["IncludeResidential"].astype(bool)].copy()
        count_columns = ["TotalCount", "ValidCount", "InvalidCount", "PendingCount",
                         "RightCensoredCount", "ValidShare", *audit_flags]
        metrics = [*count_columns, "MedianProcessingDays", "MeanProcessingDays",
                   "Q1ProcessingDays", "Q3ProcessingDays", "IQRProcessingDays"]
        rows = []
        totals = []
        for period in periods:
            subset = included.loc[included["Period"].eq(period)]
            summary = _summarize(subset, audit_flags)
            rows.append({"Period": period, **summary})
            all_count = int(permits["Period"].eq(period).sum())
            totals.append({"Period": period, "AllPermitCount": all_count,
                           "PeriodResidentialCount": len(subset), "ExcludedCount": all_count - len(subset),
                           **{key: summary[key] for key in count_columns}})
        results = {
            "processing_summary": pd.DataFrame(rows, columns=["Period", *metrics]).convert_dtypes(),
            "processing_period_totals": pd.DataFrame(totals, columns=[
                "Period", "AllPermitCount", "PeriodResidentialCount", "ExcludedCount", *count_columns,
            ]).convert_dtypes(),
        }
        breakdowns = []
        if "ResidentialType" in included:
            breakdowns.append(("ResidentialType", "ResidentialType", "processing_type_summary"))
        if self.community_column is not None:
            breakdowns.append((self.community_column, "Community", "processing_community_summary"))
        for source, label, key in breakdowns:
            if any(not isinstance(v, str) for v in included[source].dropna()):
                raise TypeError(f"{source} must contain text or missing values.")
            labels = included[source].astype("string").str.strip().replace("", pd.NA)
            if label == "ResidentialType":
                labels = labels.fillna("Unknown")
            grouped_rows = []
            for period in periods:
                subset = included.loc[included["Period"].eq(period)]
                group_labels = labels.loc[included["Period"].eq(period)]
                for location, group in subset.groupby(group_labels, dropna=False, sort=True, observed=True):
                    grouped_rows.append({"Period": period, label: location, **_summarize(group, audit_flags)})
            results[key] = pd.DataFrame(grouped_rows, columns=["Period", label, *metrics]).convert_dtypes()
        return results


def _summarize(records: pd.DataFrame, audit_flags: dict[str, str]) -> dict[str, Any]:
    """Summarize one residential cohort without treating unknown durations as zero.

    Args:
        records: Validated records for one period or subgroup.
        audit_flags: Output count names mapped to optional feature flags.

    Returns:
        Counts, nullable audit counts, and duration statistics in calendar days.
    """
    durations = records.loc[records["HasValidProcessingDays"].astype(bool), "ProcessingDays"].astype(float)
    total = len(records)
    count = len(durations)
    q1 = durations.quantile(0.25) if count else None
    q3 = durations.quantile(0.75) if count else None
    return {
        "TotalCount": total, "ValidCount": count, "InvalidCount": total - count,
        "PendingCount": int(records["IsPending"].sum()),
        "RightCensoredCount": int(records["IsRightCensored"].sum()),
        "ValidShare": count / total if total else None,
        **{name: int(records[flag].sum()) if flag in records else None for name, flag in audit_flags.items()},
        "MedianProcessingDays": durations.median() if count else None,
        "MeanProcessingDays": durations.mean() if count else None,
        "Q1ProcessingDays": q1, "Q3ProcessingDays": q3,
        "IQRProcessingDays": q3 - q1 if count else None,
    }
