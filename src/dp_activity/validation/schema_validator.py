"""Validate source and processed table schemas.

Design pattern:
    Strategy and Result Object.
Why:
    It isolates schema validation from transformation code and returns structured issues that callers can decide to warn on or treat as fatal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaIssue:
    severity: str
    column: str | None
    message: str


class SchemaValidator:
    """Check required columns, supported types, and key availability."""

    def validate(self, table: Any, required_columns: list[str]) -> list[SchemaIssue]:
        """Return issues; callers decide whether errors stop the pipeline."""
        # TODO: Report missing required columns as errors.
        # TODO: Report unexpected columns as information, not automatic failure.
        # TODO: Check PermitNum exists and is usable as the expected identifier.
        # TODO: Check configured date/geography/classification evidence fields.
        raise NotImplementedError
