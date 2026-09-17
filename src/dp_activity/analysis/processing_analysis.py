"""Processing-time analysis."""

from __future__ import annotations

from typing import Any

from .base import Analysis


class ProcessingAnalysis(Analysis):
    name = "processing"

    def run(self, permits: Any) -> dict[str, Any]:
        """Summarize valid application-to-decision intervals."""
        # TODO: Report all rows, valid rows, pending rows, and invalid rows by Period.
        # TODO: Restrict duration statistics to HasValidProcessingDays=true.
        # TODO: Calculate count, median, mean, Q1, and Q3.
        # TODO: Add breakdowns by ResidentialType and optional community.
        # TODO: Label right-censoring: undecided recent applications are not random missingness.
        raise NotImplementedError

