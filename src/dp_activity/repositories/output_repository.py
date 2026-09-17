"""Persistence boundary for generated tables and run manifests.

This module isolates generated-table and manifest persistence from analysis logic.

Design Pattern:
    Repository.

Pattern Rationale:
    It hides filesystem persistence behind project-level write operations so analysis
    code does not depend on CSV or JSON mechanics.

Typical Usage:
    Construct these persistence boundaries with configured directories and use them from
    orchestration code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class OutputRepository:
    """Persist generated tables and reproducibility manifests.

    This class implements the Repository pattern so analytical code depends on
    project-level write operations rather than CSV or JSON mechanics.

    Attributes:
        output_directory: Root directory for generated artifacts.
    """

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def write_table(self, table: Any, filename: str) -> Path:
        """Write a DataFrame-like table atomically and return its path.

        Args:
            table: DataFrame-like table used by the operation.
            filename: Output filename relative to the configured repository directory.

        Returns:
            The completed table path.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Validate filename and keep it inside output_directory.
        # TODO: Write to a temporary sibling file, then replace the target.
        # TODO: Use stable column order, UTF-8, and no implicit index.
        raise NotImplementedError

    def write_manifest(self, manifest: dict[str, Any], filename: str) -> Path:
        """Record inputs, settings, Git revision, checksums, and outputs.

        Args:
            manifest: Run metadata to serialize as a reproducibility manifest.
            filename: Output filename relative to the configured repository directory.

        Returns:
            The completed manifest path.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Serialize JSON with sorted keys and readable indentation.
        raise NotImplementedError
