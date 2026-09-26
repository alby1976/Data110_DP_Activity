"""General data-quality checks and machine-readable results.

This module evaluates configured data-quality checks and reports structured results
without silently repairing records.

Design Pattern:
    Strategy and Result Object.

Pattern Rationale:
    It packages configurable quality checks as one validation strategy and returns
    explicit immutable results instead of printing or silently repairing data.

Typical Usage:
    Run these components at the appropriate pipeline boundary and retain their
    structured findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

@dataclass(frozen=True)
class QualityCheckResult:
    """Record one immutable data-quality finding.

    Attributes:
        check_name: Stable name of the executed check.
        status: Machine-readable ``pass``, ``warn``, or ``fail`` state.
        affected_rows: Number of affected records, counting all members of a
            duplicate group. Zero for a schema prerequisite failure or an empty
            table; consult status and message rather than the count alone.
        message: Human-readable explanation of the result.
    """

    check_name: str
    status: str
    affected_rows: int
    message: str


class DataQualityValidator:
    """Evaluate configured data-quality thresholds.

    This class is a validation Strategy that reports immutable findings instead of
    silently repairing source or derived data.

    Inject ``validate`` with the project's ``quality_checks`` settings bound by
    ``functools.partial``. Schema prerequisites are reported as failures; only
    malformed caller arguments raise exceptions.
    """

    def validate(self, permits: Any, settings: dict[str, Any]) -> list[QualityCheckResult]:
        """Run identifier, date, freshness, geography, and row-count checks.

        Args:
            permits: Pandas DataFrame with unique string column names, normally
                after cleaning. Standard fields are ``permit_number``,
                ``applied_date``, ``decision_date``, ``community``, ``latitude``,
                and ``longitude``. Cleaner Boolean invalid flags are respected.
            settings: Quality-check mapping. ``require_unique_permit_number``
                and the three ``warn_on_*`` options default to true. Setting
                uniqueness to false downgrades duplicates to warnings; setting
                a warning option to false omits that check. Optional
                ``minimum_row_count`` and ``max_data_age_days`` are nonnegative
                integers. Freshness requires an explicit ISO ``reference_date``
                and uses the latest valid application date, never the clock.

        Returns:
            Ordered immutable results, including passes, without changing or
            removing records. Missing dates are distinct from malformed dates;
            missing decisions are warnings, not proof of pending status. Coordinates
            must be finite and within geographic bounds; zero is valid.

        Raises:
            TypeError: The input is not a DataFrame, settings are not a mapping,
                or an option has the wrong type.
            ValueError: Column names, thresholds, reference date, or supplied
                cleaner invalid flags are malformed.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        if not isinstance(settings, dict):
            raise TypeError("settings must be a dictionary of quality checks.")
        if not permits.columns.is_unique or any(
            not isinstance(name, str) or not name.strip() for name in permits.columns
        ):
            raise ValueError("Column names must be unique, nonblank strings.")
        options = {}
        for name in (
            "require_unique_permit_number", "warn_on_missing_community",
            "warn_on_missing_coordinates", "warn_on_negative_processing_days",
        ):
            options[name] = settings.get(name, True)
            if not isinstance(options[name], bool):
                raise TypeError(f"{name} must be Boolean.")
        for name in ("minimum_row_count", "max_data_age_days"):
            if name in settings:
                value = settings[name]
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError(f"{name} must be an integer.")
                if value < 0:
                    raise ValueError(f"{name} must be nonnegative.")
        reference = pd.NaT
        if "max_data_age_days" in settings:
            reference = _calendar_date(settings.get("reference_date"))
            if pd.isna(reference):
                raise ValueError("Freshness requires a valid ISO reference_date.")

        results: list[QualityCheckResult] = []
        if _has_columns(permits, ["permit_number"], "identifier_columns", results):
            identifiers = permits["permit_number"]
            missing = _missing(identifiers)
            results.append(_result("missing_permit_number", missing, "fail"))
            duplicates = identifiers.duplicated(keep=False) & ~missing
            results.append(_result(
                "duplicate_permit_number", duplicates,
                "fail" if options["require_unique_permit_number"] else "warn",
            ))

        dates: dict[str, pd.Series] = {}
        for name in ("applied_date", "decision_date"):
            if not _has_columns(permits, [name], f"{name}_column", results):
                continue
            values = permits[name]
            parsed = values.map(_calendar_date).astype("datetime64[ns]")
            invalid = (~_missing(values) & parsed.isna()) | _invalid_flag(permits, name)
            dates[name] = parsed.mask(invalid)
            results.append(_result(f"invalid_{name}", invalid, "warn"))
            results.append(_result(
                f"missing_{name}", _missing(values) & ~invalid, "warn",
            ))
        if options["warn_on_negative_processing_days"] and len(dates) == 2:
            negative = dates["decision_date"].lt(dates["applied_date"])
            results.append(_result("negative_processing_days", negative, "warn"))

        if options["warn_on_missing_community"] and _has_columns(
            permits, ["community"], "community_column", results,
        ):
            results.append(_result("missing_community", _missing(permits["community"]), "warn"))
        if options["warn_on_missing_coordinates"] and _has_columns(
            permits, ["latitude", "longitude"], "coordinate_columns", results,
        ):
            missing_coordinates = pd.Series(False, index=permits.index)
            invalid_coordinates = pd.Series(False, index=permits.index)
            for name, bound in (("latitude", 90), ("longitude", 180)):
                values = permits[name]
                missing = _missing(values)
                numeric = pd.to_numeric(values, errors="coerce")
                invalid = (
                    (~missing & ~numeric.between(-bound, bound).fillna(False))
                    | values.map(lambda value: isinstance(value, bool))
                    | _invalid_flag(permits, name)
                )
                missing_coordinates |= missing & ~invalid
                invalid_coordinates |= invalid
            results.append(_result("missing_coordinates", missing_coordinates, "warn"))
            results.append(_result("invalid_coordinates", invalid_coordinates, "warn"))

        if "minimum_row_count" in settings:
            minimum = settings["minimum_row_count"]
            below = len(permits) < minimum
            results.append(QualityCheckResult(
                "minimum_row_count", "fail" if below else "pass",
                len(permits) if below else 0,
                f"Observed {len(permits)} records; configured minimum is {minimum}.",
            ))
        if "max_data_age_days" in settings:
            latest = dates["applied_date"].max() if "applied_date" in dates else pd.NaT
            if pd.isna(latest):
                results.append(QualityCheckResult(
                    "data_freshness", "fail", len(permits),
                    "Freshness cannot be assessed without a valid application date.",
                ))
            else:
                age = (reference.normalize() - latest.normalize()).days
                stale = age > settings["max_data_age_days"]
                results.append(QualityCheckResult(
                    "data_freshness", "warn" if stale else "pass",
                    len(permits) if stale else 0,
                    f"Latest application is {latest.date()}; age at reference date "
                    f"{reference.date()} is {age} days (limit {settings['max_data_age_days']}).",
                ))
        return results


