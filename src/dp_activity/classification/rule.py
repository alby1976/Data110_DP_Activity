"""Domain representation of one classification rule.

Design pattern:
    Specification and Value Object.
Why:
    Each immutable rule represents one reusable matching predicate plus its classification outcome, identified by stable rule data rather than object identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MatchType = Literal["exact", "contains", "starts_with", "regex"]


@dataclass(frozen=True)
class ClassificationRule:
    """One ordered and auditable rule from classification_rules.csv."""

    rule_id: str
    rule_group: str
    field: str
    match_type: MatchType
    match_value: str
    include_residential: bool
    residential_type: str
    rezoning_relevant: bool
    priority: int
    enabled: bool
    validation_status: str
    notes: str

    def matches(self, value: Any, *, case_sensitive: bool = False) -> bool:
        """Return whether value satisfies this rule's matching operation."""
        # TODO: Treat missing values as non-matches.
        # TODO: Normalize surrounding whitespace and optionally case.
        # TODO: Implement exact, contains, starts_with, and compiled regex.
        # TODO: Raise a project-specific error for an unsupported match type.
        raise NotImplementedError
