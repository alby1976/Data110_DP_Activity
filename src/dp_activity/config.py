"""Load, validate, and expose project configuration.

This module converts untrusted YAML settings into validated, immutable project
configuration with repository-relative paths.

Design Pattern:
    Immutable Value Object and Factory Function.

Pattern Rationale:
    Validated YAML is converted once into frozen configuration objects so downstream
    code receives stable settings instead of untrusted dictionaries.

Typical Usage:
    Call load_config() at the composition root and pass the returned immutable settings
    to downstream components.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StudyPeriod:
    """Represent an inclusive policy-period boundary.

    This immutable value object keeps a named date interval together so period logic
    receives validated boundaries rather than unrelated scalar values.

    Attributes:
        name: Human-readable period label.
        start: Inclusive first date in the period.
        end: Inclusive last date, or None for an open-ended period.
    """

    name: str
    start: date
    end: date | None


@dataclass(frozen=True)
class ProjectConfig:
    """Hold validated settings required by the analysis pipeline.

    This immutable value object separates trusted, resolved configuration from the raw
    YAML mapping retained for settings not yet promoted to typed attributes.

    Attributes:
        repository_root: Absolute project root used to resolve relative paths.
        raw_data_dir: Directory for immutable source snapshots.
        processed_data_dir: Directory for transformed data products.
        reports_dir: Directory for reports and reporting exports.
        classification_rules_path: Validated classification-rule CSV path.
        periods: Ordered policy-period definitions.
        raw: Complete validated settings mapping.
    """

    repository_root: Path
    raw_data_dir: Path
    processed_data_dir: Path
    reports_dir: Path
    classification_rules_path: Path
    periods: tuple[StudyPeriod, ...]
    raw: dict[str, Any]


def load_config(settings_path: Path) -> ProjectConfig:
    """Read YAML, validate it, resolve paths, and return immutable settings.

    Args:
        settings_path: Path to the project YAML settings file.

    Returns:
        Validated, immutable project configuration.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Parse YAML and fail clearly when it is malformed.
    # TODO: Check every required section and field.
    # TODO: Parse ISO dates and confirm primary periods do not overlap.
    # TODO: Confirm months 1..12 occur exactly once in the season mapping.
    # TODO: Resolve paths and reject paths that escape repository_root.
    # TODO: Return ProjectConfig; never expose unvalidated YAML directly.
    raise NotImplementedError
