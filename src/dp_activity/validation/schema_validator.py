"""Validate source and processed table schemas.

This module identifies source or processed schema issues and leaves stop-or-warn policy
to its caller.

Design Pattern:
    Strategy and Result Object.

Pattern Rationale:
    It isolates schema validation from transformation code and returns structured issues
    that callers can decide to warn on or treat as fatal.

Typical Usage:
    Run these components at the appropriate pipeline boundary and retain their
    structured findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaIssue:
    """Record one immutable schema finding.

    Attributes:
        severity: Machine-readable importance assigned to the issue.
        column: Related column name, or None for table-level findings.
        message: Human-readable explanation of the issue.
    """

    severity: str
    column: str | None
    message: str


class SchemaValidator:
    """Evaluate required columns and supported table structure.

    This class is a validation Strategy that reports structured issues and leaves
    stop-or-warn policy to the caller.
    """

    def validate(self, table: Any, required_columns: list[str]) -> list[SchemaIssue]:
        """Return issues; callers decide whether errors stop the pipeline.

        Args:
            table: DataFrame-like table used by the operation.
            required_columns: Column names that must be present in the table.

        Returns:
            Structured schema issues; an empty list indicates no findings.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Report missing required columns as errors.
        # TODO: Report unexpected columns as information, not automatic failure.
        # TODO: Check PermitNum exists and is usable as the expected identifier.
        # TODO: Check configured date/geography/classification evidence fields.
        raise NotImplementedError
