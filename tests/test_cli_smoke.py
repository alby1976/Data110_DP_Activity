"""Exercise the offline CLI pipeline using frozen synthetic permit records.

This module verifies real collaborator integration and exported analytical
denominators without contacting external services or using production outputs.

Design Pattern:
    None.

Pattern Rationale:
    These integration tests exercise the application's existing composition root
    rather than implementing a separate application pattern.

Typical Usage:
    Run pytest tests/test_cli_smoke.py to verify the complete CLI table workflow
    with isolated configuration, rules, snapshots, and reporting directories.
"""

import hashlib
from pathlib import Path
import shutil
import socket

import pandas as pd
import pytest
import requests
import yaml

from dp_activity import cli


@pytest.fixture
def smoke_workspace(tmp_path, monkeypatch) -> tuple[Path, Path, Path]:
    """Create an isolated real CLI workspace and prohibit network requests.

    Args:
        tmp_path: Pytest-owned output root.
        monkeypatch: Installs fail-fast guards only at network boundaries.

    Returns:
        Settings path, immutable snapshot copy, and reporting directory.
    """
    def no_network(*args, **kwargs):
        """Fail if offline execution attempts external I/O.

        Args:
            *args: Ignored network call arguments.
            **kwargs: Ignored network call options.

        Raises:
            AssertionError: Any network operation is attempted.
        """
        raise AssertionError("The frozen CLI smoke test must remain offline.")

    monkeypatch.setattr(requests.sessions.Session, "request", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    root = Path(__file__).resolve().parents[1]
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    shutil.copyfile(root / "config/classification_rules.csv", config_dir / "classification_rules.csv")
    fixture = root / "tests/fixtures/cli_smoke/permits.csv"
    snapshot = tmp_path / "permits.csv"
    shutil.copyfile(fixture, snapshot)
    shutil.copyfile(fixture.with_suffix(".csv.metadata.json"), snapshot.with_suffix(".csv.metadata.json"))
    settings = yaml.safe_load((root / "config/settings.yaml").read_text(encoding="utf-8"))
    settings["storage"].update(output_base_name="smoke", include_timestamp=False,
                               overwrite_outputs=True, processed_output_formats=["csv"])
    settings["outputs"]["clean_permits"] = "frozen_clean"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "pipeline.log").write_text("Prior synthetic run\n", encoding="utf-8")
    return settings_path, snapshot, tmp_path / "data/processed"


@pytest.mark.parametrize("format_name", ["csv", "json", "parquet"])
def test_real_cli_exports_reconciled_frozen_results(smoke_workspace, capsys, format_name) -> None:
    """Run every pipeline collaborator and verify persisted counts and exposure.

    Args:
        smoke_workspace: Isolated real configuration and frozen snapshot.
        capsys: Captures CLI success and error messages.
        format_name: Configured processed output format.
    """
    if format_name == "parquet":
        pytest.importorskip("pyarrow")
    settings_path, snapshot, output = smoke_workspace
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    settings["storage"]["processed_output_formats"] = [format_name]
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    original = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert cli.main(["--settings", str(settings_path), "run", str(snapshot)]) == 0
    captured = capsys.readouterr()
    assert "Pipeline completed successfully." in captured.out
    assert not captured.err
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == original
    archived = list((settings_path.parent.parent / "reports/logs/archive").glob("*"))
    assert len(archived) == 1
    assert archived[0].read_text(encoding="utf-8") == "Prior synthetic run\n"

    def read(label: str) -> pd.DataFrame:
        """Read one configured output with the real format reader.

        Args:
            label: Exported filename label.

        Returns:
            Persisted table without implicit index columns.
        """
        path = output / f"smoke_{label}.{format_name}"
        if format_name == "csv":
            return pd.read_csv(path)
        if format_name == "json":
            return pd.read_json(path, convert_dates=False)
        return pd.read_parquet(path)

    clean = read("frozen_clean").set_index("permit_number")
    assert len(clean) == 7
    assert clean["IncludeResidential"].sum() == 6
    assert clean.loc["SYN-B2", "Period"] == "Before"
    assert clean.loc["SYN-D1", "Period"] == "During"
    assert clean.loc["SYN-D2", "Period"] == "During"
    assert clean.loc["SYN-P1", "Period"] == "Early Post-Repeal"
    assert clean.loc["SYN-D2", "IsPending"]
    assert clean.loc["SYN-P1", "IsRightCensored"]
    assert not clean.loc["SYN-P1", "HasValidProcessingDays"]
    volume = read("permit_volume").set_index("Period")
    assert volume["PermitCount"].to_dict() == {"Before": 2, "During": 2, "Early Post-Repeal": 2}
    monthly = read("monthly_volume")
    months = pd.to_datetime(monthly["YearMonth"])
    assert monthly.loc[months.eq("2023-02-01"), "PermitCount"].iloc[0] == 0
    september = monthly.loc[months.eq("2026-09-01")].iloc[0]
    assert september["ExposureDays"] == 22
    assert september["DP_Rate30"] == pytest.approx(30 / 22)
    assert monthly.groupby("Period")["PermitCount"].sum().to_dict() == volume["PermitCount"].to_dict()
    assert read("seasonal_summary")["PermitCount"].sum() == 6
    assert read("type_summary")["PermitCount"].sum() == 6
    assert read("rezoning_summary")["RezoningRelevantShare"].eq(1).all()
    reconciliation = read("reconciliation")
    totals = reconciliation.loc[reconciliation["Scope"].eq("All")].set_index("Metric")
    assert totals.loc["ResidentialCount", "PythonValue"] == 6
    assert totals.loc["HasValidProcessingDays", "PythonValue"] == 5
    assert read("sensitivity_summary").empty
    assert read("validation_schema_validator")["severity"].ne("error").all()
    quality = read("validation_data_quality_validator")
    assert quality["status"].ne("fail").all()
    assert quality["status"].eq("warn").any()
    classification = read("validation_classification_validator")
    assert classification["status"].ne("fail").all()
    assert read("bias_audit")["Flag"].eq("IsRightCensored").any()
    assert not list(output.glob("*.tmp"))
    first_paths = {path.name for path in output.iterdir()}
    assert cli.main(["--settings", str(settings_path), "run", str(snapshot)]) == 0
    assert {path.name for path in output.iterdir()} == first_paths
    pd.testing.assert_frame_equal(read("permit_volume").set_index("Period"), volume)


def test_cli_currently_exports_reported_validation_failures(smoke_workspace, capsys) -> None:
    """Make the current collect-only policy explicit without endorsing failed outputs.

    Args:
        smoke_workspace: Isolated CLI settings and snapshot.
        capsys: Captures the CLI result for failure diagnosis.
    """
    settings, snapshot, output = smoke_workspace
    records = pd.read_csv(snapshot)
    records.loc[1, "permitnum"] = records.loc[0, "permitnum"]
    records.to_csv(snapshot, index=False)
    assert cli.main(["--settings", str(settings), "run", str(snapshot)]) == 0
    report = pd.read_csv(output / "smoke_validation_data_quality_validator.csv")
    assert report["status"].eq("fail").any()
    assert (output / "smoke_frozen_clean.csv").exists()
    assert "Pipeline completed successfully." in capsys.readouterr().out
