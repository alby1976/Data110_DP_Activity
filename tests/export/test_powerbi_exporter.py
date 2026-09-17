import pandas as pd

from conftest import implemented

from dp_activity.export.powerbi_exporter import PowerBIExporter


def test_export_writes_clean_and_reconciliation_tables(tmp_path) -> None:
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

