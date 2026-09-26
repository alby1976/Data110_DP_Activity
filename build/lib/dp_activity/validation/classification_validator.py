"""Validate rule coverage and classification reliability.

This module measures classification coverage, overlap, review burden, and labelled-
sample reliability.

Design Pattern:
    Strategy and Result Table.

Pattern Rationale:
    It encapsulates one replaceable validation algorithm and returns structured findings
    that can be exported or interpreted by the pipeline.

Typical Usage:
    Run these components at the appropriate pipeline boundary and retain their
    structured findings.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from dp_activity.classification.rule import ClassificationRule

_AUDIT_COLUMNS = (
    "ValidationStatus", "ClassificationConflictCount", "ClassificationMatchCount",
    "ClassificationMatchedRules", "ResidentialType", "IncludeResidential", "RezoningRelevant",
)

class ClassificationValidator:
    """Evaluate classification coverage and reliability.

    This class is a validation Strategy that returns structured findings for export or
    pipeline policy decisions.

    Bind the supplied rules to ``validate`` using ``functools.partial`` for
    pipeline injection. The result table is independent of the input and does
    not modify classifications or decide whether execution should stop.
    """

    def validate(
        self, classified_permits: Any, rules: list[Any], *,
        audit_label_column: str | None = None,
    ) -> Any:
        """Return a tidy validation report.

        Args:
            classified_permits: Permit table containing classification outcomes and audit fields.
            rules: Classification rules used to validate recorded outcomes.
                Disabled rules remain recognizable but cannot be valid matches.
            audit_label_column: Optional column of independent human-reviewed
                residential-type labels. Null or blank labels are excluded;
                labels are compared exactly with ``ResidentialType``.

        Returns:
            DataFrame with one ``summary`` row and, when requested, one
            ``confusion`` row per observed expected/predicted class pair.
            Summary count percentages use all input records; audit accuracy
            uses only labelled records. Undefined rates and unavailable metrics
            are nullable, never invented zeroes. ``status`` is fail for missing
            audit columns, unknown/disabled rule IDs, or inconsistent audit
            evidence; warn for unmatched/review records or human-label errors;
            otherwise pass. Overlap alone is informational. ``message`` explains
            the assessment. Confusion rows use ``record_count`` and leave
            summary metrics null so totals are not repeated.

        Raises:
            TypeError: Input/rules have unsupported types.
            ValueError: Required core fields are absent, columns/rule IDs repeat,
                audit values are malformed, or the label column is unavailable.

        Note:
            Coverage measures rule matching, not classification accuracy. Audit
            consistency checks compare stored outcomes and match order with
            supplied rules; they do not rerun predicates on source evidence.
            An empty input has no measurable coverage and receives a warning.
        """
        if not isinstance(classified_permits, pd.DataFrame):
            raise TypeError("classified_permits must be a pandas DataFrame.")
        if not isinstance(rules, list) or any(not isinstance(r, ClassificationRule) for r in rules):
            raise TypeError("rules must be a list of ClassificationRule objects.")
        if len({r.rule_id for r in rules}) != len(rules):
            raise ValueError("Rule IDs must be unique.")
        table = classified_permits
        if not table.columns.is_unique or any(
            not isinstance(name, str) or not name.strip() for name in table.columns
        ):
            raise ValueError("Column names must be unique nonblank strings.")
        core = {"ClassificationRule", "ClassificationNeedsReview"}
        if not core.issubset(table.columns):
            raise ValueError(f"Missing core classification fields: {sorted(core - set(table.columns))}")
        for column in ("ClassificationNeedsReview", "IncludeResidential", "RezoningRelevant"):
            if column in table and (
                table[column].isna().any()
                or (len(table) and not pd.api.types.is_bool_dtype(table[column]))
            ):
                raise ValueError(f"{column} must contain nonmissing Booleans.")
        for column in ("ClassificationRule", "ValidationStatus", "ResidentialType"):
            if column in table:
                for value in table[column]:
                    if column == "ClassificationRule" and pd.api.types.is_scalar(value) and pd.isna(value):
                        continue
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{column} must contain nonblank strings.")
        for column in ("ClassificationMatchCount", "ClassificationConflictCount"):
            if column in table and len(table) and (
                not pd.api.types.is_integer_dtype(table[column])
                or pd.api.types.is_bool_dtype(table[column])
                or table[column].isna().any() or table[column].lt(0).any()
            ):
                raise ValueError(f"{column} must contain nonnegative integers.")
        if "ClassificationMatchedRules" in table:
            for value in table["ClassificationMatchedRules"]:
                if not isinstance(value, (tuple, list)) or any(
                    not isinstance(item, str) or not item.strip() for item in value
                ):
                    raise ValueError("ClassificationMatchedRules must contain lists/tuples of rule IDs.")

        by_id = {r.rule_id: r for r in rules}
        missing = [name for name in _AUDIT_COLUMNS if name not in table]
        unmatched = int(table["ClassificationRule"].isna().sum())
        review = int(table["ClassificationNeedsReview"].sum())
        unknown = disabled = inconsistent = 0
        for row in table.to_dict("records"):
            winner_id = row["ClassificationRule"]
            has_winner = not pd.isna(winner_id)
            matched_ids = row.get("ClassificationMatchedRules", [])
            recorded = set(matched_ids) | ({winner_id} if has_winner else set())
            unknown += bool(recorded - by_id.keys())
            disabled += any(not by_id[item].enabled for item in recorded if item in by_id)
            bad = not has_winner and not row["ClassificationNeedsReview"]
            winner = by_id.get(winner_id) if has_winner else None
            if winner is not None:
                expected = {
                    "ValidationStatus": winner.validation_status,
                    "ResidentialType": winner.residential_type,
                    "IncludeResidential": winner.include_residential,
                    "RezoningRelevant": winner.rezoning_relevant,
                    "ClassificationNeedsReview": winner.validation_status in {"review", "provisional", "fallback"},
                }
                bad |= any(row[name] != value for name, value in expected.items() if name in row)
            elif not has_winner:
                bad |= any(row[name] != value for name, value in {
                    "ValidationStatus": "unmatched", "IncludeResidential": False,
                    "RezoningRelevant": False, "ClassificationMatchCount": 0,
                    "ClassificationConflictCount": 0,
                }.items() if name in row)
            if "ClassificationMatchedRules" in row:
                bad |= len(set(matched_ids)) != len(matched_ids)
                bad |= (not matched_ids or matched_ids[0] != winner_id) if has_winner else bool(matched_ids)
                if all(item in by_id for item in matched_ids):
                    ordered = sorted(matched_ids, key=lambda item: (by_id[item].priority, item))
                    bad |= list(matched_ids) != ordered
                for name, expected_count in (
                    ("ClassificationMatchCount", len(matched_ids)),
                    ("ClassificationConflictCount", max(0, len(matched_ids) - 1)),
                ):
                    if name in row:
                        bad |= row[name] != expected_count
            inconsistent += bool(bad)

        total = len(table)
        summary = {
            "report_type": "summary", "status": "pass", "record_count": total,
            "matched_count": total - unmatched, "unmatched_count": unmatched,
            "coverage_percentage": (total - unmatched) * 100 / total if total else None,
            "unmatched_percentage": unmatched * 100 / total if total else None,
            "review_count": review, "review_percentage": review * 100 / total if total else None,
            "overlap_count": int(table["ClassificationConflictCount"].gt(0).sum()) if "ClassificationConflictCount" in table else None,
            "additional_match_count": int(table["ClassificationConflictCount"].sum()) if "ClassificationConflictCount" in table else None,
            "unknown_rule_count": unknown, "disabled_rule_count": disabled,
            "inconsistent_audit_count": inconsistent, "missing_audit_columns": ", ".join(missing),
            "enabled_rule_count": sum(r.enabled for r in rules),
            "audit_count": None, "audit_error_count": None, "audit_accuracy_percentage": None,
            "expected_type": None, "predicted_type": None,
        }
        for status in ("review", "provisional", "fallback"):
            summary[f"{status}_status_count"] = (
                int(table["ValidationStatus"].eq(status).sum()) if "ValidationStatus" in table else None
            )

        confusion: list[dict[str, Any]] = []
        if audit_label_column is not None:
            if not isinstance(audit_label_column, str) or not audit_label_column.strip():
                raise ValueError("audit_label_column must be a nonblank column name.")
            if audit_label_column not in table or "ResidentialType" not in table:
                raise ValueError("Audit requires the label column and ResidentialType.")
            labels = table[audit_label_column]
            if any(not isinstance(value, str) for value in labels.dropna()):
                raise ValueError("Audit labels must be strings or missing.")
            labelled = labels.notna() & labels.fillna("").str.strip().ne("")
            audit = table.loc[labelled, [audit_label_column, "ResidentialType"]].copy()
            if audit_label_column == "ResidentialType":
                raise ValueError("Independent audit labels must not use ResidentialType itself.")
            audit.columns = ["expected_type", "predicted_type"]
            errors = int(audit["expected_type"].ne(audit["predicted_type"]).sum())
            summary.update(audit_count=len(audit), audit_error_count=errors,
                           audit_accuracy_percentage=(len(audit) - errors) * 100 / len(audit) if len(audit) else None)
            for (expected, predicted), count in audit.groupby(["expected_type", "predicted_type"], sort=True).size().items():
                confusion.append({
                    "report_type": "confusion", "status": "pass" if expected == predicted else "warn",
                    "expected_type": expected, "predicted_type": predicted, "record_count": int(count),
                    "message": "Observed independently labelled class pair; not population accuracy.",
                })
        if missing or unknown or disabled or inconsistent:
            summary["status"] = "fail"
        elif not total or unmatched or review or summary["audit_error_count"]:
            summary["status"] = "warn"
        summary["message"] = (
            f"{total} records; {unmatched} unmatched; {review} need review; "
            f"{unknown} reference unknown rules; {disabled} reference disabled rules; "
            f"{inconsistent} have inconsistent audit fields. "
            f"Missing audit columns: {', '.join(missing) or 'none'}. "
            "Coverage is not accuracy; overlapping rules are not automatically contradictory."
        )
        return pd.DataFrame([summary, *confusion]).convert_dtypes()
