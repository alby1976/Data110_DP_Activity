"""Save Socrata records through interchangeable file-format adapters.

This module defines a common persistence contract, concrete CSV, JSON, and Parquet
adapters, reflective adapter discovery, and runtime adapter selection.

Design Pattern:
    Adapter, Strategy, and Reflective Factory.

Pattern Rationale:
    Each format adapter translates project-owned Socrata records into one external file
    representation. The writer selects an adapter at runtime, while the factory uses
    Python reflection to load approved adapter subclasses without adding format-specific
    branches to the Socrata client or analysis pipeline.

Typical Usage:
    Import and use these components when acquiring or persisting external Socrata
    records.
"""

from __future__ import annotations

import csv
import importlib
import inspect
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

Record = Mapping[str, Any]


class FileFormatAdapter(ABC):
    """Define the contract for output-format adapters.

    This abstract class participates in the Adapter and Strategy patterns. Concrete
    adapters translate project-owned records into a specific file representation,
    while callers depend only on the shared save operation.

    Attributes:
        extensions: Lowercase file suffixes supported by the adapter.
    """

    extensions: tuple[str, ...] = ()

    @abstractmethod
    def save(self, records: Iterable[Record], output_path: Path) -> Path:
        """Write records to output_path and return the completed path.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.

        Returns:
            The completed output path.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        raise NotImplementedError

    @classmethod
    def supports(cls, output_path: Path) -> bool:
        """Return whether this adapter supports the file's lowercase suffix.

        Args:
            output_path: Destination path for the serialized records.

        Returns:
            True when the path suffix is supported; otherwise False.
        """
        return output_path.suffix.lower() in cls.extensions

    @staticmethod
    def prepare_output_path(output_path: Path) -> Path:
        """Create the parent directory and reject directory targets.

        Args:
            output_path: Destination path for the serialized records.

        Returns:
            The normalized output path with an existing parent directory.

        Raises:
            IsADirectoryError: The requested output path already exists as a directory.
        """
        path = Path(output_path)
        if path.exists() and path.is_dir():
            raise IsADirectoryError(f"Output path is a directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class CsvFileAdapter(FileFormatAdapter):
    """Adapt records to a UTF-8 CSV file.

    This concrete Adapter preserves the union of source fields in first-seen order so
    heterogeneous Socrata records can be written through the common file-format
    contract.
    """

    extensions = (".csv",)

    def save(self, records: Iterable[Record], output_path: Path) -> Path:
        """Write records as a UTF-8 CSV file.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.

        Returns:
            The completed CSV path.

        Raises:
            IsADirectoryError: The requested output path is a directory.
        """
        rows = [dict(record) for record in records]
        path = self.prepare_output_path(output_path)
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))

        with path.open("w", encoding="utf-8", newline="") as handle:
            if fieldnames:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

        return path


class JsonFileAdapter(FileFormatAdapter):
    """Adapt records to a readable UTF-8 JSON array.

    This concrete Adapter converts project records to JSON while preserving non-ASCII
    text and providing a stable, human-readable representation.
    """

    extensions = (".json",)

    def save(self, records: Iterable[Record], output_path: Path) -> Path:
        """Write records as a readable UTF-8 JSON array.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.

        Returns:
            The completed JSON path.

        Raises:
            IsADirectoryError: The requested output path is a directory.
        """
        path = self.prepare_output_path(output_path)
        rows = [dict(record) for record in records]
        with path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
        return path


class ParquetFileAdapter(FileFormatAdapter):
    """Adapt records to a Parquet table.

    This concrete Adapter delegates columnar serialization to pandas and an installed
    Parquet engine while preserving the common file-format contract.
    """

    extensions = (".parquet", ".pq")

    def save(self, records: Iterable[Record], output_path: Path) -> Path:
        """Write records as a Parquet table.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.

        Returns:
            The completed Parquet path.

        Raises:
            IsADirectoryError: The requested output path is a directory.
            RuntimeError: pandas or a compatible Parquet engine is unavailable.
        """
        path = self.prepare_output_path(output_path)
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - pandas is a project dependency
            raise RuntimeError("Parquet output requires pandas.") from exc

        try:
            pd.DataFrame([dict(record) for record in records]).to_parquet(path, index=False)
        except ImportError as exc:
            raise RuntimeError(
                "Parquet output requires an engine such as pyarrow or fastparquet."
            ) from exc
        return path


class ReflectiveFileAdapterFactory:
    """Create built-in or reflected file-format adapters.

    This class implements a reflective Factory. It centralizes alias registration and
    safe class validation so new adapters can be loaded without adding
    format-specific branches to the writer.

    Attributes:
        _aliases: Case-insensitive names mapped to validated adapter classes.
    """

    def __init__(self) -> None:
        self._aliases: dict[str, type[FileFormatAdapter]] = {
            "csv": CsvFileAdapter,
            "json": JsonFileAdapter,
            "parquet": ParquetFileAdapter,
            "pq": ParquetFileAdapter,
        }

    def register(self, alias: str, adapter_class: type[FileFormatAdapter]) -> None:
        """Register a validated adapter class under a case-insensitive alias.

        Args:
            alias: Case-insensitive name used to register the adapter.
            adapter_class: Concrete FileFormatAdapter subclass to register.

        Raises:
            ValueError: The normalized alias is blank.
            TypeError: adapter_class is not a concrete FileFormatAdapter subclass.
        """
        normalized = alias.strip().lower().lstrip(".")
        if not normalized:
            raise ValueError("Adapter alias cannot be blank.")
        self._validate_adapter_class(adapter_class)
        self._aliases[normalized] = adapter_class

    def create(self, adapter_spec: str, **adapter_options: Any) -> FileFormatAdapter:
        """Create an adapter from an alias or ``package.module:ClassName`` specification.

        Args:
            adapter_spec: Registered alias or import path identifying an adapter class.
            adapter_options: Keyword arguments passed to a newly constructed adapter.

        Returns:
            A newly constructed adapter.

        Raises:
            ValueError: The specification is blank or cannot be imported.
            TypeError: The resolved object is not a concrete FileFormatAdapter subclass.
        """
        normalized = adapter_spec.strip()
        if not normalized:
            raise ValueError("Adapter specification cannot be blank.")

        alias = normalized.lower().lstrip(".")
        adapter_class = self._aliases.get(alias)
        if adapter_class is None:
            adapter_class = self._load_class(normalized)

        self._validate_adapter_class(adapter_class)
        return adapter_class(**adapter_options)

    def create_for_path(self, output_path: Path) -> FileFormatAdapter:
        """Infer a built-in adapter from the output filename extension.

        Args:
            output_path: Destination path for the serialized records.

        Returns:
            A newly constructed built-in adapter for the path suffix.

        Raises:
            ValueError: The path has no suffix or no adapter is registered for it.
        """
        suffix = Path(output_path).suffix.lower().lstrip(".")
        if not suffix:
            raise ValueError("Output path must have an extension or an adapter must be specified.")
        try:
            return self.create(suffix)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"No file adapter is registered for '.{suffix}'.") from exc

    @staticmethod
    def _load_class(adapter_spec: str) -> type[FileFormatAdapter]:
        """Load an adapter class from an import specification.

        Args:
            adapter_spec: Registered alias or import path identifying an adapter class.

        Returns:
            The object resolved from the specified module and class name.

        Raises:
            ValueError: The specification is malformed or cannot be imported.
        """
        module_name, separator, class_name = adapter_spec.partition(":")
        if not separator:
            module_name, separator, class_name = adapter_spec.rpartition(".")
        if not module_name or not separator or not class_name:
            raise ValueError(
                "Custom adapter must use 'package.module:ClassName' or a dotted class path."
            )

        try:
            module = importlib.import_module(module_name)
            candidate = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            raise ValueError(f"Cannot load file adapter '{adapter_spec}'.") from exc
        return candidate

    @staticmethod
    def _validate_adapter_class(candidate: Any) -> None:
        """Validate that a reflected object is a concrete adapter class.

        Args:
            candidate: Object resolved through reflection and proposed as an adapter class.

        Raises:
            TypeError: The candidate is not a concrete FileFormatAdapter subclass.
        """
        if not inspect.isclass(candidate) or not issubclass(candidate, FileFormatAdapter):
            raise TypeError("Reflected adapter must be a FileFormatAdapter subclass.")
        if inspect.isabstract(candidate):
            raise TypeError("Reflected adapter must implement save().")


class SocrataFileWriter:
    """Save Socrata records through a selected file-format adapter.

    This class is the context for the file-format Strategy and delegates adapter
    construction to ReflectiveFileAdapterFactory.

    Attributes:
        factory: Factory used to select or construct output adapters.
    """

    def __init__(self, factory: ReflectiveFileAdapterFactory | None = None) -> None:
        self.factory = factory or ReflectiveFileAdapterFactory()

    def save(
        self,
        records: Iterable[Record],
        output_path: Path,
        *,
        adapter: str | FileFormatAdapter | None = None,
        adapter_options: Mapping[str, Any] | None = None,
    ) -> Path:
        """Save records using an explicit adapter or infer one from the file extension.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.
            adapter: Adapter alias, reflected class path, adapter instance, or None for extension-
                based selection.
            adapter_options: Keyword arguments passed to a newly constructed adapter.

        Returns:
            The path written by the selected adapter.

        Raises:
            ValueError: Adapter selection is invalid or adapter options conflict with an instance.
            TypeError: adapter is not a supported selector or adapter instance.
        """
        path = Path(output_path)
        if adapter is None:
            selected = self.factory.create_for_path(path)
        elif isinstance(adapter, str):
            selected = self.factory.create(adapter, **dict(adapter_options or {}))
        elif isinstance(adapter, FileFormatAdapter):
            if adapter_options:
                raise ValueError("adapter_options cannot be used with an adapter instance.")
            selected = adapter
        else:
            raise TypeError("adapter must be a name, FileFormatAdapter instance, or None.")

        return selected.save(records, path)
