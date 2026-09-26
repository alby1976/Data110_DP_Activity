"""Project persistence repositories.

This package contains persistence boundaries for immutable source snapshots and
generated analysis outputs.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Construct these persistence boundaries with configured directories and use them from
    orchestration code.
"""

from .output_repository import OutputRepository
from .raw_data_repository import RawDataRepository

__all__ = [
    "OutputRepository",
    "RawDataRepository",
]
