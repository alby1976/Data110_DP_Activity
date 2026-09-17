"""Permit-volume analysis.

This module calculates total and monthly residential permit volumes, including explicit
zero-activity months.

Design Pattern:
    Strategy.

Pattern Rationale:
    It provides the volume-calculation algorithm as an interchangeable pipeline
    analysis.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from typing import Any

from .base import Analysis


class VolumeAnalysis(Analysis):
    """Implement the volume analysis strategy.

    This concrete Strategy lets the pipeline calculate total and monthly residential
    permit activity, including zero-activity months.
    """

    name = "volume"

    def run(self, permits: Any) -> dict[str, Any]:
        """Calculate total and monthly residential application counts.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Total and monthly volume tables keyed by stable output names.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Filter IncludeResidential=true and keep denominator counts.
        # TODO: Count applications by Period and YearMonth.
        # TODO: Calculate mean/median monthly count using explicit zero months.
        # TODO: Calculate absolute and percent change; blank percent when baseline=0.
        # TODO: Return permit_volume and monthly_volume tables.
        raise NotImplementedError
