from pathlib import Path

from conftest import REPOSITORY_ROOT, implemented

from dp_activity.config import load_config


def test_loads_project_settings_and_periods() -> None:
    config = implemented(load_config, REPOSITORY_ROOT / "config/settings.yaml")
    assert config.repository_root == REPOSITORY_ROOT
    assert [period.name for period in config.periods][:2] == ["Before", "During"]
    assert config.classification_rules_path.is_file()

