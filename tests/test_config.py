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

import pytest
import yaml

from conftest import REPOSITORY_ROOT, implemented

from dp_activity.config import load_config


@pytest.mark.parametrize("layout", ["one_file_per_table", "one_workbook", "invalid"])
def test_excel_layout_configuration(tmp_path, layout) -> None:
    """Validate both workbook layouts and reject unknown values.

    Args:
        tmp_path: Isolated configuration directory.
        layout: Requested Excel layout.
    """
    (tmp_path / "config").mkdir()
    settings = _copy_project_settings(tmp_path)
    settings["storage"]["excel_layout"] = layout
    path = tmp_path / "config" / "settings.yaml"
    path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    if layout == "invalid":
        with pytest.raises(ValueError, match="excel_layout"):
            load_config(path)
    else:
        assert load_config(path).excel_layout == layout


@pytest.mark.parametrize("raw_excel", [False, True])
def test_excel_is_supported_only_for_processed_outputs(tmp_path, raw_excel) -> None:
    """Accept configured Excel exports without promising an Excel raw adapter.

    Args:
        tmp_path: Isolated project configuration directory.
        raw_excel: Whether to request unsupported raw Excel storage.
    """
    (tmp_path / "config").mkdir()
    settings = _copy_project_settings(tmp_path)
    settings["storage"]["processed_output_formats"] = ["csv", "xlsx"]
    if raw_excel:
        settings["storage"]["raw_snapshot_formats"] = ["xlsx"]
    settings_path = tmp_path / "config" / "settings.yaml"
    settings_path.parent.mkdir(exist_ok=True)
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    if raw_excel:
        with pytest.raises(ValueError, match="raw_snapshot_formats"):
            load_config(settings_path)
    else:
        assert load_config(settings_path).processed_output_formats == ("csv", "xlsx")


def test_loads_project_settings_and_periods(tmp_path) -> None:
    """Load project defaults without reading a developer's real credentials.

    Raw storage must include CSV but may also enable additional formats.

    Args:
        tmp_path: Isolated repository root containing no local secrets.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(_copy_project_settings(tmp_path)), encoding="utf-8")
    config = implemented(load_config, settings_path)
    assert config.repository_root == tmp_path
    assert config.env_file.path == tmp_path / ".env"
    assert config.socrata_app_token is None
    assert [period.name for period in config.periods][:2] == ["Before", "During"]
    assert config.classification_rules_path.is_file()
    assert config.log_archive.log_file == tmp_path / "reports/pipeline.log"
    assert config.log_archive.archive_existing is True
    assert config.log_archive.archive_dir == tmp_path / "reports/logs/archive"
    assert config.log_archive.archive_timestamp_format == "%Y%m%d_%H%M%S"
    assert config.output_base_name == "development_permits"
    assert config.overwrite_outputs is True
    assert config.output_include_timestamp is False
    assert config.output_timestamp_format == "%Y%m%d_%H%M%S"
    assert "csv" in config.raw_snapshot_formats
    assert config.processed_output_formats == ("csv",)


def test_load_config_returns_populated_attributes(tmp_path) -> None:
    """Verify populated configuration attributes using isolated fixture files.

    Args:
        tmp_path: Temporary repository root used instead of local credentials.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(_copy_project_settings(tmp_path)), encoding="utf-8")
    config = implemented(load_config, settings_path)

    for field in fields(config):
        assert getattr(config, field.name) is not None

    for period in config.periods:
        for field in fields(period):
            value = getattr(period, field.name)
            if field.name == "end":
                continue
            assert value is not None


