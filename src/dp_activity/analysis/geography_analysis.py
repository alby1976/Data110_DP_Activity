"""Community and ward analysis."""

from __future__ import annotations

from typing import Any

from .base import Analysis


class GeographyAnalysis(Analysis):
    name = "geography"

    def __init__(self, minimum_baseline_count: int) -> None:
        self.minimum_baseline_count = minimum_baseline_count

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare permit activity by community and ward."""
        # TODO: Keep missing geography visible and report its denominator impact.
        # TODO: Count residential permits by Period, Community, and Ward.
        # TODO: Pivot Before/During counts and calculate absolute change.
        # TODO: Calculate percent change only where baseline is non-zero.
        # TODO: Add SmallBaselineWarning; do not delete small communities.
        # TODO: Return community and ward tables suitable for maps/Power BI.
        raise NotImplementedError

