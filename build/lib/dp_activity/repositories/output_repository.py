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

import json
from pathlib import Path
from typing import Any

import pandas as pd


class OutputRepository:
    """Persist generated tables and reproducibility manifests.

    This class implements the Repository pattern so analytical code depends on
    project-level write operations rather than CSV or JSON mechanics.

    Attributes:
        output_directory: Root directory for generated artifacts.
    """

    def __init__(self, output_directory: Path, *, overwrite_outputs: bool = True) -> None:
        """Configure the generated-output repository.

        Args:
            output_directory: Root directory for generated artifacts.
            overwrite_outputs: Whether configured output paths may replace existing files.
                When false, writes use a collision-safe sibling filename.
        """
        self.output_directory = output_directory
        self.overwrite_outputs = overwrite_outputs

    def write_table(self, table: Any, filename: str) -> Path:
        """Write a DataFrame-like table atomically and return its path.

        Args:
            table: DataFrame-like table used by the operation.
            filename: Output filename relative to the configured repository directory.

        Returns:
            The completed table path.

        Raises:
            TypeError: The table does not provide the writer needed for the requested
                file extension.
            ValueError: The filename is invalid or the extension is unsupported.
        """
        target = self._target_path(filename)
        target = self._collision_safe_path(target)
        temporary_path = self._temporary_path(target)

        try:
            self._write_table_to_path(table, temporary_path, target.suffix.lower())
            temporary_path.replace(target)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return target

    def write_workbook(self, tables: dict[str, Any], filename: str) -> Path:
        """Persist related tables as sheets in one atomic Excel workbook.

        Args:
            tables: Valid Excel sheet names mapped to DataFrame-like tables.
            filename: Relative .xlsx destination; collision policy is preserved.

        Returns:
            Path of the completed workbook.

        Raises:
            ValueError: No tables are supplied or the extension is not .xlsx.
            ImportError: The optional Excel writer dependency is unavailable.
            OSError: The workbook cannot be written or replaced.
        """
        if not tables or Path(filename).suffix.lower() != ".xlsx":
            raise ValueError("A workbook requires tables and an .xlsx filename.")
        target = self._collision_safe_path(self._target_path(filename))
        temporary_path = self._temporary_path(target)
        try:
            self._write_excel(tables, temporary_path)
            temporary_path.replace(target)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return target

    @staticmethod
    def _write_excel(tables: dict[str, Any], path: Path) -> None:
        """Serialize sheets with literal source text and no implicit index.

        Args:
            tables: Sheet names mapped to tables.
            path: Temporary binary output destination.

        Raises:
            ImportError: XlsxWriter is unavailable.
            ValueError: Sheet names or table dimensions violate Excel limits.
        """
        try:
            import xlsxwriter  # noqa: F401
        except ImportError as exc:
            raise ImportError('Excel export requires pip install ".[excel]".') from exc
        with path.open("wb") as stream:
            with pd.ExcelWriter(
                stream, engine="xlsxwriter",
                engine_kwargs={"options": {
                    "strings_to_formulas": False, "strings_to_urls": False,
                }},
            ) as writer:
                for sheet, table in tables.items():
                    table.to_excel(writer, sheet_name=sheet, index=False)

    def write_manifest(self, manifest: dict[str, Any], filename: str) -> Path:
        """Record inputs, settings, Git revision, checksums, and outputs.

        Args:
            manifest: Run metadata to serialize as a reproducibility manifest.
            filename: Output filename relative to the configured repository directory.

        Returns:
            The completed manifest path.

        Raises:
            ValueError: The filename is invalid.
        """
        target = self._target_path(filename)
        target = self._collision_safe_path(target)
        temporary_path = self._temporary_path(target)

        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    manifest,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
                handle.write("\n")
            temporary_path.replace(target)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return target

    def _target_path(self, filename: str) -> Path:
        """Return a validated path under the output directory.

        Args:
            filename: Relative output filename requested by a caller.

        Returns:
            Absolute or relative path contained by the output repository.

        Raises:
            TypeError: The filename is not a string.
            ValueError: The filename is blank or escapes the output directory.
        """
        if not isinstance(filename, str):
            raise TypeError("Output filename must be a string.")
        if not filename.strip():
            raise ValueError("Output filename cannot be blank.")

        root = self.output_directory.resolve()
        target = (root / filename).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Output filename escapes the repository directory: {filename}")
        if target == root:
            raise ValueError("Output filename must identify a file, not the output directory.")

        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _collision_safe_path(self, target: Path) -> Path:
        """Return target or a numbered sibling when overwrites are disabled.

        Args:
            target: Requested output path.

        Returns:
            A writable output path.

        Raises:
            FileExistsError: Collision-safe candidates are exhausted.
        """
        if self.overwrite_outputs or not target.exists():
            return target

        for collision_index in range(1, 1000):
            candidate = target.with_name(
                f"{target.stem}_{collision_index:03d}{target.suffix}"
            )
            if not candidate.exists():
                return candidate

        raise FileExistsError(f"Could not create a collision-safe output name for {target}.")

    @staticmethod
    def _temporary_path(target: Path) -> Path:
        """Return a hidden sibling path used for atomic replacement.

        Args:
            target: Final output path.

        Returns:
            Temporary path in the same directory as the final output.
        """
        return target.with_name(f".{target.name}.tmp")

    @staticmethod
    def _write_table_to_path(table: Any, path: Path, suffix: str) -> None:
        """Serialize a table to path using the requested table format.

        Args:
            table: DataFrame-like object.
            path: Temporary destination path.
            suffix: Lowercase final output suffix.

        Raises:
            TypeError: The table does not support the requested write operation.
            ValueError: The suffix is unsupported.
            ImportError: Excel output is requested without XlsxWriter installed.
        """
        if suffix == ".xlsx":
            OutputRepository._require_writer(table, "to_excel")
            OutputRepository._write_excel({"Data": table}, path)
            return
        if suffix == ".csv":
            OutputRepository._require_writer(table, "to_csv")
            table.to_csv(path, index=False, encoding="utf-8")
            return
        if suffix == ".json":
            OutputRepository._require_writer(table, "to_json")
            table.to_json(path, orient="records", date_format="iso", indent=2)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            return
        if suffix in {".parquet", ".pq"}:
            OutputRepository._require_writer(table, "to_parquet")
            pd.DataFrame(table).to_parquet(path, index=False)
            return

        raise ValueError(f"Unsupported output table format: {suffix}")

    @staticmethod
    def _require_writer(table: Any, method_name: str) -> None:
        """Validate that a table has the requested writer method.

        Args:
            table: Candidate DataFrame-like table.
            method_name: Writer method required for the target format.

        Raises:
            TypeError: The table lacks the required writer method.
        """
        if not hasattr(table, method_name):
            raise TypeError(f"Table must provide {method_name}().")
