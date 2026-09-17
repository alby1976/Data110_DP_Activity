"""Apply ordered rules and produce classification audit fields."""

from __future__ import annotations

from typing import Any

from .rule import ClassificationRule


class PermitClassifier:
    """First-match classifier with conflict and unmatched reporting."""

    def __init__(
        self,
        rules: list[ClassificationRule],
        field_map: dict[str, str],
        unmatched_action: str = "Review",
    ) -> None:
        self.rules = rules
        self.field_map = field_map
        self.unmatched_action = unmatched_action

    def classify(self, permits: Any) -> Any:
        """Return permits with residential, type, relevance, and audit columns."""
        # TODO: Verify every rule field maps to an available DataFrame column.
        # TODO: For each record, evaluate all rules in configured order.
        # TODO: Select the first match while counting additional matches as conflicts.
        # TODO: Write ClassificationRule and rule ValidationStatus.
        # TODO: Write IncludeResidential, ResidentialType, RezoningRelevant.
        # TODO: Mark unmatched/review/provisional/fallback records for review.
        # TODO: Preserve original evidence fields beside derived outcomes.
        raise NotImplementedError

    def coverage_report(self, classified_permits: Any) -> Any:
        """Summarize matches, unmatched rows, review states, and conflicts."""
        # TODO: Group by rule, period (when available), and review status.
        raise NotImplementedError

