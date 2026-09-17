"""Meteorological season fields, including cross-year winters.

Design pattern:
    Functional Core / Pipes and Filters.
Why:
    A pure transformation owns the cross-year season algorithm so it composes cleanly with other feature stages.
"""

from __future__ import annotations

from typing import Any


def add_season_features(
    permits: Any,
    *,
    date_column: str,
    season_months: dict[str, list[int]],
    analysis_windows: list[Any],
) -> Any:
    """Add season name, start date, label, sort key, and completeness flag."""
    # TODO: Map Sep-Nov=Fall, Dec-Feb=Winter, Mar-May=Spring, Jun-Aug=Summer.
    # TODO: For Jan/Feb, set season start to December 1 of the previous year.
    # TODO: Format Winter labels like "Winter 2024–25".
    # TODO: Use SeasonStartDate as the chronological sort key.
    # TODO: Determine whether all days of the season fall within its analysis window.
    # TODO: Flag seasons split by the August policy boundaries as partial.
    raise NotImplementedError
