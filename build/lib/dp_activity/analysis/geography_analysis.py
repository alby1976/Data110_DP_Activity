"""Community and ward analysis.

This module compares permit activity by community and ward while preserving missing
geography and small-baseline warnings.

Design Pattern:
    Strategy.

Pattern Rationale:
    It packages community and ward calculations as one interchangeable analysis that the
    pipeline can select without geography-specific branching.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any
from numbers import Real

import pandas as pd

from .base import Analysis


class GeographyAnalysis(Analysis):
    """Implement the geography analysis strategy.

    This concrete Strategy lets the pipeline compare permit activity by community and
    ward while retaining missing geography and small-baseline warnings.

    Attributes:
        minimum_baseline_count: Count below which a community baseline is flagged.
    """

    name = "geography"

    def __init__(
        self, minimum_baseline_count: int, *, period_order: list[str] | None = None,
        community_column: str = "Community", ward_column: str = "Ward",
    ) -> None:
        """Configure the comparison and source geography fields.

        Args:
            minimum_baseline_count: Nonnegative count below which to warn.
            period_order: Unique study labels; the second is compared with the
                first and later periods are contextual. Defaults to Before/During.
            community_column: Source community field, retained as text labels.
            ward_column: Source ward field, normalized to text for reporting.

        Raises:
            TypeError: Configuration values have unsupported types.
            ValueError: Threshold is negative or labels are blank or duplicated.
        """
        if type(minimum_baseline_count) is not int:
            raise TypeError("minimum_baseline_count must be an integer.")
        if minimum_baseline_count < 0:
            raise ValueError("minimum_baseline_count must be nonnegative.")
        periods = ["Before", "During"] if period_order is None else period_order
        if not isinstance(periods, list) or any(not isinstance(p, str) for p in periods):
            raise TypeError("period_order must be a list of strings.")
        if len(periods) < 2 or any(not p.strip() for p in periods) or len(set(periods)) != len(periods):
            raise ValueError("Provide at least two unique nonblank period labels.")
        for field in (community_column, ward_column):
            if not isinstance(field, str) or not field.strip():
                raise TypeError("Geography field names must be nonblank strings.")
        self.minimum_baseline_count = minimum_baseline_count
        self.period_order = tuple(periods)
        self.community_column = community_column
        self.ward_column = ward_column

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare permit activity by community and ward.

        Args:
            permits: DataFrame with nonmissing Boolean IncludeResidential,
                configured Period labels, and the configured geography columns.
                Geography accepts text or numeric labels; nulls and blanks are
                kept as a separate missing group, not a literal place name.

        Returns:
            ``community_summary`` and ``ward_summary`` contain period/location
            counts, fractional PermitShare using all residential records, and
            primary comparison metrics. Absent period/location pairs have zero
            counts. PercentChange is null for zero baselines. SmallBaselineWarning
            applies to both primary periods; contextual rows have no comparisons.
            ``geography_period_totals`` includes residential, excluded, and missing
            geography counts per period. Summary denominators repeat per location
            and must not be summed. Empty inputs retain stable output columns.

        Raises:
            TypeError: Input, inclusion flags, or geography values are unsupported.
            ValueError: Required columns are missing, columns are duplicated, or
                periods are missing or outside the configured study labels.

        Note:
            Counts measure permit records, not homes. Input records are neither
            mutated nor deduplicated. Missing locations remain in denominators.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        required = {"Period", "IncludeResidential", self.community_column, self.ward_column}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing geography fields: {sorted(required - set(permits.columns))}")
        inclusion = permits["IncludeResidential"]
        if inclusion.isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(inclusion)):
            raise TypeError("IncludeResidential must contain nonmissing Booleans.")
        if any(not isinstance(p, str) or p not in self.period_order for p in permits["Period"]):
            raise ValueError("Every record needs a configured Period.")
        included = permits.loc[inclusion.astype(bool)].copy()
        denominators = included.groupby("Period", observed=True).size()
        all_counts = permits.groupby("Period", observed=True).size()
        totals = [{"Period": period, "AllPermitCount": int(all_counts.get(period, 0)),
                   "PeriodResidentialCount": int(denominators.get(period, 0)),
                   "ExcludedCount": int(all_counts.get(period, 0) - denominators.get(period, 0))}
                  for period in self.period_order]
        results = {}
        for source, label, output in (
            (self.community_column, "Community", "community_summary"),
            (self.ward_column, "Ward", "ward_summary"),
        ):
            values = included[source]
            if any(not isinstance(v, (str, Real)) or isinstance(v, bool)
                   for v in values.dropna()):
                raise TypeError("Geography values must be scalar text or numeric labels.")
            locations = values.astype("string").str.strip().replace("", pd.NA)
            # An internal integer key keeps real labels distinct from missing data.
            codes, unique = pd.factorize(locations, sort=True)
            keys = list(range(len(unique))) + ([-1] if locations.isna().any() else [])
            working = pd.DataFrame({"Period": included["Period"].to_numpy(), "Key": codes})
            counts = working.groupby(["Period", "Key"], observed=True).size()
            rows = []
            for position, period in enumerate(self.period_order):
                denominator = int(denominators.get(period, 0))
                totals[position][f"Missing{label}Count"] = int(counts.get((period, -1), 0))
                for key in keys:
                    count = int(counts.get((period, key), 0))
                    baseline = int(counts.get((self.period_order[0], key), 0))
                    row = {"Period": period, label: unique[key] if key >= 0 else pd.NA,
                           "IsMissingGeography": key == -1, "PermitCount": count,
                           "PeriodResidentialCount": denominator,
                           "PermitShare": count / denominator if denominator else None,
                           "BaselinePeriod": self.period_order[0] if position < 2 else None,
                           "BaselinePermitCount": baseline if position < 2 else None,
                           "AbsoluteChange": None, "PercentChange": None,
                           "SmallBaselineWarning": baseline < self.minimum_baseline_count
                           if position < 2 else None}
                    if position == 1:
                        row.update(AbsoluteChange=count - baseline,
                                   PercentChange=(count - baseline) * 100 / baseline if baseline else None)
                    rows.append(row)
            columns = ["Period", label, "IsMissingGeography", "PermitCount",
                       "PeriodResidentialCount", "PermitShare", "BaselinePeriod",
                       "BaselinePermitCount", "AbsoluteChange", "PercentChange", "SmallBaselineWarning"]
            results[output] = pd.DataFrame(rows, columns=columns).convert_dtypes()
        results["geography_period_totals"] = pd.DataFrame(totals).convert_dtypes()
        return results
