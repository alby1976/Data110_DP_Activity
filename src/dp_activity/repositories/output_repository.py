"""Persistence boundary for generated tables and run manifests.

Design pattern:
    Repository.
Why:
    It hides filesystem persistence behind project-level write operations so analysis code does not depend on CSV or JSON mechanics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class OutputRepository:
    """Write reproducible outputs using names supplied by configuration."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def write_table(self, table: Any, filename: str) -> Path:
        """Write a DataFrame-like table atomically and return its path."""
        # TODO: Validate filename and keep it inside output_directory.
        # TODO: Write to a temporary sibling file, then replace the target.
        # TODO: Use stable column order, UTF-8, and no implicit index.
        raise NotImplementedError

    def write_manifest(self, manifest: dict[str, Any], filename: str) -> Path:
        """Record inputs, settings, Git revision, checksums, and outputs."""
        # TODO: Serialize JSON with sorted keys and readable indentation.
        raise NotImplementedError
