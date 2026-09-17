"""General data-quality checks and machine-readable results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualityCheckResult:
    check_name: str
    status: str
    affected_rows: int
    message: str


class DataQualityValidator:
    """Evaluate configured quality thresholds without silently repairing data."""

    def validate(self, permits: Any, settings: dict[str, Any]) -> list[QualityCheckResult]:
        """Run identifier, date, freshness, geography, and row-count checks."""
        # TODO: Count missing and duplicate PermitNum values.
        # TODO: Count invalid dates and decisions earlier than applications.
        # TODO: Measure missing community and coordinates.
        # TODO: Compare row count with minimum expected threshold.
        # TODO: Compare max AppliedDate with the configured freshness threshold.
        # TODO: Return pass/warn/fail records suitable for export.
        raise NotImplementedError

