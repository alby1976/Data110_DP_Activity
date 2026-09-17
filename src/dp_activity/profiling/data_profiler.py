"""Create evidence needed before finalizing cleaning and rules.

Design pattern:
    Pipes and Filters.
Why:
    Profiling is a read-only pipeline stage that transforms source records into named evidence tables without owning persistence.
"""

from __future__ import annotations

from typing import Any


class DataProfiler:
    """Profile structure, missingness, dates, and important categories."""

    def profile(self, permits: Any, categorical_columns: list[str]) -> dict[str, Any]:
        """Return named tidy profile tables."""
        # TODO: Produce row/column counts and inferred data types.
        # TODO: Report missing count and percentage for every field.
        # TODO: Report PermitNum uniqueness and duplicate examples.
        # TODO: Report min/max/invalid counts for date fields.
        # TODO: Produce value counts for category, proposed use, district, status, etc.
        # TODO: Include examples of long descriptions for manual rule review.
        # TODO: Return tables; leave file writing to OutputRepository.
        raise NotImplementedError
