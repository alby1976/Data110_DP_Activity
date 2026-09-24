"""Export stable, tidy tables for Power BI.

This module defines the export boundary for finalized project tables and Power BI
reconciliation outputs, preserving analytical evidence and nullable audit counts.

Design Pattern:
    Adapter.

Pattern Rationale:
    It converts project-owned tables into stable reporting schemas and conventions
    expected by Power BI.

Typical Usage:
    Inject a configured exporter into the analysis pipeline and call export() to
    persist tables through the output repository.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
import re
from typing import Any

import pandas as pd

from dp_activity.repositories.output_repository import OutputRepository
from dp_activity.validation.schema_validator import SchemaIssue
from dp_activity.validation.data_quality_validator import QualityCheckResult


class PowerBIExporter:
    """Adapt project tables to stable Power BI input files.

    This class participates in the Adapter pattern by translating in-memory analytical
    tables into explicit CSV schemas and reconciliation metadata.

    Attributes:
        output_directory: Directory that receives exported tables.
        output_repository: Repository used to persist generated output files.
        output_formats: File formats requested for processed outputs.
        base_name: Extension-free filename stem used for configured outputs.
        include_timestamp: Whether generated output names should include timestamps.
        timestamp_format: ``strftime`` format used for generated output timestamps.
        output_names: Optional logical-name to filename-label mapping.
    """

    def __init__(
        self,
        output_directory: Path | None = None,
        *,
        output_repository: OutputRepository | None = None,
        output_formats: Sequence[str] = ("csv",),
        base_name: str = "development_permits",
        include_timestamp: bool = False,
        timestamp_format: str = "%Y%m%d_%H%M%S",
        output_names: dict[str, str] | None = None,
    ) -> None:
        """Configure the Power BI export adapter.

        Args:
            output_directory: Directory that receives generated files when an explicit
                repository is not supplied.
            output_repository: Optional repository that owns output persistence.
            output_formats: Processed-output formats requested by configuration.
            base_name: Extension-free filename stem used for configured outputs.
            include_timestamp: Whether generated output names should include timestamps.
            timestamp_format: ``strftime`` format used for generated output timestamps.
            output_names: Optional filename labels for logical table names.

        Raises:
            ValueError: Neither an output directory nor repository is supplied, or the
                configured output formats/base name are blank.
        """
        if output_repository is None and output_directory is None:
            raise ValueError("PowerBIExporter requires an output directory or repository.")

        self.output_repository = output_repository or OutputRepository(output_directory)
        self.output_directory = self.output_repository.output_directory
        self.output_formats = tuple(format_name.strip().lower() for format_name in output_formats)
        self.base_name = base_name.strip()
        self.include_timestamp = include_timestamp
        self.timestamp_format = timestamp_format
        self.output_names = dict(output_names or {})

        if not self.output_formats or any(not format_name for format_name in self.output_formats):
            raise ValueError("PowerBIExporter output formats cannot be blank.")
        if not self.base_name:
            raise ValueError("PowerBIExporter base name cannot be blank.")
        if set(self.output_formats) - {"csv", "json", "parquet", "pq"}:
            raise ValueError("Unsupported processed output format.")
        if len(set(self.output_formats)) != len(self.output_formats):
            raise ValueError("Output formats must be unique.")
        _filename_label(self.base_name)
        for key, label in self.output_names.items():
            _filename_label(key)
            _filename_label(label)

    def export(
        self,
        permit_table: Any,
        analysis_tables: dict[str, Any],
        validation_tables: dict[str, Any],
    ) -> dict[str, Path]:
        """Write reporting tables and independent Python reconciliation totals.

        Args:
            permit_table: Final permit-level table exported for reporting.
            analysis_tables: Stable analysis names mapped to finalized result tables.
            validation_tables: Validator names mapped to structured findings.

        Returns:
            Logical names mapped to written paths for one format. Multiple formats
            use ``name.format`` keys. Includes clean_permits, supplied analyses,
            validation_<validator>, reconciliation, and bias_audit. Filenames use
            base_name, configured label (or logical name), and one optional UTC
            timestamp shared by the whole export.

        Raises:
            TypeError: Tables, validation reports, or inclusion/audit flags have
                unsupported types.
            ValueError: Columns or output names are ambiguous or unsafe, required
                permit columns are missing, or destination filenames collide.
            OSError: Persistence fails; earlier files may already have been written.

        Note:
            Validates and prepares every table before writing. Writes are atomic
            per file, not transactional across the export. Preserves row order,
            column order, missing values, and all source records; never exports
            an implicit index. Date cells become ISO text across formats, Boolean
            cells stay Boolean. Reconciliation is computed from permits, not
            sums of overlapping summary tables. It does not certify Power BI
            agreement or source quality. Full provenance manifests remain separate.
        """
        permits = _prepare_table(permit_table)
        required = {"permit_number", "applied_date", "IncludeResidential"}
        if not required.issubset(permits.columns):
            raise ValueError(f"Missing permit export columns: {sorted(required - set(permits.columns))}")
        inclusion = permits["IncludeResidential"]
        if inclusion.isna().any() or (len(permits) and not pd.api.types.is_bool_dtype(inclusion)):
            raise TypeError("IncludeResidential must contain nonmissing Booleans.")
        if not isinstance(analysis_tables, dict) or not isinstance(validation_tables, dict):
            raise TypeError("Analysis and validation tables must be dictionaries.")
        tables = {"clean_permits": permits}
        for name, table in analysis_tables.items():
            _filename_label(name)
            if name in {"clean_permits", "reconciliation", "bias_audit"} or name.startswith("validation_"):
                raise ValueError(f"Reserved output name: {name}")
            tables[name] = _prepare_table(table)
        for name, report in validation_tables.items():
            _filename_label(name)
            if isinstance(report, pd.DataFrame):
                table = report
            elif isinstance(report, (list, tuple)) and all(
                isinstance(item, (SchemaIssue, QualityCheckResult)) for item in report
            ):
                table = pd.DataFrame([asdict(item) for item in report]) if report else pd.DataFrame(
                    columns=["severity", "column", "message", "check_name", "status", "affected_rows"],
                )
            else:
                raise TypeError(f"Unsupported validation report: {name}")
            tables[f"validation_{name}"] = _prepare_table(table)
        tables["reconciliation"], tables["bias_audit"] = _audit_tables(permits)
        timestamp = datetime.now(timezone.utc).strftime(self.timestamp_format) if self.include_timestamp else None
        if timestamp is not None:
            _filename_label(timestamp)
        pending = []
        seen = set()
        for name, table in tables.items():
            label = self.output_names.get(name, name)
            stem = f"{self.base_name}_{label}" + (f"_{timestamp}" if timestamp else "")
            for format_name in self.output_formats:
                filename = f"{stem}.{format_name}"
                if filename.casefold() in seen:
                    raise ValueError(f"Duplicate export destination: {filename}")
                seen.add(filename.casefold())
                key = name if len(self.output_formats) == 1 else f"{name}.{format_name}"
                pending.append((key, table, filename))
        return {key: self.output_repository.write_table(table, filename) for key, table, filename in pending}


def _filename_label(value: str) -> None:
    """Reject ambiguous or path-like output labels before any writes.

    Args:
        value: Extension-free filename component.

    Raises:
        ValueError: The label contains characters outside letters, digits, _ or -.
    """
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError(f"Invalid output filename label: {value!r}")


def _prepare_table(table: Any) -> pd.DataFrame:
    """Copy a table and give date cells a consistent ISO representation.

    Args:
        table: Reporting DataFrame with explicit, unique columns.

    Returns:
        Input-preserving copy with ISO date/datetime text and nullable Booleans.

    Raises:
        TypeError: Input is not a DataFrame.
        ValueError: Column names are empty, duplicated, or leaked CSV index names.
    """
    if not isinstance(table, pd.DataFrame):
        raise TypeError("Export tables must be pandas DataFrames.")
    if not len(table.columns) or not table.columns.is_unique or any(
        not isinstance(name, str) or not name.strip() or name.startswith("Unnamed:")
        for name in table.columns
    ):
        raise ValueError("Export columns must be unique nonblank names without accidental CSV indexes.")
    result = table.copy(deep=True)
    for name in result:
        if pd.api.types.is_datetime64_any_dtype(result[name]) or pd.api.types.is_object_dtype(result[name]):
            result[name] = result[name].map(
                lambda value: None if value is pd.NaT else value.isoformat()
                if isinstance(value, (date, datetime)) else value
            )
    return result


def _audit_tables(permits: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate independent record counts and overlapping audit flags.

    Args:
        permits: Prepared permits with validated residential inclusion.

    Returns:
        Long-form reconciliation (Scope, Group, Metric, PythonValue) and bias
        audit (Flag, Available, TrueCount, UnknownCount). Optional flags are
        counted across all records; absent evidence stays null. Grouped
        residential counts retain missing labels as null groups.

    Raises:
        TypeError: An available audit flag is not Boolean.
    """
    included = permits["IncludeResidential"].astype(bool)
    rows = [
        {"Scope": "All", "Group": None, "Metric": "AllPermitCount", "PythonValue": len(permits)},
        {"Scope": "All", "Group": None, "Metric": "ResidentialCount", "PythonValue": int(included.sum())},
        {"Scope": "All", "Group": None, "Metric": "ExcludedCount", "PythonValue": int((~included).sum())},
    ]
    for field in ("Period", "YearMonth", "ResidentialType"):
        if field in permits:
            counts = permits.loc[included].groupby(field, dropna=False, observed=True, sort=False).size()
            rows.extend({"Scope": field, "Group": None if pd.isna(label) else str(label),
                         "Metric": "ResidentialCount", "PythonValue": int(count)}
                        for label, count in counts.items())
    audits = []
    for flag in ("ClassificationNeedsReview", "HasValidProcessingDays", "IsPending", "IsRightCensored",
                 "HasNegativeProcessingDays", "ProcessingDateMissing", "ProcessingDateInvalid",
                 "IsAfterObservationEnd", "IsPartialSeason"):
        present = flag in permits
        values = permits[flag] if present else None
        if present and len(permits) and not pd.api.types.is_bool_dtype(values):
            raise TypeError(f"Audit field {flag} must have Boolean dtype.")
        count = int(values.sum()) if present else None
        unknown = int(values.isna().sum()) if present else None
        audits.append({"Flag": flag, "Available": present, "TrueCount": count, "UnknownCount": unknown})
        rows.append({"Scope": "All", "Group": None, "Metric": flag, "PythonValue": count})
        if present:
            rows.append({"Scope": "Residential", "Group": None, "Metric": flag,
                         "PythonValue": int(values.loc[included].sum())})
    return pd.DataFrame(rows).convert_dtypes(), pd.DataFrame(audits).convert_dtypes()