def _missing(values: pd.Series) -> pd.Series:
    """Identify nulls and blank strings without changing source evidence.

    Args:
        values: Column to inspect.

    Returns:
        Boolean mask aligned with the original row index.
    """
    return values.isna() | values.map(lambda value: isinstance(value, str) and not value.strip())


def _calendar_date(value: Any) -> Any:
    """Parse an ISO date while retaining its source calendar time.

    Args:
        value: ISO string or date object; numeric epochs are unsupported.

    Returns:
        Naive Timestamp, or NaT for missing or malformed values.
    """
    if not isinstance(value, (str, date)):
        return pd.NaT
    parsed = pd.to_datetime(value, format="ISO8601", errors="coerce")
    return pd.NaT if pd.isna(parsed) else parsed.tz_localize(None)


def _invalid_flag(table: pd.DataFrame, name: str) -> pd.Series:
    """Preserve cleaner evidence after bad values have become nulls.

    Args:
        table: Cleaned or manually prepared permit table.
        name: Field whose optional Boolean invalid flag is inspected.

    Returns:
        Boolean mask, defaulting to false when no flag exists.

    Raises:
        ValueError: A supplied flag is not Boolean or contains missing values.
    """
    flag = f"{name}_invalid"
    if flag not in table:
        return pd.Series(False, index=table.index)
    values = table[flag]
    if not pd.api.types.is_bool_dtype(values.dtype) or values.isna().any():
        raise ValueError(f"{flag} must contain nonmissing Boolean values.")
    return values.astype(bool)


def _has_columns(
    table: pd.DataFrame, columns: list[str], check: str,
    results: list[QualityCheckResult],
) -> bool:
    """Report unavailable check prerequisites instead of silently passing them.

    Args:
        table: Table under inspection.
        columns: Columns needed by one check.
        check: Stable prerequisite check name.
        results: Report receiving a failure when required fields are absent.

    Returns:
        Whether all prerequisite columns exist.
    """
    missing = [name for name in columns if name not in table]
    if missing:
        results.append(QualityCheckResult(
            check, "fail", 0, f"Cannot evaluate check; missing columns: {', '.join(missing)}.",
        ))
    return not missing


def _result(name: str, mask: pd.Series, severity: str) -> QualityCheckResult:
    """Convert an affected-record mask into an immutable result.

    Args:
        name: Stable quality-check identifier.
        mask: Boolean mask identifying affected rows.
        severity: Warning or failure status to use when records are affected.

    Returns:
        A pass for no affected records, otherwise the supplied severity.
    """
    count = int(mask.sum())
    return QualityCheckResult(
        name, severity if count else "pass", count,
        f"{name}: {count} of {len(mask)} records affected.",
    )