def test_load_config_accepts_supported_storage_formats(tmp_path) -> None:
    """Verify that storage formats can request every supported writer format.

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
    settings["storage"]["include_timestamp"] = True
    settings["storage"]["timestamp_format"] = "%Y%m%dT%H%M%SZ"
    settings["storage"]["raw_snapshot_formats"] = ["csv", "json", "jgeojson", "parquet"]
    settings["storage"]["processed_output_formats"] = ["parquet", "jgeojson", "json", "csv"]
    settings["logging"]["archive_existing"] = False
    settings["logging"]["archive_dir"] = "reports/logs/old"
    settings["logging"]["archive_timestamp_format"] = "%Y-%m-%d_%H-%M-%S"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    config = implemented(load_config, settings_path)

    assert config.raw_snapshot_formats == ("csv", "json", "jgeojson", "parquet")
    assert config.processed_output_formats == ("parquet", "jgeojson", "json", "csv")
    assert config.output_base_name == "permits_snapshot"
    assert config.overwrite_outputs is False
    assert config.output_include_timestamp is True
    assert config.output_timestamp_format == "%Y%m%dT%H%M%SZ"
    assert config.log_archive.archive_existing is False
    assert config.log_archive.archive_dir == tmp_path / "reports/logs/old"
    assert config.log_archive.archive_timestamp_format == "%Y-%m-%d_%H-%M-%S"


def test_load_config_reads_env_file_and_resolves_named_socrata_token(tmp_path) -> None:
    """Verify that `.env` values are loaded without storing secrets in YAML.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        """
        # Local-only Socrata credentials.
        export SOCRATA_APP_TOKEN="test-token"
        EXTRA_SETTING='kept as text'
        """,
        encoding="utf-8",
    )
    settings = _copy_project_settings(tmp_path)
    settings["paths"]["env_file"] = ".env.local"
    settings["data_source"]["app_token_env"] = "SOCRATA_APP_TOKEN"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    config = implemented(load_config, settings_path)

    assert config.env_file.path == env_file
    assert config.env_file.get("SOCRATA_APP_TOKEN") == "test-token"
    assert config.env_file.get("EXTRA_SETTING") == "kept as text"
    assert config.socrata_app_token == "test-token"
    assert "test-token" not in repr(config)
    assert "kept as text" not in repr(config.env_file)


def test_load_config_allows_missing_env_file(tmp_path) -> None:
    """Verify that a missing local `.env` file behaves like empty settings.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings = _copy_project_settings(tmp_path)
    settings["paths"]["env_file"] = ".env.missing"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    config = implemented(load_config, settings_path)

    assert config.env_file.path == tmp_path / ".env.missing"
    assert config.env_file.variables == ()
    assert config.socrata_app_token is None


@pytest.mark.parametrize(
    ("env_text", "message"),
    [
        ("SOCRATA_APP_TOKEN\n", "expected NAME=value"),
        ("1TOKEN=value\n", "invalid variable name"),
        ("SOCRATA_APP_TOKEN=one\nSOCRATA_APP_TOKEN=two\n", "duplicate variable"),
    ],
)
def test_load_config_rejects_malformed_env_file(
    tmp_path,
    env_text: str,
    message: str,
) -> None:
    """Verify that malformed `.env` files fail with clear validation messages.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
        env_text: Environment-file content to validate.
        message: Expected validation-message fragment.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (tmp_path / ".env").write_text(env_text, encoding="utf-8")
    settings = _copy_project_settings(tmp_path)
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_config(settings_path)


def test_load_config_rejects_env_file_outside_repository(tmp_path) -> None:
    """Verify that the configured environment file cannot escape the repository.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings = _copy_project_settings(tmp_path)
    settings["paths"]["env_file"] = "../outside.env"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    with pytest.raises(ValueError, match="paths.env_file"):
        load_config(settings_path)


@pytest.mark.parametrize("timestamp_format", ["", " ", "%Y/%m/%d"])
def test_load_config_rejects_invalid_output_timestamp_format(
    tmp_path,
    timestamp_format: str,
) -> None:
    """Verify that configured output timestamps remain filename-safe.

    Args:
        tmp_path: Pytest fixture providing an isolated repository-like directory.
        timestamp_format: Invalid timestamp format under test.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings = _copy_project_settings(tmp_path)
    settings["storage"]["timestamp_format"] = timestamp_format
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    with pytest.raises((TypeError, ValueError), match="storage.timestamp_format"):
        load_config(settings_path)


def _copy_project_settings(repository_root) -> dict:
    """Return project settings adjusted for an isolated repository root.

    Args:
        repository_root: Temporary repository-like directory used by a test.

    Returns:
        A mutable settings mapping with required local fixture files created.
    """
    config_dir = repository_root / "config"
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")
    settings = yaml.safe_load((REPOSITORY_ROOT / "config/settings.yaml").read_text())
    settings["paths"]["classification_rules"] = "config/classification_rules.csv"
    settings["paths"]["env_file"] = ".env"
    return settings
