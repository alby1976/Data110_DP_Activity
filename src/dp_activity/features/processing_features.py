"""Application-to-decision processing-time features.

This module derives processing durations, validity indicators, and right-censoring flags
without performing input/output.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A deterministic table transformation derives processing duration and validity flags
    without performing I/O.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from __future__ import annotations

from typing import Any


def add_processing_features(
    permits: Any,
    *,
    applied_date_column: str,
    decision_date_column: str,
) -> Any:
    """Add ProcessingDays and validity/censoring flags.

    Args:
        permits: DataFrame-like table of permit records.
        applied_date_column: Name of the cleaned application-date column.
        decision_date_column: Name of the cleaned decision-date column.

    Returns:
        A copy of the permit table with duration and validity fields.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Subtract AppliedDate from DecisionDate in calendar days.
    # TODO: HasValidProcessingDays=true only when both dates exist and result >= 0.
    # TODO: Flag negative values separately for quality review.
    # TODO: Flag records with no decision as pending/right-censored.
    # TODO: Keep invalid rows in the dataset but exclude them from duration summaries.
    raise NotImplementedError
