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

import pandas as pd

@dataclass(frozen=True)
class SchemaIssue:
    """Record one immutable schema finding.

    Attributes:
        severity: ``error`` for unusable structure or missing requirements;
            ``info`` for additional columns retained as evidence.
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

    Supply ``validate`` with configured required columns through a callable such
    as ``functools.partial`` when injecting it into the pipeline. Column names
    are matched exactly; source-field translation belongs to the cleaner.
    """

    def validate(self, table: Any, required_columns: list[str]) -> list[SchemaIssue]:
        """Inspect column structure without modifying the input table.

        Args:
            table: Pandas DataFrame to inspect. Unsupported table objects produce
                a table-level error finding.
            required_columns: Nonblank, unique column names from configuration.
                This is a minimum schema, not an exhaustive allowed-column list.

        Returns:
            Immutable findings ordered by invalid labels, duplicate names,
            missing requirements, then additional columns. An empty list means
            the table has exactly the required, unambiguous column names.

        Raises:
            TypeError: Required columns are not a list of strings.
            ValueError: Required names are blank or duplicated.

        Note:
            Empty tables can have valid schemas. Null or duplicate identifier
            values, field types, and invalid dates are data-quality concerns;
            they are not inferred from column names here. Source evidence and
            derived columns are reported as information, never removed.
        """
        if not isinstance(required_columns, list) or any(
            not isinstance(name, str) for name in required_columns
        ):
            raise TypeError("required_columns must be a list of strings.")
        if any(not name.strip() for name in required_columns):
            raise ValueError("Required column names cannot be blank.")
        if len(set(required_columns)) != len(required_columns):
            raise ValueError("Required column names must be unique.")

        if not isinstance(table, pd.DataFrame):
            return [SchemaIssue("error", None, "Expected a pandas DataFrame.")]

        issues: list[SchemaIssue] = []
        names: list[str] = []
        for position, name in enumerate(table.columns):
            if not isinstance(name, str) or not name.strip():
                issues.append(SchemaIssue(
                    "error", None,
                    f"Column at position {position} must have a nonblank string name.",
                ))
            else:
                names.append(name)

        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in names:
            if name in seen and name not in duplicates:
                issues.append(SchemaIssue(
                    "error", name, f"Column '{name}' appears more than once.",
                ))
                duplicates.add(name)
            seen.add(name)

        for name in required_columns:
            if name not in seen:
                issues.append(SchemaIssue(
                    "error", name, f"Required column '{name}' is missing.",
                ))

        required = set(required_columns)
        for name in dict.fromkeys(names):
            if name not in required:
                issues.append(SchemaIssue(
                    "info", name, f"Additional column '{name}' is outside the required schema.",
                ))
        return issues
