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

from tests.conftest import implemented

from dp_activity.export.powerbi_exporter import PowerBIExporter


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

    paths = implemented(
        PowerBIExporter(tmp_path).export,
        permits,
        {"monthly_summary": pd.DataFrame({"PermitCount": [1]})},
        {},
    )

    assert paths["clean_permits"].exists()
    assert paths["reconciliation"].exists()
    assert "Unnamed: 0" not in pd.read_csv(paths["clean_permits"]).columns
