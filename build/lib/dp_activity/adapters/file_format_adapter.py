"""Save Socrata records through interchangeable file-format adapters.

This module defines a common persistence contract, concrete CSV, JSON, GeoJSON,
and Parquet adapters, reflective adapter discovery, and runtime adapter selection.

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
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

Record = Mapping[str, Any]
FILENAME_TOKEN_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _parse_optional_float(value: Any) -> float | None:
    """Return a finite float for coordinate values, or None when unusable.

    Args:
        value: Candidate coordinate value from a source record.

    Returns:
        A finite floating-point coordinate, or None for missing, blank, Boolean,
        non-numeric, infinite, or NaN values.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coordinate):
        return None
    return coordinate


class FileFormatAdapter(ABC):
    """Define the contract for output-format adapters.

    This abstract class participates in the Adapter and Strategy patterns. Concrete
    adapters translate project-owned records into a specific file representation,
    while callers depend only on the shared save operation.

    Attributes:
        extensions: Lowercase file suffixes supported by the adapter.
    """

    extensions: tuple[str, ...] = ()

    def __init__(self, extensions: Iterable[str] | None = None) -> None:
        """Validate and store the file extensions supported by this adapter.

        Args:
            extensions: Optional extension list used by dynamically configured
                adapters. When omitted, the subclass's ``extensions`` class attribute
                defines the supported suffixes.

        Raises:
            TypeError: An extension is not a string.
            ValueError: No extensions are configured, or an extension is blank.
        """
        configured_extensions = tuple(extensions or self.extensions)
        if not configured_extensions:
            raise ValueError("File format adapters must declare at least one extension.")

        normalized_extensions: list[str] = []
        for extension in configured_extensions:
            if not isinstance(extension, str):
                raise TypeError("File format adapter extensions must be strings.")

            normalized_extension = extension.strip().lower()
            if not normalized_extension:
                raise ValueError("File format adapter extensions cannot be blank.")
            if not normalized_extension.startswith("."):
                normalized_extension = f".{normalized_extension}"
            normalized_extensions.append(normalized_extension)

        self.extensions = tuple(dict.fromkeys(normalized_extensions))

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

    @staticmethod
    def materialize_records(records: Iterable[Record]) -> list[dict[str, Any]]:
        """Return concrete row dictionaries after validating record shape.

        Args:
            records: Iterable of mapping-like Socrata records.

        Returns:
            A list of plain dictionaries suitable for serialization.

        Raises:
            TypeError: A supplied record is not mapping-like.
        """
        rows: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise TypeError(f"Record at position {index} must be a mapping.")
            rows.append(dict(record))
        return rows


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
        rows = self.materialize_records(records)
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
        rows = self.materialize_records(records)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
        return path


