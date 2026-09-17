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

from .base import Analysis


class TypeAnalysis(Analysis):
    """Implement the type analysis strategy.

    This concrete Strategy lets the pipeline compare residential development-type
    counts and shares across policy periods.
    """

    name = "type"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare counts and shares by classified residential type.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Residential-type result tables keyed by stable output names.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Filter included residential records.
        # TODO: Group by Period and ResidentialType.
        # TODO: Calculate counts, period denominator, and TypeShare.
        # TODO: Retain Review/Unknown categories rather than hiding them.
        # TODO: Calculate changes with baseline-zero handling.
        raise NotImplementedError
