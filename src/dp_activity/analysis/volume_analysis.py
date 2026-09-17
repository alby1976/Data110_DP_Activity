"""Permit-volume analysis."""

from __future__ import annotations

from typing import Any

from .base import Analysis


class VolumeAnalysis(Analysis):
    name = "volume"

    def run(self, permits: Any) -> dict[str, Any]:
        """Calculate total and monthly residential application counts."""
        # TODO: Filter IncludeResidential=true and keep denominator counts.
        # TODO: Count applications by Period and YearMonth.
        # TODO: Calculate mean/median monthly count using explicit zero months.
        # TODO: Calculate absolute and percent change; blank percent when baseline=0.
        # TODO: Return permit_volume and monthly_volume tables.
        raise NotImplementedError

