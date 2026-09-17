"""Seasonal permit analysis."""

from __future__ import annotations

from typing import Any

from .base import Analysis


class SeasonalAnalysis(Analysis):
    name = "seasonal"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare seasonality without disguising partial exposure."""
        # TODO: Count residential applications by Period, Season, and SeasonStartDate.
        # TODO: Carry IsCompleteSeason into every output.
        # TODO: Produce complete-season headline comparisons.
        # TODO: Produce clearly labelled partial-season context separately.
        # TODO: Compare like calendar months as a supporting seasonality check.
        raise NotImplementedError

