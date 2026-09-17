"""Analysis of the transparent rezoning-relevance flag.

Design pattern:
    Strategy.
Why:
    It isolates the analytical rezoning-relevance comparison while remaining interchangeable with the other analysis components.
"""

from __future__ import annotations

from typing import Any

from .base import Analysis


class RezoningAnalysis(Analysis):
    name = "rezoning"

    def run(self, permits: Any) -> dict[str, Any]:
        """Compare rezoning-relevant counts and shares by policy period."""
        # TODO: Filter included residential permits.
        # TODO: Count RezoningRelevant=true/false/review by Period.
        # TODO: Calculate share using all classified residential permits as denominator.
        # TODO: Break results down by rule, housing type, and district for auditability.
        # TODO: Label the flag as analytical, not an official City designation.
        raise NotImplementedError
