"""Export stable, tidy tables for Power BI.

Design pattern:
    Adapter.
Why:
    It converts project-owned tables into the stable CSV schemas and conventions expected by Power BI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class PowerBIExporter:
    """Write analysis outputs with explicit schemas and reconciliation metadata."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def export(
        self,
        permit_table: Any,
        analysis_tables: dict[str, Any],
        validation_tables: dict[str, Any],
    ) -> dict[str, Path]:
        """Export configured CSV files and return logical-name/path mappings."""
        # TODO: Define required columns and order for every exported table.
        # TODO: Format dates as ISO values and Booleans consistently.
        # TODO: Write clean_permits plus each summary/validation table as UTF-8 CSV.
        # TODO: Add a reconciliation table with Python headline totals.
        # TODO: Reject accidental index columns and duplicate column names.
        # TODO: Return all output paths for inclusion in the run manifest.
        raise NotImplementedError
