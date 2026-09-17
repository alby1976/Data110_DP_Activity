"""Application-to-decision processing-time features.

Design pattern:
    Functional Core / Pipes and Filters.
Why:
    A deterministic table transformation derives processing duration and validity flags without performing I/O.
"""

from __future__ import annotations

from typing import Any


def add_processing_features(
    permits: Any,
    *,
    applied_date_column: str,
    decision_date_column: str,
) -> Any:
    """Add ProcessingDays and validity/censoring flags."""
    # TODO: Subtract AppliedDate from DecisionDate in calendar days.
    # TODO: HasValidProcessingDays=true only when both dates exist and result >= 0.
    # TODO: Flag negative values separately for quality review.
    # TODO: Flag records with no decision as pending/right-censored.
    # TODO: Keep invalid rows in the dataset but exclude them from duration summaries.
    raise NotImplementedError
