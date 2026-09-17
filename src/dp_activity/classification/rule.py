"""Domain representation of one classification rule.

This module models one immutable, auditable classification condition and its associated
analytical outcome.

Design Pattern:
    Specification and Value Object.

Pattern Rationale:
    Each immutable rule represents one reusable matching predicate plus its
    classification outcome, identified by stable rule data rather than object identity.

Typical Usage:
    Import and use these components during the permit-classification stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MatchType = Literal["exact", "contains", "starts_with", "regex"]


@dataclass(frozen=True)
class ClassificationRule:
    """Represent one immutable and auditable classification rule.

    This value object also acts as a Specification: matches() evaluates one reusable
    predicate, while the remaining attributes describe the resulting classification.

    Attributes:
        rule_id: Stable identifier recorded in classification audit fields.
        rule_group: Logical family used to organize related rules.
        field: Source evidence field evaluated by the rule.
        match_type: Supported comparison operation.
        match_value: Text or pattern compared with a source value.
        include_residential: Whether matching records enter residential analyses.
        residential_type: Housing-form classification assigned on a match.
        rezoning_relevant: Whether a match is analytically relevant to rezoning.
        priority: Evaluation order; lower values run first.
        enabled: Whether the rule is eligible for evaluation.
        validation_status: Evidence status attached to the rule.
        notes: Human-readable context for maintainers and reviewers.
    """

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
        """Return whether value satisfies this rule's matching operation.

        Args:
            value: Source value evaluated by the rule.
            case_sensitive: Whether matching preserves letter case.

        Returns:
            True when the source value satisfies this rule; otherwise False.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Treat missing values as non-matches.
        # TODO: Normalize surrounding whitespace and optionally case.
        # TODO: Implement exact, contains, starts_with, and compiled regex.
        # TODO: Raise a project-specific error for an unsupported match type.
        raise NotImplementedError
