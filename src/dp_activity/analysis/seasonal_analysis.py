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

from .base import Analysis


class SeasonalAnalysis(Analysis):
    """Implement the seasonal analysis strategy.

    This concrete Strategy lets the pipeline separate complete-season headline
    comparisons from partial-season context.
    """

    name = "seasonal"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare seasonality without disguising partial exposure.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Complete- and partial-season result tables keyed by stable output names.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Count residential applications by Period, Season, and SeasonStartDate.
        # TODO: Carry IsCompleteSeason into every output.
        # TODO: Produce complete-season headline comparisons.
        # TODO: Produce clearly labelled partial-season context separately.
        # TODO: Compare like calendar months as a supporting seasonality check.
        raise NotImplementedError
