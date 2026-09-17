"""Create consistent, accessible charts from analysis tables.

Design pattern:
    Factory.
Why:
    It centralizes figure construction and styling so callers request a chart type without duplicating plotting setup.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ChartFactory:
    """Render charts only from finalized tidy analysis tables."""

    def __init__(self, style: dict[str, Any] | None = None) -> None:
        self.style = style or {}

    def monthly_volume(self, table: Any):
        """Build a period-aware monthly volume chart."""
        # TODO: Validate required columns.
        # TODO: Use consistent period colors and readable date ticks.
        # TODO: Mark policy boundaries and label partial periods.
        # TODO: Return the Figure; do not save implicitly.
        raise NotImplementedError

    def save(self, figure: Any, path: Path) -> Path:
        """Save one chart with reproducible dimensions and accessible resolution."""
        # TODO: Validate extension, create parent directory, and save with tight bounds.
        raise NotImplementedError
