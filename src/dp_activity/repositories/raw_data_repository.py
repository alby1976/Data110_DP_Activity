"""Persistence boundary for immutable raw snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RawDataRepository:
    """Save and retrieve source snapshots plus reproducibility metadata."""

    def __init__(self, raw_directory: Path) -> None:
        self.raw_directory = raw_directory

    def save_snapshot(
        self,
        records: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> Path:
        """Write a new snapshot without changing an older snapshot."""
        # TODO: Create a timestamped, collision-safe filename.
        # TODO: Write records in the configured raw format.
        # TODO: Calculate SHA-256 after writing the data.
        # TODO: Write a sidecar metadata file containing source/query/count/checksum.
        # TODO: Return the snapshot path; never overwrite an existing snapshot.
        raise NotImplementedError

    def load_snapshot(self, snapshot_path: Path):
        """Load one named snapshot into a DataFrame."""
        # TODO: Reject missing files and unsupported extensions.
        # TODO: Load without applying cleaning or classification.
        raise NotImplementedError

