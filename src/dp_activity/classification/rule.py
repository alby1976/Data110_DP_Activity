"""Domain representation of one classification rule.

This module models one immutable, auditable classification condition and its associated
analytical outcome.

Design Pattern:
    Specification and Value Object.

Pattern Rationale:
    Each immutable rule represents one reusable matching predicate plus its
    classification outcome, identified by stable rule data rather than object identity.

Typical Usage:
    RuleLoader constructs rules from validated CSV rows. PermitClassifier calls
    matches() against a source scalar, then uses the matching rule's outcome and
    audit fields. A rule does not select a winning rule or modify permit data.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal

import pandas as pd
from pandas.api.types import is_scalar

MatchType = Literal["exact", "contains", "starts_with", "regex"]


class InvalidRuleError(ValueError):
    """Indicate that a rule definition cannot form a valid matching specification."""


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

    def __post_init__(self) -> None:
        """Validate the value object's scalar fields and matching specification.

        CSV field allowlists, cross-rule conflicts, and rule-ID uniqueness belong
        to RuleLoader. This validation also protects rules constructed directly.

        Raises:
            TypeError: A field does not match its declared scalar type. Boolean
                fields must be bool, and priority must be an integer, not bool.
            InvalidRuleError: A required string is blank, match_type is unsupported,
                or the regular expression is invalid.
        """
        for name in (
            "rule_id", "rule_group", "field", "match_type", "match_value",
            "residential_type", "validation_status", "notes",
        ):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
            if name != "notes" and not value.strip():
                raise InvalidRuleError(f"{name} must not be blank.")
        for name in ("include_residential", "rezoning_relevant", "enabled"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be Boolean.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer.")
        if self.match_type not in {"exact", "contains", "starts_with", "regex"}:
            raise InvalidRuleError(f"Unsupported match type: {self.match_type!r}")
        if self.match_type == "regex":
            try:
                re.compile(self.match_value)
            except re.error as exc:
                raise InvalidRuleError(f"Rule {self.rule_id!r} has an invalid regex: {exc}") from exc

    def matches(self, value: Any, *, case_sensitive: bool = False) -> bool:
        """Return whether value satisfies this rule's matching operation.

        Args:
            value: Scalar source evidence. Nonmissing non-string scalars are
                converted to text to support numeric source codes.
            case_sensitive: Whether matching preserves letter case. Literal
                comparisons use Unicode casefold by default; regex uses IGNORECASE.

        Returns:
            True when this enabled rule matches the normalized source text.
            Disabled rules, missing values, and blank source text never match.

        Raises:
            TypeError: case_sensitive is not Boolean, or an enabled rule receives
                a nonscalar value such as a list, mapping, or Series.

        Note:
            Source text and literal match values have surrounding whitespace
            stripped. Regex patterns are preserved verbatim so escapes, character
            classes, and significant spaces retain their meaning. Regex performs
            a search anywhere in the text; use anchors for whole-field matching.
            Inline regex flags retain Python's normal semantics. Compiled patterns
            use Python's regex cache without mutating this frozen value object.
        """
        if not isinstance(case_sensitive, bool):
            raise TypeError("case_sensitive must be Boolean.")
        if not self.enabled:
            return False
        if not is_scalar(value):
            raise TypeError("Rule matching requires a scalar source value.")
        if pd.isna(value):
            return False
        text = str(value).strip()
        if not text:
            return False
        if self.match_type == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(self.match_value, flags).search(text) is not None

        expected = self.match_value.strip()
        if not case_sensitive:
            text, expected = text.casefold(), expected.casefold()
        if self.match_type == "exact":
            return text == expected
        if self.match_type == "contains":
            return expected in text
        return text.startswith(expected)
