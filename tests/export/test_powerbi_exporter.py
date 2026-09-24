"""Tests for powerbi exporter.

This module verifies the documented contracts and edge cases of the powerbi exporter
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

import pandas as pd
import pytest
from datetime import datetime, timezone

from dp_activity.export import powerbi_exporter as exporter_module
from dp_activity.export.powerbi_exporter import PowerBIExporter
from dp_activity.repositories.output_repository import OutputRepository
from dp_activity.validation.schema_validator import SchemaIssue
from dp_activity.validation.data_quality_validator import QualityCheckResult


def test_export_writes_clean_and_reconciliation_tables(tmp_path) -> None:
    """Verify that export writes clean and reconciliation tables.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1"],
            "applied_date": pd.to_datetime(["2024-08-06"]),
            "IncludeResidential": [True],
        }
    )

    paths = PowerBIExporter(tmp_path).export(
        permits,
        {"monthly_summary": pd.DataFrame({"PermitCount": [1]})},
        {},
    )

    assert paths["clean_permits"].exists()
    assert paths["reconciliation"].exists()
    assert "Unnamed: 0" not in pd.read_csv(paths["clean_permits"]).columns


@pytest.fixture
def permits() -> pd.DataFrame:
    """Supply mixed residential records with missing and overlapping audit evidence.

    Returns:
        Small reporting table with meaningful reconciliation denominators.
    """
    return pd.DataFrame({
        "permit_number": ["A", "B", "C"],
        "applied_date": pd.to_datetime(["2024-08-06", None, "2024-08-07"]),
        "IncludeResidential": [True, True, False],
        "Period": ["During", "During", "During"],
        "ResidentialType": ["Duplex", None, "Office"],
        "YearMonth": pd.to_datetime(["2024-08-01"] * 3),
        "ClassificationNeedsReview": pd.array([True, None, False], dtype="boolean"),
        "HasValidProcessingDays": [True, False, True],
    })


def test_formats_validation_reports_reconciliation_and_preservation(tmp_path, permits) -> None:
    """Reconcile from permits while retaining real validator output shapes.

    Args:
        tmp_path: Isolated output directory.
        permits: Mixed permit fixture.
    """
    original = permits.copy(deep=True)
    reports = {
        "schema": [SchemaIssue("error", "example", "missing evidence")],
        "quality": [QualityCheckResult("duplicates", "warn", 2, "inspect")],
        "classification": pd.DataFrame({"status": ["warn"], "record_count": [3]}),
        "empty": [],
    }
    paths = PowerBIExporter(tmp_path, output_formats=("csv", "json"), base_name="study",
                            output_names={"clean_permits": "clean"}).export(
        permits, {"volume": pd.DataFrame({"PermitCount": [999]})}, reports,
    )
    assert paths["clean_permits.csv"].name == "study_clean.csv"
    clean = pd.read_json(paths["clean_permits.json"], convert_dates=False)
    assert clean.loc[0, "applied_date"] == "2024-08-06T00:00:00"
    assert pd.isna(clean.loc[1, "applied_date"])
    assert clean["IncludeResidential"].tolist() == [True, True, False]
    assert pd.read_csv(paths["validation_schema.csv"]).loc[0, "severity"] == "error"
    assert pd.read_csv(paths["validation_quality.csv"]).loc[0, "affected_rows"] == 2
    assert pd.read_csv(paths["validation_empty.csv"]).empty
    totals = pd.read_csv(paths["reconciliation.csv"])
    headline = totals.loc[totals["Scope"].eq("All")].set_index("Metric")
    assert headline.loc["AllPermitCount", "PythonValue"] == 3
    assert headline.loc["ResidentialCount", "PythonValue"] == 2
    assert headline.loc["ExcludedCount", "PythonValue"] == 1
    assert totals.loc[totals["Scope"].eq("ResidentialType"), "PythonValue"].sum() == 2
    residential = totals.loc[totals["Scope"].eq("Residential")].set_index("Metric")
    assert residential.loc["HasValidProcessingDays", "PythonValue"] == 1
    audit = pd.read_csv(paths["bias_audit.csv"]).set_index("Flag")
    assert audit.loc["ClassificationNeedsReview", "TrueCount"] == 1
    assert audit.loc["ClassificationNeedsReview", "UnknownCount"] == 1
    assert not audit.loc["IsPending", "Available"]
    assert pd.isna(audit.loc["IsPending", "TrueCount"])
    pd.testing.assert_frame_equal(permits, original)


