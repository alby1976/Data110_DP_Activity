"""Policy-period features based on the configured primary date.

Design pattern:
    Functional Core / Pipes and Filters.
Why:
    A side-effect-free transformation adds period fields to a table, making the rule deterministic, composable, and easy to test at boundaries.
"""

from __future__ import annotations

from typing import Any


def add_period_features(
    permits: Any,
    *,
    date_column: str,
    periods: list[Any],
) -> Any:
    """Add Period and policy-boundary audit fields."""
    # TODO: Validate periods are inclusive, ordered, and non-overlapping.
    # TODO: Assign each valid date to Before, During, Early Post-Repeal, or Outside.
    # TODO: Keep missing/invalid dates explicit rather than guessing a period.
    # TODO: Add a stable categorical sort order.
    # TODO: Flag applications whose decision crosses a policy boundary.
    raise NotImplementedError
