"""Analysis-output exporters.

This package contains output adapters that prepare finalized project tables for
downstream reporting tools.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Use these components after validation to prepare stable downstream reporting files.
"""

from .powerbi_exporter import PowerBIExporter

__all__ = [
    "PowerBIExporter",
]
