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

from .base import Analysis


class GeographyAnalysis(Analysis):
    """Implement the geography analysis strategy.

    This concrete Strategy lets the pipeline compare permit activity by community and
    ward while retaining missing geography and small-baseline warnings.

    Attributes:
        minimum_baseline_count: Count below which a community baseline is flagged.
    """

    name = "geography"

    def __init__(self, minimum_baseline_count: int) -> None:
        self.minimum_baseline_count = minimum_baseline_count

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare permit activity by community and ward.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Community and ward summary tables keyed by stable output names.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Keep missing geography visible and report its denominator impact.
        # TODO: Count residential permits by Period, Community, and Ward.
        # TODO: Pivot Before/During counts and calculate absolute change.
        # TODO: Calculate percent change only where baseline is non-zero.
        # TODO: Add SmallBaselineWarning; do not delete small communities.
        # TODO: Return community and ward tables suitable for maps/Power BI.
        raise NotImplementedError
