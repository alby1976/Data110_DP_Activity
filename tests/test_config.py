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

from dataclasses import fields

import yaml

from conftest import REPOSITORY_ROOT, implemented

from dp_activity.config import load_config


def test_loads_project_settings_and_periods() -> None:
    """Verify that project settings are loaded into typed config objects."""
    config = implemented(load_config, REPOSITORY_ROOT / "config/settings.yaml")
    assert config.repository_root == REPOSITORY_ROOT
    assert [period.name for period in config.periods][:2] == ["Before", "During"]
    assert config.classification_rules_path.is_file()
    assert config.output_base_name == "development_permits"
    assert config.overwrite_outputs is True
    assert config.raw_snapshot_formats == ("csv",)
    assert config.processed_output_formats == ("csv",)


def test_load_config_returns_populated_attributes() -> None:
    """Verify that loaded configuration objects expose populated attributes."""
    config = implemented(load_config, REPOSITORY_ROOT / "config/settings.yaml")

    for field in fields(config):
        assert getattr(config, field.name) is not None

    for period in config.periods:
        for field in fields(period):
            value = getattr(period, field.name)
            if field.name == "end":
                continue
            assert value is not None


def test_load_config_accepts_csv_and_parquet_storage_formats(tmp_path) -> None:
    """Verify that storage formats can request CSV, Parquet, or both.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")
    settings = yaml.safe_load((REPOSITORY_ROOT / "config/settings.yaml").read_text())
    settings["paths"]["classification_rules"] = "config/classification_rules.csv"
    settings["storage"]["output_base_name"] = "permits_snapshot"
    settings["storage"]["overwrite_outputs"] = False
    settings["storage"]["raw_snapshot_formats"] = ["csv", "parquet"]
    settings["storage"]["processed_output_formats"] = ["parquet", "csv"]
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    config = implemented(load_config, settings_path)

    assert config.raw_snapshot_formats == ("csv", "parquet")
    assert config.processed_output_formats == ("parquet", "csv")
    assert config.output_base_name == "permits_snapshot"
    assert config.overwrite_outputs is False
