"""Tests for cli.

This module verifies the documented contracts and edge cases of the cli component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

from datetime import datetime

import yaml

from conftest import implemented

from dp_activity import cli
from dp_activity.cli import build_parser
from dp_activity.pipeline.analysis_pipeline import PipelineResult


def test_parser_supports_run_command() -> None:
    """Verify that parser supports run command."""
    parser = implemented(build_parser)
    arguments = parser.parse_args(["run"])
    assert arguments.command == "run"


def test_run_command_requires_snapshot_path() -> None:
    """Verify that run reports a command-usage error without a snapshot path."""
    assert cli.main(["run"]) == 2


def test_main_dispatches_run_command(monkeypatch) -> None:
    """Verify that main loads config and executes the selected command object.

    Args:
        monkeypatch: Pytest fixture used to replace pipeline assembly during the test.
    """

    class StubRunCommand:
        """Provide a successful command double for CLI dispatch tests."""

        def execute(self) -> PipelineResult:
            """Return a deterministic empty pipeline result.

            Returns:
                Empty pipeline output collections suitable for summary printing.
            """
            return PipelineResult(
                cleaned_permits=[],
                analysis_tables={},
                validation_reports={},
                output_paths={},
            )

    monkeypatch.setattr(cli, "build_run_command", lambda config, snapshot_path: StubRunCommand())

    assert cli.main(["run", "snapshot.csv"]) == 0


def test_main_archives_existing_pipeline_log(monkeypatch, tmp_path) -> None:
    """Verify that main archives an existing log before running the command.

    Args:
        monkeypatch: Pytest fixture used to replace pipeline assembly during the test.
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """

    class StubRunCommand:
        """Provide a successful command double for archive tests."""

        def execute(self) -> PipelineResult:
            """Return an empty pipeline result.

            Returns:
                Empty pipeline output collections suitable for summary printing.
            """
            return PipelineResult(
                cleaned_permits=[],
                analysis_tables={},
                validation_reports={},
                output_paths={},
            )

    class FixedDateTime:
        """Provide a deterministic timestamp for archived log filenames."""

        @staticmethod
        def now(timezone):
            """Return the fixed datetime used by this test.

            Args:
                timezone: Timezone argument supplied by the production code.

            Returns:
                Fixed datetime used to build the archive filename.
            """
            return datetime(2026, 9, 18, 14, 30, 22)

    config_dir = tmp_path / "config"
    reports_dir = tmp_path / "reports"
    config_dir.mkdir()
    reports_dir.mkdir()
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")
    log_file = reports_dir / "pipeline.log"
    log_file.write_text("previous run\n", encoding="utf-8")

    settings = yaml.safe_load(cli.DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))
    settings["paths"]["classification_rules"] = "config/classification_rules.csv"
    settings["logging"]["archive_timestamp_format"] = "%Y%m%d_%H%M%S"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    monkeypatch.setattr(cli, "build_run_command", lambda config, snapshot_path: StubRunCommand())
    monkeypatch.setattr(cli, "datetime", FixedDateTime)

    assert cli.main(["--settings", str(settings_path), "run", "snapshot.csv"]) == 0
    assert not log_file.exists()
    archived_log = tmp_path / "reports/logs/archive/pipeline_20260918_143022.log"
    assert archived_log.read_text(encoding="utf-8") == "previous run\n"
