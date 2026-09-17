"""Create evidence needed before finalizing cleaning and rules."""

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