class JsonGeoFileAdapter(FileFormatAdapter):
    """Adapt records to a GeoJSON FeatureCollection.

    This concrete Adapter translates records with latitude and longitude fields
    into GeoJSON features while preserving each original record as feature
    properties. Rows without usable coordinates are retained with a null geometry
    so export completeness remains auditable.

    Attributes:
        extensions: GeoJSON-oriented suffixes supported by this adapter.
        latitude_field: Record field that contains latitude values.
        longitude_field: Record field that contains longitude values.
    """

    extensions = (".geojson", ".jgeojson", ".jsongeo")

    def __init__(
        self,
        *,
        latitude_field: str = "latitude",
        longitude_field: str = "longitude",
    ) -> None:
        """Configure coordinate field names for GeoJSON conversion.

        Args:
            latitude_field: Record field that contains latitude values.
            longitude_field: Record field that contains longitude values.

        Raises:
            ValueError: A coordinate field name is blank.
        """
        super().__init__()
        if not latitude_field.strip() or not longitude_field.strip():
            raise ValueError("GeoJSON coordinate field names cannot be blank.")
        self.latitude_field = latitude_field
        self.longitude_field = longitude_field

    def save(self, records: Iterable[Record], output_path: Path) -> Path:
        """Write records as a GeoJSON FeatureCollection.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized GeoJSON.

        Returns:
            The completed GeoJSON path.

        Raises:
            IsADirectoryError: The requested output path is a directory.
            TypeError: A supplied record is not mapping-like.
        """
        path = self.prepare_output_path(output_path)
        rows = self.materialize_records(records)
        feature_collection = {
            "type": "FeatureCollection",
            "features": [self._record_to_feature(row) for row in rows],
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(feature_collection, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
        return path

    def _record_to_feature(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return one GeoJSON feature for a materialized record.

        Args:
            record: Plain record dictionary.

        Returns:
            A GeoJSON feature with point geometry when coordinates are valid;
            otherwise a feature with null geometry.
        """
        latitude = _parse_optional_float(record.get(self.latitude_field))
        longitude = _parse_optional_float(record.get(self.longitude_field))
        geometry = None
        if latitude is not None and longitude is not None:
            geometry = {
                "type": "Point",
                "coordinates": [longitude, latitude],
            }

        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": dict(record),
        }


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
            pd.DataFrame(self.materialize_records(records)).to_parquet(path, index=False)
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
            "geojson": JsonGeoFileAdapter,
            "jgeojson": JsonGeoFileAdapter,
            "jsongeo": JsonGeoFileAdapter,
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
        if not isinstance(adapter_spec, str):
            raise TypeError("Adapter specification must be a string.")

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
        except ValueError as exc:
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
        include_timestamp: bool = False,
        label: str | None = None,
        data_period: str | None = None,
        timestamp_format: str = "%Y%m%d_%H%M%S",
        now: datetime | None = None,
    ) -> Path:
        """Save records using an explicit adapter or infer one from the file extension.

        Args:
            records: Iterable of mapping-like Socrata records.
            output_path: Destination path for the serialized records.
            adapter: Adapter alias, reflected class path, adapter instance, or None for extension-
                based selection.
            adapter_options: Keyword arguments passed to a newly constructed adapter.
            include_timestamp: Whether to append the current UTC date/time to
                the output filename before the extension.
            label: Optional filename label inserted before the timestamp when
                include_timestamp is true.
            data_period: Optional data-period label inserted before the timestamp
                when include_timestamp is true.
            timestamp_format: ``strftime`` pattern used when include_timestamp is true.
            now: Optional datetime used for deterministic tests.

        Returns:
            The path written by the selected adapter.

        Raises:
            ValueError: Adapter selection is invalid or adapter options conflict with an instance.
            TypeError: adapter is not a supported selector or adapter instance.
        """
        path = Path(output_path)
        if adapter is None:
            if adapter_options:
                raise ValueError("adapter_options require an explicit adapter name.")
            selected = self.factory.create_for_path(path)
        elif isinstance(adapter, str):
            selected = self.factory.create(adapter, **dict(adapter_options or {}))
        elif isinstance(adapter, FileFormatAdapter):
            if adapter_options:
                raise ValueError("adapter_options cannot be used with an adapter instance.")
            selected = adapter
        else:
            raise TypeError("adapter must be a name, FileFormatAdapter instance, or None.")

        if include_timestamp:
            path = self._timestamped_output_path(
                path,
                label=label,
                data_period=data_period,
                timestamp_format=timestamp_format,
                now=now,
            )

        return selected.save(records, path)

    @staticmethod
    def _timestamped_output_path(
        output_path: Path,
        *,
        label: str | None = None,
        data_period: str | None = None,
        timestamp_format: str,
        now: datetime | None = None,
    ) -> Path:
        """Return output_path with optional label, period, and UTC timestamp.

        Args:
            output_path: Destination path requested by the caller.
            label: Optional filename label inserted after the base stem.
            data_period: Optional data-period label inserted after label.
            timestamp_format: ``strftime`` pattern used to format the timestamp.
            now: Optional datetime used for deterministic tests.

        Returns:
            A sibling path whose filename includes filename-safe suffix parts.

        Raises:
            ValueError: A filename part is blank after normalization, or the
                timestamp format is blank or creates path separators.
            TypeError: The timestamp format or filename part has an unexpected type.
        """
        if not isinstance(timestamp_format, str):
            raise TypeError("timestamp_format must be a string.")
        if not timestamp_format.strip():
            raise ValueError("timestamp_format cannot be blank.")

        timestamp_source = now or datetime.now(timezone.utc)
        timestamp = timestamp_source.strftime(timestamp_format)
        if not timestamp:
            raise ValueError("timestamp_format produced an empty timestamp.")
        if any(separator in timestamp for separator in ("/", "\\")):
            raise ValueError("timestamp_format must not produce path separators.")

        filename_parts = [output_path.stem]
        if label is not None:
            filename_parts.append(_normalize_filename_token(label, field_name="label"))
        if data_period is not None:
            filename_parts.append(
                _normalize_filename_token(data_period, field_name="data_period")
            )
        filename_parts.append(timestamp)

        return output_path.with_name(f"{'_'.join(filename_parts)}{output_path.suffix}")


def _normalize_filename_token(value: str, *, field_name: str) -> str:
    """Return a filesystem-safe filename token for user-facing labels.

    Args:
        value: User-facing filename component.
        field_name: Field name used in validation messages.

    Returns:
        A stripped token where whitespace and punctuation runs are replaced with
        underscores.

    Raises:
        TypeError: The value is not a string.
        ValueError: The value is blank or contains no filename-safe characters.
    """
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    normalized = FILENAME_TOKEN_PATTERN.sub("_", value.strip()).strip("._-")
    if not normalized:
        raise ValueError(f"{field_name} must contain filename-safe characters.")
    return normalized
