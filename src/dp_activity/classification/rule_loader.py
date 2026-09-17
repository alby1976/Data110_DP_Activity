"""Load and validate data-driven classification rules.

Design pattern:
    Factory.
Why:
    It validates external CSV rows and constructs trusted ClassificationRule domain objects, centralizing creation and conversion rules.
"""

from __future__ import annotations

from pathlib import Path

from .rule import ClassificationRule


class RuleLoader:
    """Translate the CSV rule table into validated domain objects."""

    def load(self, path: Path) -> list[ClassificationRule]:
        """Return enabled rules in deterministic evaluation order."""
        # TODO: Read CSV and require every documented column.
        # TODO: Reject blank/duplicate RuleID values and invalid priorities.
        # TODO: Parse Booleans strictly rather than relying on truthy strings.
        # TODO: Validate MatchType, ValidationStatus, and supported Field values.
        # TODO: Compile regex patterns to find syntax errors early.
        # TODO: Detect duplicate conditions with conflicting outcomes.
        # TODO: Build ClassificationRule objects.
        # TODO: Filter Enabled=true and sort by (Priority, RuleID).
        raise NotImplementedError
