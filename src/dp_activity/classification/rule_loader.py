"""Load and validate data-driven classification rules.

This module validates external CSV rule definitions and converts enabled rows into
trusted domain objects.

Design Pattern:
    Factory.

Pattern Rationale:
    It validates external CSV rows and constructs trusted ClassificationRule domain
    objects, centralizing creation and conversion rules.

Typical Usage:
    Call RuleLoader.load() with the configured classification_rules.csv path at
    the composition root, then inject its ordered rules into PermitClassifier.
"""

from __future__ import annotations

import csv
from pathlib import Path
import re
from typing import cast, get_args

from .rule import ClassificationRule, InvalidRuleError, MatchType


_REQUIRED_COLUMNS = (
    "RuleID", "RuleGroup", "Field", "MatchType", "MatchValue",
    "IncludeResidential", "ResidentialType", "RezoningRelevant", "Priority",
    "Enabled", "ValidationStatus", "Notes",
)
_FIELD_ALIASES = {
    "category": "category",
    "description": "description",
    "proposedusecode": "proposedusecode",
    "proposed_use_code": "proposedusecode",
    "proposedusedescription": "proposedusedescription",
    "proposed_use_description": "proposedusedescription",
    "landusedistrict": "landusedistrict",
    "land_use_district": "landusedistrict",
}
_VALIDATION_STATUSES = frozenset({"validated_2026_sample", "provisional", "fallback", "review"})


class RuleLoader:
    """Construct validated classification rules from CSV data.

    This class is a Factory that centralizes external-row validation and conversion to
    trusted ClassificationRule value objects.
    """

    def load(self, path: Path) -> list[ClassificationRule]:
        """Return enabled rules in deterministic evaluation order.

        Args:
            path: UTF-8 CSV rule file; an optional UTF-8 byte-order mark is accepted.

        Returns:
            Enabled immutable rules sorted by (priority, rule_id). A header-only
            file or a valid file containing only disabled rules returns an empty list.

        Raises:
            OSError: The file cannot be opened or read, including a missing file.
            UnicodeError: The file is not valid UTF-8.
            InvalidRuleError: Headers, row widths, field values, IDs, regular
                expressions, or enabled duplicate-condition outcomes are invalid.

        Note:
            All rows are validated before disabled rules are excluded. Required
            headers are case-sensitive; surrounding header whitespace is ignored.
            Extra named columns are allowed but ignored. Boolean cells must be
            TRUE or FALSE after trimming. Priorities are signed decimal integers.
            Notes may be blank; all other required values must be nonblank.

            Raw classification fields and their underscore-separated equivalents
            are accepted and stored as canonical source names. Literal match text
            is trimmed, while regex patterns are preserved verbatim. Conflicts
            compare literal conditions case-insensitively, matching the project's
            default evaluation mode. Regex duplicates require identical pattern
            text; this check does not attempt to prove regex equivalence or detect
            overlap between different predicates. Outcomes include residential
            inclusion, housing type, rezoning relevance, and validation status.
        """
        source = Path(path)
        rules: list[ClassificationRule] = []
        seen_ids: set[str] = set()
        conditions: dict[tuple[str, str, str], ClassificationRule] = {}
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            try:
                headers = [name.strip() for name in next(reader, [])]
                if not headers or any(not name for name in headers):
                    raise InvalidRuleError("A nonblank header row is required.")
                if len(headers) != len(set(headers)):
                    raise InvalidRuleError("Duplicate CSV column headers are not allowed.")
                missing = set(_REQUIRED_COLUMNS) - set(headers)
                if missing:
                    raise InvalidRuleError(f"Missing required columns: {', '.join(sorted(missing))}")
                for values in reader:
                    if not values:
                        continue
                    if len(values) != len(headers):
                        raise InvalidRuleError("CSV row width does not match the header.")
                    rule = _build_rule(dict(zip(headers, values)))
                    if rule.rule_id in seen_ids:
                        raise InvalidRuleError(f"Duplicate RuleID: {rule.rule_id!r}")
                    seen_ids.add(rule.rule_id)
                    if not rule.enabled:
                        continue
                    condition = (
                        rule.field, rule.match_type,
                        rule.match_value if rule.match_type == "regex" else rule.match_value.casefold(),
                    )
                    previous = conditions.get(condition)
                    if previous is not None and _outcome(previous) != _outcome(rule):
                        raise InvalidRuleError(
                            f"Conflicting outcomes for identical conditions: "
                            f"{previous.rule_id!r} and {rule.rule_id!r}"
                        )
                    conditions[condition] = rule
                    rules.append(rule)
            except (csv.Error, InvalidRuleError, TypeError) as exc:
                raise InvalidRuleError(f"{source}: line {reader.line_num}: {exc}") from exc
        return sorted(rules, key=lambda rule: (rule.priority, rule.rule_id))


