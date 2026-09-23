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

    def __init__(
        self, period_order: list[str] | None = None, *, district_column: str = "LandUseDistrict",
    ) -> None:
        """Configure study ordering and the optional district audit source.

        Args:
            period_order: Unique nonblank labels in study order. The second is
                compared with the first; later periods are contextual. None
                reports observed periods in input order without comparisons.
            district_column: District source field; its presence enables an
                audit breakdown. Missing fields do not imply known districts.

        Raises:
            TypeError: Configuration has unsupported types.
            ValueError: Period order is empty, duplicated, or contains blanks.
        """
        if period_order is not None:
            if not isinstance(period_order, list) or any(not isinstance(p, str) for p in period_order):
                raise TypeError("period_order must be a list of strings.")
            if not period_order or any(not p.strip() for p in period_order) or len(set(period_order)) != len(period_order):
                raise ValueError("Period order must contain unique nonblank labels.")
        if not isinstance(district_column, str) or not district_column.strip():
            raise TypeError("district_column must be a nonblank string.")
        self.period_order = tuple(period_order) if period_order is not None else None
        self.district_column = district_column

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare rezoning-relevant counts and shares by policy period.

        Args:
            permits: DataFrame with Period and nonmissing Boolean
                IncludeResidential and RezoningRelevant. Optional
                ClassificationNeedsReview must also be nonmissing Boolean.
                ClassificationRule, ResidentialType, and the district field
                enable separate audit tables when present.

        Returns:
            ``rezoning_summary`` contains all-record, residential, excluded,
            relevant, and not-relevant counts, fractional RezoningRelevantShare,
            and review counts. With explicit period order, the second period
            also has relevant-count changes and share change in percentage
            points. Zero baselines yield null percent change. Empty residential
            populations yield null shares, but retain zero counts.
            Optional ``rezoning_rule_summary``, ``rezoning_type_summary``, and
            ``rezoning_district_summary`` report observed residential groups
            with group-local denominators; null/blank labels remain null groups.
            Review counts are null if the review flag is unavailable.

        Raises:
            TypeError: Input, flags, or audit labels have unsupported types.
            ValueError: Columns are missing/duplicated or periods are unusable.

        Note:
            Relevance is a project-defined analytical flag, not an official City
            designation or evidence of a causal policy effect. Review is an
            overlapping audit flag, not a third relevance value. Included review
            records stay in both the denominator and their assigned flag count.
            Input is never mutated, reclassified, or deduplicated.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not permits.columns.is_unique:
            raise ValueError("Input columns must be unique.")
        required = {"Period", "IncludeResidential", "RezoningRelevant"}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing rezoning fields: {sorted(required - set(permits.columns))}")
        flags = ["IncludeResidential", "RezoningRelevant"]
        if "ClassificationNeedsReview" in permits:
            flags.append("ClassificationNeedsReview")
        for flag in flags:
            if permits[flag].isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(permits[flag])):
                raise TypeError(f"{flag} must contain nonmissing Booleans.")
        if any(not isinstance(p, str) or not p.strip() for p in permits["Period"]):
            raise ValueError("Every record needs a nonblank Period.")
        periods = list(self.period_order) if self.period_order is not None else list(permits["Period"].drop_duplicates())
        if set(permits["Period"]) - set(periods):
            raise ValueError("Input contains periods outside period_order.")
        included = permits.loc[permits["IncludeResidential"].astype(bool)].copy()
        metrics = ["ResidentialCount", "RezoningRelevantCount", "NotRezoningRelevantCount",
                   "RezoningRelevantShare", "ReviewCount", "RelevantReviewCount"]
        comparison = ["BaselinePeriod", "BaselineRelevantCount", "AbsoluteChange",
                      "PercentChange", "ShareChangePercentagePoints"]
        rows = []
        for position, period in enumerate(periods):
            subset = included.loc[included["Period"].eq(period)]
            counts = _summarize(subset)
            all_count = int(permits["Period"].eq(period).sum())
            row = {"Period": period, "AllPermitCount": all_count,
                   "ExcludedCount": all_count - len(subset), **counts,
                   **dict.fromkeys(comparison)}
            if self.period_order is not None and position == 1:
                baseline = rows[0]["RezoningRelevantCount"]
                baseline_share = rows[0]["RezoningRelevantShare"]
                change = counts["RezoningRelevantCount"] - baseline
                row.update(BaselinePeriod=periods[0], BaselineRelevantCount=baseline,
                           AbsoluteChange=change, PercentChange=change * 100 / baseline if baseline else None,
                           ShareChangePercentagePoints=(counts["RezoningRelevantShare"] - baseline_share) * 100
                           if counts["ResidentialCount"] and rows[0]["ResidentialCount"] else None)
            rows.append(row)
        results = {"rezoning_summary": pd.DataFrame(rows, columns=[
            "Period", "AllPermitCount", "ExcludedCount", *metrics, *comparison,
        ]).convert_dtypes()}
        for source, label, key in (
            ("ClassificationRule", "ClassificationRule", "rezoning_rule_summary"),
            ("ResidentialType", "ResidentialType", "rezoning_type_summary"),
            (self.district_column, "LandUseDistrict", "rezoning_district_summary"),
        ):
            if source not in included:
                continue
            if any(not isinstance(v, str) for v in included[source].dropna()):
                raise TypeError(f"{source} must contain text or missing values.")
            labels = included[source].astype("string").str.strip().replace("", pd.NA)
            audit_rows = []
            for period in periods:
                mask = included["Period"].eq(period)
                for group_label, group in included.loc[mask].groupby(
                    labels.loc[mask], dropna=False, sort=True, observed=True,
                ):
                    audit_rows.append({"Period": period, label: group_label, **_summarize(group)})
            results[key] = pd.DataFrame(audit_rows, columns=["Period", label, *metrics]).convert_dtypes()
        return results


def _summarize(records: pd.DataFrame) -> dict[str, Any]:
    """Count assigned relevance while keeping review uncertainty visible.

    Args:
        records: Validated included residential records for a period or group.

    Returns:
        Residential and relevance counts, fractional share, and optional review
        counts. Review counts overlap the relevance partition.
    """
    total = len(records)
    relevant = int(records["RezoningRelevant"].sum())
    review = records.get("ClassificationNeedsReview")
    return {
        "ResidentialCount": total, "RezoningRelevantCount": relevant,
        "NotRezoningRelevantCount": total - relevant,
        "RezoningRelevantShare": relevant / total if total else None,
        "ReviewCount": int(review.sum()) if review is not None else None,
        "RelevantReviewCount": int((review & records["RezoningRelevant"]).sum()) if review is not None else None,
    }
