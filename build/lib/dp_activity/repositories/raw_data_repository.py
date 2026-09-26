"""Persistence boundary for immutable raw snapshots.

This module stores and retrieves immutable source snapshots together with
reproducibility metadata.

Design Pattern:
    Repository.

Pattern Rationale:
    It separates immutable snapshot storage and retrieval from acquisition and analysis
    logic.

Typical Usage:
    Construct these persistence boundaries with configured directories and use them from
    orchestration code.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pandas import DataFrame

from dp_activity.adapters.file_format_adapter import SocrataFileWriter


class RawDataRepository:
    """Persist and retrieve immutable source snapshots.

    This class implements the Repository pattern and separates raw-data storage,
    checksums, and metadata sidecars from acquisition and analysis logic.

    Attributes:
        raw_directory: Root directory for immutable snapshots and sidecars.
    """

    def __init__(
        self,
        raw_directory: Path,
        *,
        file_format: str = "csv",
        base_name: str = "development_permits",
        writer: SocrataFileWriter | None = None,
    ) -> None:
        """Configure the repository root and raw snapshot format.

        Args:
            raw_directory: Directory where immutable snapshots and sidecars are stored.
            file_format: File format extension or adapter alias for new snapshots.
            base_name: Filename stem used before the UTC timestamp.
            writer: Optional file writer strategy used to serialize records.

        Raises:
            ValueError: The file format or base name is blank.
        """
        normalized_format = file_format.strip().lower().lstrip(".")
        normalized_base_name = base_name.strip()
        if not normalized_format:
            raise ValueError("Raw snapshot file format cannot be blank.")
        if not normalized_base_name:
            raise ValueError("Raw snapshot base name cannot be blank.")

        self.raw_directory = raw_directory
        self.file_format = normalized_format
        self.base_name = normalized_base_name
        self.writer = writer or SocrataFileWriter()

    def save_snapshot(
        self,
        records: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> Path:
        """Write a new snapshot without changing an older snapshot.

        Args:
            records: Iterable of mapping-like Socrata records.
            metadata: Source and retrieval facts stored beside the snapshot.

        Returns:
            The newly created immutable snapshot path.

        Raises:
            FileExistsError: A matching snapshot path already exists after collision
                attempts are exhausted.
        """
        self.raw_directory.mkdir(parents=True, exist_ok=True)
        snapshot_path = self._next_snapshot_path()
        self.writer.save(records, snapshot_path, adapter=self.file_format)

        checksum = self._sha256(snapshot_path)
        sidecar_path = snapshot_path.with_suffix(f"{snapshot_path.suffix}.metadata.json")
        sidecar = {
            **metadata,
            "row_count": len(records),
            "snapshot_file": snapshot_path.name,
            "sha256": checksum,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with sidecar_path.open("w", encoding="utf-8") as handle:
            json.dump(
                sidecar,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            handle.write("\n")

        return snapshot_path

    def load_snapshot(self, snapshot_path: Path) -> DataFrame:
        """Load one named snapshot into a DataFrame.

        Args:
            snapshot_path: Path identifying the immutable source snapshot to process.

        Returns:
            A DataFrame containing the unmodified snapshot records.

        Raises:
            FileNotFoundError: The snapshot path does not exist.
            ValueError: The snapshot extension is not supported.
        """
        path = Path(snapshot_path)
        if not path.exists():
            raise FileNotFoundError(f"Raw snapshot does not exist: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"Raw snapshot path is a directory: {path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            return cast(pd.DataFrame, pd.read_csv(path))
        if suffix == ".json":
            return pd.read_json(path)
        if suffix in {".parquet", ".pq"}:
            return pd.read_parquet(path)

        raise ValueError(f"Unsupported raw snapshot format: {suffix}")

    def _next_snapshot_path(self) -> Path:
        """Return a timestamped path that does not overwrite an existing snapshot.

        Returns:
            A path under the raw repository directory.

        Raises:
            FileExistsError: All collision-safe candidate names already exist.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = f".{self.file_format}"
        candidate = self.raw_directory / f"{self.base_name}_{timestamp}{suffix}"
        if not candidate.exists():
            return candidate

        for collision_index in range(1, 1000):
            candidate = (
                self.raw_directory
                / f"{self.base_name}_{timestamp}_{collision_index:03d}{suffix}"
            )
            if not candidate.exists():
                return candidate

        raise FileExistsError(
            f"Could not create a collision-safe raw snapshot name in {self.raw_directory}."
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        """Calculate the SHA-256 checksum for a completed snapshot.

        Args:
            path: Snapshot file to hash.

        Returns:
            Lowercase hexadecimal SHA-256 digest.
        """
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
