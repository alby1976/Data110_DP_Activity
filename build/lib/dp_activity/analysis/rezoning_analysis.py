"""Analysis of the transparent rezoning-relevance flag.

This module compares the project-defined rezoning-relevance flag across policy periods
without presenting it as an official City designation.

Design Pattern:
    Strategy.

Pattern Rationale:
    It isolates the analytical rezoning-relevance comparison while remaining
    interchangeable with the other analysis components.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .base import Analysis


class RezoningAnalysis(Analysis):
    """Implement the rezoning analysis strategy.

    This concrete Strategy lets the pipeline compare the project-defined
    rezoning-relevance flag across policy periods.
    """

    name = "rezoning"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare rezoning-relevant counts and shares by policy period.

        Args:
            permits: DataFrame with Period, nonmissing Boolean IncludeResidential,
                and nullable Boolean RezoningRelevant. Optional Boolean
                ClassificationNeedsReview supplies an overlapping review audit.
                ClassificationRule, ResidentialType, and land_use_district
                enable optional breakdowns; missing/blank labels become Unknown.

        Returns:
            ``rezoning_summary`` reports residential relevant, nonrelevant, and
            unknown counts and shares for each observed period, including periods
            with no residential records. Shares use all residential records and
            are null for zero denominators. ReviewCount overlaps those categories
            and is null when review evidence is unavailable or incomplete.
            Optional ``rezoning_by_rule``, ``rezoning_by_type``, and
            ``rezoning_by_district`` use the same period-wide denominator;
            GroupResidentialCount records each subgroup's size.

        Raises:
            TypeError: Input, Boolean flags, or included subgroup labels have
                unsupported types.
            ValueError: Required fields are missing, columns are duplicated,
                or periods are missing or blank.

        Note:
            Relevance is an analytical flag, not an official City designation or
            evidence of policy causation. Review records remain in denominators.
            Counts measure records, not dwellings; inputs are never mutated or
            deduplicated. Do not sum repeated period denominators in breakdowns.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        required = {"Period", "IncludeResidential", "RezoningRelevant"}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing rezoning fields: {sorted(required - set(permits.columns))}")
        for field in ("IncludeResidential", "RezoningRelevant", "ClassificationNeedsReview"):
            if field in permits and len(permits) and not pd.api.types.is_bool_dtype(permits[field]):
                raise TypeError(f"{field} must have Boolean dtype.")
        if permits["IncludeResidential"].isna().any():
            raise TypeError("IncludeResidential must contain nonmissing Booleans.")
        if any(not isinstance(p, str) or not p.strip() for p in permits["Period"]):
            raise ValueError("Every record needs a nonblank Period.")
        included = permits.loc[permits["IncludeResidential"].astype(bool)].copy()
        dimensions = {
            "rezoning_by_rule": "ClassificationRule",
            "rezoning_by_type": "ResidentialType",
            "rezoning_by_district": "land_use_district",
        }
        for field in dimensions.values():
            if field in included:
                if any(not isinstance(v, str) for v in included[field].dropna()):
                    raise TypeError(f"Included {field} values must be strings or missing.")
                included[field] = included[field].astype("string").str.strip().replace("", pd.NA).fillna("Unknown")
        rows = []
        breakdowns = {key: [] for key, field in dimensions.items() if field in included}
        for period in permits["Period"].drop_duplicates():
            subset = included.loc[included["Period"].eq(period)]
            denominator = len(subset)
            all_count = int(permits["Period"].eq(period).sum())
            rows.append({"Period": period, "AllPermitCount": all_count,
                         "ExcludedCount": all_count - denominator,
                         **_counts(subset, denominator)})
            for key in breakdowns:
                field = dimensions[key]
                for label, group in subset.groupby(field, sort=True, observed=True):
                    breakdowns[key].append({"Period": period, field: label,
                                            "GroupResidentialCount": len(group),
                                            **_counts(group, denominator)})
        measures = ["PeriodResidentialCount", "RezoningRelevantCount", "NotRezoningRelevantCount",
                    "UnknownRelevanceCount", "RezoningRelevantShare", "NotRezoningRelevantShare",
                    "UnknownRelevanceShare", "ReviewCount"]
        results = {"rezoning_summary": pd.DataFrame(
            rows, columns=["Period", "AllPermitCount", "ExcludedCount", *measures],
        ).convert_dtypes()}
        for key, values in breakdowns.items():
            results[key] = pd.DataFrame(values, columns=[
                "Period", dimensions[key], "GroupResidentialCount", *measures,
            ]).convert_dtypes()
        return results


def _counts(group: pd.DataFrame, denominator: int) -> dict[str, Any]:
    """Summarize relevance without excluding unknown or review records.

    Args:
        group: Residential records for one period or audit subgroup.
        denominator: All residential records in the enclosing policy period.

    Returns:
        Counts and fractional shares with null shares for empty denominators.
        ReviewCount is null when any required review evidence is unavailable.
    """
    relevant = group["RezoningRelevant"].astype("boolean")
    yes = int(relevant.eq(True).sum())
    no = int(relevant.eq(False).sum())
    unknown = int(relevant.isna().sum())
    review = group.get("ClassificationNeedsReview")
    return {
        "PeriodResidentialCount": denominator,
        "RezoningRelevantCount": yes,
        "NotRezoningRelevantCount": no,
        "UnknownRelevanceCount": unknown,
        "RezoningRelevantShare": yes / denominator if denominator else None,
        "NotRezoningRelevantShare": no / denominator if denominator else None,
        "UnknownRelevanceShare": unknown / denominator if denominator else None,
        "ReviewCount": int(review.sum()) if review is not None and review.notna().all() else None,
    }
