"""Validate rule coverage and classification reliability."""

from __future__ import annotations

from typing import Any


class ClassificationValidator:
    """Check coverage, overlap, review burden, and labelled audit samples."""

    def validate(self, classified_permits: Any, rules: list[Any]) -> Any:
        """Return a tidy validation report."""
        # TODO: Count matched/unmatched records and coverage percentage.
        # TODO: Count potential multi-rule conflicts hidden by first-match priority.
        # TODO: Count review, provisional, and fallback outcomes separately.
        # TODO: Confirm every recorded RuleID exists in the supplied rule set.
        # TODO: If a labelled audit sample exists, build a confusion matrix by class.
        # TODO: Report errors and rates; do not claim a rule is valid from its label alone.
        raise NotImplementedError

