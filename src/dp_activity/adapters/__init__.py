"""External-service and file-format adapters.

This package exposes adapters that isolate Socrata access and output-format details from
the rest of the application.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Import and use these components when acquiring or persisting external Socrata
    records.
"""

from .file_format_adapter import (
    CsvFileAdapter,
    FileFormatAdapter,
    JsonGeoFileAdapter,
    JsonFileAdapter,
    ParquetFileAdapter,
    ReflectiveFileAdapterFactory,
    SocrataFileWriter,
)

__all__ = [
    "CsvFileAdapter",
    "FileFormatAdapter",
    "JsonGeoFileAdapter",
    "JsonFileAdapter",
    "ParquetFileAdapter",
    "ReflectiveFileAdapterFactory",
    "SocrataFileWriter",
]
