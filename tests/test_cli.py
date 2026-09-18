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