def _build_rule(row: dict[str, str]) -> ClassificationRule:
    """Translate one CSV row into a validated domain value object.

    Args:
        row: Header-keyed raw CSV cells with the required schema present.

    Returns:
        An immutable rule with canonical field names and typed Boolean/integer values.

    Raises:
        InvalidRuleError: A required cell, field, status, operation, or priority is invalid.
    """
    values = {name: row[name].strip() for name in _REQUIRED_COLUMNS}
    for name in _REQUIRED_COLUMNS:
        if name != "Notes" and not values[name]:
            raise InvalidRuleError(f"{name} must not be blank.")
    if values["Field"] not in _FIELD_ALIASES:
        raise InvalidRuleError(f"Unsupported Field: {values['Field']!r}")
    if values["ValidationStatus"] not in _VALIDATION_STATUSES:
        raise InvalidRuleError(f"Unsupported ValidationStatus: {values['ValidationStatus']!r}")
    if values["MatchType"] not in get_args(MatchType):
        raise InvalidRuleError(f"Unsupported MatchType: {values['MatchType']!r}")
    if re.fullmatch(r"[+-]?[0-9]+", values["Priority"]) is None:
        raise InvalidRuleError("Priority must be a decimal integer.")
    return ClassificationRule(
        rule_id=values["RuleID"], rule_group=values["RuleGroup"],
        field=_FIELD_ALIASES[values["Field"]],
        match_type=cast(MatchType, values["MatchType"]),
        match_value=row["MatchValue"] if values["MatchType"] == "regex" else values["MatchValue"],
        include_residential=_parse_boolean(values["IncludeResidential"], "IncludeResidential"),
        residential_type=values["ResidentialType"],
        rezoning_relevant=_parse_boolean(values["RezoningRelevant"], "RezoningRelevant"),
        priority=int(values["Priority"]), enabled=_parse_boolean(values["Enabled"], "Enabled"),
        validation_status=values["ValidationStatus"], notes=values["Notes"],
    )


def _parse_boolean(value: str, column: str) -> bool:
    """Parse explicit CSV Boolean tokens without relying on string truthiness.

    Args:
        value: Trimmed CSV value.
        column: Column name included in validation errors.

    Returns:
        True for TRUE and False for FALSE.

    Raises:
        InvalidRuleError: The value is neither TRUE nor FALSE.
    """
    if value not in {"TRUE", "FALSE"}:
        raise InvalidRuleError(f"{column} must be TRUE or FALSE.")
    return value == "TRUE"


def _outcome(rule: ClassificationRule) -> tuple[bool, str, bool, str]:
    """Return the analytical and review outcome used for conflict detection.

    Args:
        rule: Validated rule whose condition may duplicate another rule.

    Returns:
        Inclusion, housing type, relevance, and review status in a comparable tuple.
    """
    return (
        rule.include_residential, rule.residential_type,
        rule.rezoning_relevant, rule.validation_status,
    )
