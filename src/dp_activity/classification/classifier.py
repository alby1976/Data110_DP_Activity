"""Apply ordered rules and produce classification audit fields.

This module applies ordered rules to permit evidence and retains coverage, conflict, and
review fields for auditability.

Design Pattern:
    Chain of Responsibility.

Pattern Rationale:
    Ordered rules are tried in priority order until the first match handles a record;
    later matches are still counted for conflict auditing.

Typical Usage:
    Inject loaded rules and source-to-cleaned field mappings, then classify a
    cleaned DataFrame. Pass coverage_report() tables to the output repository;
    classification itself performs no I/O.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .rule import ClassificationRule

_OUTPUT_DTYPES = {
    "ClassificationRule": "string", "ValidationStatus": "string",
    "IncludeResidential": "bool", "ResidentialType": "string", "RezoningRelevant": "bool",
    "ClassificationNeedsReview": "bool", "ClassificationMatchCount": "int64",
    "ClassificationConflictCount": "int64", "ClassificationMatchedRules": "object",
}
_REVIEW_STATUSES = frozenset({"review", "provisional", "fallback"})


class PermitClassifier:
    """Apply ordered classification rules with auditable outcomes.

    This class implements a Chain of Responsibility: rules are evaluated in priority
    order, the first match determines the outcome, and additional matches remain
    available for conflict reporting.

    Attributes:
        rules: Ordered classification rules.
        field_map: Rule-field names mapped to permit-table column names.
        unmatched_action: Outcome assigned when no rule matches.
        case_sensitive: Whether rule matching preserves letter case.
    """

    def __init__(
        self,
        rules: list[ClassificationRule],
        field_map: dict[str, str],
        unmatched_action: str = "Review",
        *,
        case_sensitive: bool = False,
    ) -> None:
        """Build a deterministic chain from enabled immutable rules.

        Args:
            rules: Rule definitions; enabled rules are sorted by priority and ID.
            field_map: Rule-field names mapped explicitly to input columns.
            unmatched_action: Nonblank ResidentialType label for unmatched records.
                This label never causes records to be dropped or included by default.
            case_sensitive: Boolean case-matching policy supplied by configuration.

        Raises:
            TypeError: Rules, mappings, labels, or case policy have invalid types.
            ValueError: Rule IDs repeat or labels/mapping names are blank.
        """
        if not isinstance(rules, list) or any(not isinstance(rule, ClassificationRule) for rule in rules):
            raise TypeError("rules must be a list of ClassificationRule objects.")
        if len({rule.rule_id for rule in rules}) != len(rules):
            raise ValueError("Classification rule IDs must be unique.")
        if not isinstance(field_map, dict) or any(
            not isinstance(name, str) for pair in field_map.items() for name in pair
        ):
            raise TypeError("field_map must map string field names to string column names.")
        if any(not name.strip() for pair in field_map.items() for name in pair):
            raise ValueError("field_map names must not be blank.")
        if not isinstance(unmatched_action, str):
            raise TypeError("unmatched_action must be a string label.")
        if not unmatched_action.strip():
            raise ValueError("unmatched_action must not be blank.")
        if not isinstance(case_sensitive, bool):
            raise TypeError("case_sensitive must be Boolean.")
        self.rules = tuple(sorted(
            (rule for rule in rules if rule.enabled), key=lambda rule: (rule.priority, rule.rule_id)
        ))
        self.field_map = dict(field_map)
        self.unmatched_action = unmatched_action.strip()
        self.case_sensitive = case_sensitive

    def classify(self, permits: Any) -> Any:
        """Return permits with residential, type, relevance, and audit columns.

        Args:
            permits: pandas DataFrame containing all fields used by enabled rules.

        Returns:
            A copy preserving source columns, row order, and index, followed by
            ClassificationRule, ValidationStatus, IncludeResidential,
            ResidentialType, RezoningRelevant, ClassificationNeedsReview,
            ClassificationMatchCount, ClassificationConflictCount, and
            ClassificationMatchedRules (an ordered tuple of every matching ID).

        Raises:
            TypeError: Input is not a DataFrame, column names are not strings,
                or source evidence passed to a rule is nonscalar.
            ValueError: Columns are duplicated, a required mapping/column is
                absent, or an existing audit column would be overwritten.

        Note:
            The first match wins. All later matches are still evaluated for
            audit; ConflictCount is the number of additional matches, including
            same-outcome overlaps. It signals potential ambiguity, not proven
            contradictory outcomes. Overlaps are reported separately because
            fallback and catch-all rules intentionally overlap specific rules.
            Winning rules with review, provisional, or fallback status require review.

            Unmatched rows have a missing rule ID, status "unmatched", the
            configured type label, false inclusion/relevance, zero match counts,
            and NeedsReview=true. They remain available for later rule review.
        """
        _validate_frame(permits)
        collisions = set(permits.columns) & set(_OUTPUT_DTYPES)
        if collisions:
            raise ValueError(f"Classification columns already exist: {sorted(collisions)}")
        for rule in self.rules:
            if rule.field not in self.field_map:
                raise ValueError(f"No field mapping for rule {rule.rule_id!r}: {rule.field!r}")
            if self.field_map[rule.field] not in permits.columns:
                raise ValueError(f"Missing input column for rule {rule.rule_id!r}: {self.field_map[rule.field]!r}")
        columns = list(dict.fromkeys(self.field_map[rule.field] for rule in self.rules))
        positions = {name: index for index, name in enumerate(columns)}
        audit: dict[str, list[Any]] = {name: [] for name in _OUTPUT_DTYPES}
        # Use positional tuples so duplicate index labels and numeric source types
        # do not change which evidence is evaluated for a permit.
        source_rows = (
            permits[columns].itertuples(index=False, name=None)
            if columns else (() for _ in range(len(permits)))
        )
        for row in source_rows:
            matches = [
                rule for rule in self.rules
                if rule.matches(row[positions[self.field_map[rule.field]]], case_sensitive=self.case_sensitive)
            ]
            winner = matches[0] if matches else None
            values = {
                "ClassificationRule": winner.rule_id if winner else pd.NA,
                "ValidationStatus": winner.validation_status if winner else "unmatched",
                "IncludeResidential": winner.include_residential if winner else False,
                "ResidentialType": winner.residential_type if winner else self.unmatched_action,
                "RezoningRelevant": winner.rezoning_relevant if winner else False,
                "ClassificationNeedsReview": (
                    winner is None or winner.validation_status in _REVIEW_STATUSES
                ),
                "ClassificationMatchCount": len(matches),
                "ClassificationConflictCount": max(0, len(matches) - 1),
                "ClassificationMatchedRules": tuple(rule.rule_id for rule in matches),
            }
            for name, value in values.items():
                audit[name].append(value)
        result = permits.copy(deep=True)
        for name, dtype in _OUTPUT_DTYPES.items():
            result[name] = pd.Series(audit[name], dtype=dtype).array
        return result

    def coverage_report(self, classified_permits: Any) -> Any:
        """Summarize matches, unmatched rows, review states, and conflicts.

        Args:
            classified_permits: Permit table containing classification outcomes and audit fields.

        Returns:
            Observed groups by ClassificationRule, ValidationStatus,
            ClassificationNeedsReview, and Period when present. Counts are
            record_count, matched_count, unmatched_count, conflict_count (rows
            with additional matches), and additional_match_count (total later
            matches). record_percentage uses all input rows as its denominator.
            Missing rule IDs and periods remain explicit groups; unused rules
            are not synthesized into zero-count groups.

        Raises:
            TypeError: Input is not a DataFrame or column names are not strings.
            ValueError: Input has duplicated names or lacks required audit columns.
        """
        _validate_frame(classified_permits)
        groups = ["ClassificationRule", "ValidationStatus", "ClassificationNeedsReview"]
        required = groups + ["ClassificationConflictCount"]
        missing = set(required) - set(classified_permits.columns)
        if missing:
            raise ValueError(f"Missing classification audit columns: {sorted(missing)}")
        if "Period" in classified_permits:
            groups.append("Period")
        counts = ["record_count", "matched_count", "unmatched_count", "conflict_count", "additional_match_count"]
        if classified_permits.empty:
            return pd.DataFrame(columns=groups + counts + ["record_percentage"])
        working = classified_permits[groups].copy()
        working["record_count"] = 1
        working["matched_count"] = classified_permits["ClassificationRule"].notna().astype(int)
        working["unmatched_count"] = classified_permits["ClassificationRule"].isna().astype(int)
        working["conflict_count"] = classified_permits["ClassificationConflictCount"].gt(0).astype(int)
        working["additional_match_count"] = classified_permits["ClassificationConflictCount"]
        result = working.groupby(groups, dropna=False, sort=False, observed=True)[counts].sum().reset_index()
        result["record_percentage"] = result["record_count"] * 100 / len(classified_permits)
        return result


def _validate_frame(permits: Any) -> None:
    """Reject ambiguous input tables before classification or aggregation.

    Args:
        permits: Candidate permit DataFrame.

    Raises:
        TypeError: Input is not a DataFrame or column names are not strings.
        ValueError: Column names are duplicated.
    """
    if not isinstance(permits, pd.DataFrame):
        raise TypeError("permits must be a pandas DataFrame.")
    if any(not isinstance(column, str) for column in permits.columns):
        raise TypeError("Permit column names must be strings.")
    if not permits.columns.is_unique:
        raise ValueError("Permit column names must be unique.")
