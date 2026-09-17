"""Load, validate, and expose project configuration.

Keep YAML parsing and validation here so downstream modules receive trusted settings.
All configured paths must be resolved relative to the repository root.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StudyPeriod:
    """Inclusive policy-period boundary."""

    name: str
    start: date
    end: date | None


@dataclass(frozen=True)
class ProjectConfig:
    """Typed settings required by the pipeline."""

    repository_root: Path
    raw_data_dir: Path
    processed_data_dir: Path
    reports_dir: Path
    classification_rules_path: Path
    periods: tuple[StudyPeriod, ...]
    raw: dict[str, Any]


def load_config(settings_path: Path) -> ProjectConfig:
    """Read YAML, validate it, resolve paths, and return immutable settings."""
    # TODO: Parse YAML and fail clearly when it is malformed.
    # TODO: Check every required section and field.
    # TODO: Parse ISO dates and confirm primary periods do not overlap.
    # TODO: Confirm months 1..12 occur exactly once in the season mapping.
    # TODO: Resolve paths and reject paths that escape repository_root.
    # TODO: Return ProjectConfig; never expose unvalidated YAML directly.
    raise NotImplementedError

