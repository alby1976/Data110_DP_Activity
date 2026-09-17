"""Policy-period features based on the configured primary date.

This module assigns policy periods and boundary-audit fields from the configured primary
date.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A side-effect-free transformation adds period fields to a table, making the rule
    deterministic, composable, and easy to test at boundaries.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from __future__ import annotations

from typing import Any


def add_period_features(
    permits: Any,
    *,
    date_column: str,
    periods: list[Any],
) -> Any:
    """Add Period and policy-boundary audit fields.

    Args:
        permits: DataFrame-like table of permit records.
        date_column: Name of the cleaned date column used to derive features.
        periods: Ordered, non-overlapping policy-period definitions.

    Returns:
        A copy of the permit table with policy-period and boundary fields.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Validate periods are inclusive, ordered, and non-overlapping.
    # TODO: Assign each valid date to Before, During, Early Post-Repeal, or Outside.
    # TODO: Keep missing/invalid dates explicit rather than guessing a period.
    # TODO: Add a stable categorical sort order.
    # TODO: Flag applications whose decision crosses a policy boundary.
    raise NotImplementedError
