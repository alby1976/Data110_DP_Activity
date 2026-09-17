"""Residential development-type analysis.

Design pattern:
    Strategy.
Why:
    It isolates residential-type count and share calculations behind the common Analysis interface.
"""

from __future__ import annotations

from typing import Any

from .base import Analysis


class TypeAnalysis(Analysis):
    name = "type"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare counts and shares by classified residential type."""
        # TODO: Filter included residential records.
        # TODO: Group by Period and ResidentialType.
        # TODO: Calculate counts, period denominator, and TypeShare.
        # TODO: Retain Review/Unknown categories rather than hiding them.
        # TODO: Calculate changes with baseline-zero handling.
        raise NotImplementedError
