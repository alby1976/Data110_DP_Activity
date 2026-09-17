"""Meteorological season fields, including cross-year winters.

This module derives meteorological seasons, including winters that cross calendar years
and season-completeness flags.

Design Pattern:
    Functional Core / Pipes and Filters.

Pattern Rationale:
    A pure transformation owns the cross-year season algorithm so it composes cleanly
    with other feature stages.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
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
    """Add season name, start date, label, sort key, and completeness flag.

    Args:
        permits: DataFrame-like table of permit records.
        date_column: Name of the cleaned date column used to derive features.
        season_months: Season names mapped to their constituent month numbers.
        analysis_windows: Configured date windows used to determine season completeness.

    Returns:
        A copy of the permit table with season and completeness fields.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Map Sep-Nov=Fall, Dec-Feb=Winter, Mar-May=Spring, Jun-Aug=Summer.
    # TODO: For Jan/Feb, set season start to December 1 of the previous year.
    # TODO: Format Winter labels like "Winter 2024–25".
    # TODO: Use SeasonStartDate as the chronological sort key.
    # TODO: Determine whether all days of the season fall within its analysis window.
    # TODO: Flag seasons split by the August policy boundaries as partial.
    raise NotImplementedError
