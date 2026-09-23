"""Residential development-type analysis.

This module compares residential development types and retains unknown or review
categories in analytical denominators.

Design Pattern:
    Strategy.

Pattern Rationale:
    It isolates residential-type count and share calculations behind the common Analysis
    interface.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from .base import Analysis


class TypeAnalysis(Analysis):
    """Implement the type analysis strategy.

    This concrete Strategy lets the pipeline compare residential development-type
    counts and shares across policy periods.
    """

    name = "type"

    def __init__(self, period_order: list[str] | None = None) -> None:
        """Configure period ordering and the primary comparison explicitly.

        Args:
            period_order: Unique period labels in study order. The second is
                compared with the first; later periods are contextual. None
                reports observed periods in input order without change metrics.

        Raises:
            TypeError: Period order is not a list of strings.
            ValueError: Period order is empty, duplicated, or contains blanks.
        """
        if period_order is not None:
            if not isinstance(period_order, list) or any(not isinstance(p, str) for p in period_order):
                raise TypeError("period_order must be a list of strings.")
            if not period_order or any(not p.strip() for p in period_order) or len(set(period_order)) != len(period_order):
                raise ValueError("Period order must contain unique nonblank labels.")
        self.period_order = tuple(period_order) if period_order is not None else None

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare counts and shares by classified residential type.

        Args:
            permits: DataFrame with Period, Boolean IncludeResidential, and
                ResidentialType. Included null/blank type labels become Unknown
                in the report only. Review and Unknown records stay included
                when IncludeResidential is true.

        Returns:
            ``type_summary`` contains every period/type combination observed
            among included records, filling absent combinations with zero.
            PermitCount counts included records of that type; TypeShare is a
            fraction of PeriodResidentialCount, null for a zero denominator.
            With explicit period order, the second period has count changes
            and ShareChangePercentagePoints against the first. PercentChange
            uses percent units and is null when the baseline count is zero.
            ``type_period_totals`` records each period's AllPermitCount,
            PeriodResidentialCount, and ExcludedCount, even if no types exist.

        Raises:
            TypeError: Input or inclusion/type values have unsupported types.
            ValueError: Required columns are missing, columns are duplicated,
                or period labels are missing or outside the configured order.

        Note:
            The input is never mutated or deduplicated. Counts measure records,
            not housing units. Repeated denominators in type_summary must not
            be summed across types; use type_period_totals for period totals.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        required = {"Period", "IncludeResidential", "ResidentialType"}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing type-analysis fields: {sorted(required - set(permits.columns))}")
        inclusion = permits["IncludeResidential"]
        if inclusion.isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(inclusion)):
            raise TypeError("IncludeResidential must contain nonmissing Booleans.")
        if any(not isinstance(p, str) or not p.strip() for p in permits["Period"]):
            raise ValueError("Every record needs a nonblank Period.")
        periods = list(self.period_order) if self.period_order is not None else list(permits["Period"].drop_duplicates())
        if set(permits["Period"]) - set(periods):
            raise ValueError("Input contains periods outside period_order.")
        included = permits.loc[inclusion.astype(bool), ["Period", "ResidentialType"]].copy()
        types = included["ResidentialType"]
        if any(not isinstance(value, str) for value in types.dropna()):
            raise TypeError("Included residential types must be strings or missing.")
        included["ResidentialType"] = types.astype("string").str.strip().replace("", pd.NA).fillna("Unknown")
        type_names = sorted(included["ResidentialType"].unique())
        counts = included.groupby(["Period", "ResidentialType"], observed=True).size()
        denominators = included.groupby("Period", observed=True).size()
        all_counts = permits.groupby("Period", observed=True).size()
        rows = []
        totals = []
        for position, period in enumerate(periods):
            denominator = int(denominators.get(period, 0))
            all_count = int(all_counts.get(period, 0))
            totals.append({"Period": period, "AllPermitCount": all_count,
                           "PeriodResidentialCount": denominator, "ExcludedCount": all_count - denominator})
            for type_name in type_names:
                count = int(counts.get((period, type_name), 0))
                share = count / denominator if denominator else None
                row = {"Period": period, "ResidentialType": type_name,
                       "PermitCount": count, "PeriodResidentialCount": denominator,
                       "TypeShare": share, "BaselinePeriod": None, "BaselinePermitCount": None,
                       "AbsoluteChange": None, "PercentChange": None, "ShareChangePercentagePoints": None}
                if self.period_order is not None and position == 1:
                    baseline = int(counts.get((periods[0], type_name), 0))
                    baseline_total = int(denominators.get(periods[0], 0))
                    row.update(BaselinePeriod=periods[0], BaselinePermitCount=baseline,
                               AbsoluteChange=count - baseline,
                               PercentChange=(count - baseline) * 100 / baseline if baseline else None,
                               ShareChangePercentagePoints=(share - baseline / baseline_total) * 100
                               if denominator and baseline_total else None)
                rows.append(row)
        columns = ["Period", "ResidentialType", "PermitCount", "PeriodResidentialCount", "TypeShare",
                   "BaselinePeriod", "BaselinePermitCount", "AbsoluteChange", "PercentChange", "ShareChangePercentagePoints"]
        return {
            "type_summary": pd.DataFrame(rows, columns=columns).convert_dtypes(),
            "type_period_totals": pd.DataFrame(totals, columns=[
                "Period", "AllPermitCount", "PeriodResidentialCount", "ExcludedCount",
            ]).convert_dtypes(),
        }
