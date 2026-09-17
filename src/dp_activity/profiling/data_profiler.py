"""Create evidence needed before finalizing cleaning and rules.

This module produces evidence tables used to evaluate source structure and refine later
cleaning and classification rules.

Design Pattern:
    Pipes and Filters.

Pattern Rationale:
    Profiling is a read-only pipeline stage that transforms source records into named
    evidence tables without owning persistence.

Typical Usage:
    Run these components against source records before finalizing cleaning and
    classification rules.
"""

from __future__ import annotations

from typing import Any


class DataProfiler:
    """Profile source structure and important data distributions.

    This class is a read-only Pipes-and-Filters stage that returns evidence tables
    without owning their persistence.
    """

    def profile(self, permits: Any, categorical_columns: list[str]) -> dict[str, Any]:
        """Return named tidy profile tables.

        Args:
            permits: DataFrame-like table of permit records.
            categorical_columns: Columns for which categorical value-count tables are required.

        Returns:
            Profile names mapped to tidy evidence tables.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Produce row/column counts and inferred data types.
        # TODO: Report missing count and percentage for every field.
        # TODO: Report PermitNum uniqueness and duplicate examples.
        # TODO: Report min/max/invalid counts for date fields.
        # TODO: Produce value counts for category, proposed use, district, status, etc.
        # TODO: Include examples of long descriptions for manual rule review.
        # TODO: Return tables; leave file writing to OutputRepository.
        raise NotImplementedError