def test_parquet_round_trip(tmp_path, permits) -> None:
    """Preserve Boolean/null values with the optional Parquet dependency.

    Args:
        tmp_path: Isolated output directory.
        permits: Mixed permit fixture.
    """
    pytest.importorskip("pyarrow")
    paths = PowerBIExporter(tmp_path, output_formats=("parquet",)).export(permits, {}, {})
    result = pd.read_parquet(paths["clean_permits"])
    assert result["IncludeResidential"].tolist() == [True, True, False]
    assert result["ClassificationNeedsReview"].isna().sum() == 1


def test_timestamp_and_collision_safe_writes(tmp_path, permits, monkeypatch) -> None:
    """Use one UTC timestamp and honor repository overwrite protection.

    Args:
        tmp_path: Isolated output directory.
        permits: Mixed permit fixture.
        monkeypatch: Freezes the export naming clock.
    """
    class FixedDateTime(datetime):
        """Supply a stable naming timestamp for repeatable output assertions."""

        @classmethod
        def now(cls, tz=None):
            """Return the fixed naming instant.

            Args:
                tz: Requested timezone.

            Returns:
                Fixed aware timestamp.
            """
            return datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(exporter_module, "datetime", FixedDateTime)
    exporter = PowerBIExporter(output_repository=OutputRepository(tmp_path, overwrite_outputs=False),
                              include_timestamp=True)
    first = exporter.export(permits, {}, {})
    second = exporter.export(permits, {}, {})
    assert all("20260923_120000" in path.name for path in first.values())
    assert all(path.stem.endswith("_001") for path in second.values())
    assert set(first.values()).isdisjoint(second.values())


@pytest.mark.parametrize("kind", ["duplicate", "index", "missing", "flags", "late_table", "reserved", "report", "collision"])
def test_invalid_exports_write_nothing(tmp_path, permits, kind) -> None:
    """Catch invalid later tables and destination collisions before writing any file.

    Args:
        tmp_path: Isolated output directory.
        permits: Mixed permit fixture.
        kind: Invalid input contract to exercise.
    """
    analysis = {}
    reports = {}
    names = {}
    if kind == "duplicate":
        permits.columns = ["x"] * len(permits.columns)
    elif kind == "index":
        permits["Unnamed: 0"] = 0
    elif kind == "missing":
        permits = permits.drop(columns="IncludeResidential")
    elif kind == "flags":
        permits["IncludeResidential"] = "True"
    elif kind == "late_table":
        analysis["bad"] = []
    elif kind == "reserved":
        analysis["reconciliation"] = pd.DataFrame({"x": [1]})
    elif kind == "report":
        reports["bad"] = {"unexpected": "mapping"}
    elif kind == "collision":
        names = {"clean_permits": "same", "reconciliation": "SAME"}
    with pytest.raises((ValueError, TypeError)):
        PowerBIExporter(tmp_path, output_names=names).export(permits, analysis, reports)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("options", [
    {"output_formats": ["xlsx"]}, {"output_formats": ["csv", "csv"]},
    {"base_name": "../escape"}, {"output_names": {"clean_permits": "../escape"}},
])
def test_invalid_configuration_is_rejected(tmp_path, options) -> None:
    """Reject unsupported formats and unsafe names during construction.

    Args:
        tmp_path: Isolated output directory.
        options: Invalid exporter configuration.
    """
    with pytest.raises(ValueError):
        PowerBIExporter(tmp_path, **options)


def test_empty_permits_have_zero_headlines_and_explicit_schema(tmp_path, permits) -> None:
    """Export valid empty outputs without inventing audit evidence.

    Args:
        tmp_path: Isolated output directory.
        permits: Fixture whose schema is retained with no rows.
    """
    paths = PowerBIExporter(tmp_path).export(permits.iloc[:0], {}, {})
    assert pd.read_csv(paths["clean_permits"]).empty
    totals = pd.read_csv(paths["reconciliation"])
    assert totals.iloc[:3]["PythonValue"].eq(0).all()
