"""Tests for config.

This module verifies the documented contracts and edge cases of the config component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

from pathlib import Path

from conftest import REPOSITORY_ROOT, implemented

from dp_activity.config import load_config


def test_loads_project_settings_and_periods() -> None:
    """Verify that loads project settings and periods."""
    config = implemented(load_config, REPOSITORY_ROOT / "config/settings.yaml")
    assert config.repository_root == REPOSITORY_ROOT
    assert [period.name for period in config.periods][:2] == ["Before", "During"]
    assert config.classification_rules_path.is_file()
