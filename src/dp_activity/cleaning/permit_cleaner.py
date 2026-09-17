"""Deterministic cleaning for City development-permit records."""

from __future__ import annotations

from typing import Any


class PermitCleaner:
    """Standardize source data without making analytical classifications."""

    def __init__(self, column_map: dict[str, str], date_columns: list[str]) -> None:
        self.column_map = column_map
        self.date_columns = date_columns

    def clean(self, permits: Any) -> Any:
        """Return a cleaned copy and preserve traceability to source values."""
        # TODO: Copy the input; never mutate the caller's DataFrame.
        # TODO: Normalize API column names through the explicit tested map.
        # TODO: Preserve original category/use/description/district fields.
        # TODO: Trim text; convert empty strings to missing values.
        # TODO: Parse configured dates with invalid-value flags.
        # TODO: Normalize numeric coordinates without inventing missing values.
        # TODO: Do not silently drop duplicates or invalid records.
        # TODO: Return columns in a stable documented order.
        raise NotImplementedError

