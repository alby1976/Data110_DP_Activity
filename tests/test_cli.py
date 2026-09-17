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

from dp_activity.cli import build_parser


def test_parser_supports_run_command() -> None:
    """Verify that parser supports run command."""
    parser = implemented(build_parser)
    arguments = parser.parse_args(["run"])
    assert arguments.command == "run"
