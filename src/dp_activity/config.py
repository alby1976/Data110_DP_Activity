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

import yaml

SUPPORTED_STORAGE_FORMATS = frozenset({"csv", "parquet"})


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
class LogArchiveConfig:
    """Describe how an existing pipeline log should be archived.

    This immutable value object keeps log rollover behavior together so the CLI can
    configure logging without reading raw YAML keys directly.

    Attributes:
        log_file: Current run log path.
        archive_existing: Whether an existing log file should be archived before reuse.
        archive_dir: Directory that receives timestamped archived logs.
        archive_timestamp_format: ``strftime`` format used in archived log names.
    """

    log_file: Path
    archive_existing: bool
    archive_dir: Path
    archive_timestamp_format: str


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
        log_archive: Logging archive settings for pipeline log rollover.
        output_base_name: Extension-free file stem used for configured data outputs.
        overwrite_outputs: Whether generated output files may replace existing files.
        raw_snapshot_formats: Storage formats requested for immutable source snapshots.
        processed_output_formats: Storage formats requested for processed output tables.
        periods: Ordered policy-period definitions.
        raw: Complete validated settings mapping.
    """

    repository_root: Path
    raw_data_dir: Path
    processed_data_dir: Path
    reports_dir: Path
    classification_rules_path: Path
    log_archive: LogArchiveConfig
    output_base_name: str
    overwrite_outputs: bool
    raw_snapshot_formats: tuple[str, ...]
    processed_output_formats: tuple[str, ...]
    periods: tuple[StudyPeriod, ...]
    raw: dict[str, Any]


def load_config(settings_path: Path) -> ProjectConfig:
    """Read YAML, validate it, resolve paths, and return immutable settings.
    
    Args:
        settings_path: Path to the project YAML settings file.

    Returns:
        Validated, immutable project configuration.

    Raises:
        FileNotFoundError: The settings file does not exist.
        ValueError: The settings file is malformed or fails validation.
        TypeError: A required setting has an unexpected type.
    """
    path = Path(settings_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Settings file does not exist: {path}")
    if path.is_dir():
        raise ValueError(f"Settings path must be a file, not a directory: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML in settings file: {path}") from exc

    if not isinstance(loaded, dict):
        raise TypeError("Settings YAML must contain a top-level mapping.")

    raw = dict(loaded)
    repository_root = path.parent.parent.resolve()

    paths = _required_mapping(raw, "paths")
    storage = _required_mapping(raw, "storage")
    logging_settings = _required_mapping(raw, "logging")
    periods_mapping = _required_mapping(raw, "study_periods")
    seasons_mapping = _required_mapping(raw, "seasons")

    raw_data_dir = _resolve_repository_path(
        repository_root,
        _required_string(paths, "raw_data", section="paths"),
        field_name="paths.raw_data",
    )
    processed_data_dir = _resolve_repository_path(
        repository_root,
        _required_string(paths, "processed_data", section="paths"),
        field_name="paths.processed_data",
    )
    reports_dir = _resolve_repository_path(
        repository_root,
        _required_string(paths, "reports", section="paths"),
        field_name="paths.reports",
    )
    classification_rules_path = _resolve_repository_path(
        repository_root,
        _required_string(paths, "classification_rules", section="paths"),
        field_name="paths.classification_rules",
    )
    log_archive = _parse_log_archive(logging_settings, repository_root)

    output_base_name = _parse_output_base_name(storage)
    overwrite_outputs = _required_boolean(
        storage,
        "overwrite_outputs",
        section="storage",
    )
    raw_snapshot_formats = _parse_storage_formats(
        storage,
        "raw_snapshot_formats",
        field_name="storage.raw_snapshot_formats",
    )
    processed_output_formats = _parse_storage_formats(
        storage,
        "processed_output_formats",
        field_name="storage.processed_output_formats",
    )
    periods = _parse_study_periods(periods_mapping)
    _validate_seasons(seasons_mapping)

    return ProjectConfig(
        repository_root=repository_root,
        raw_data_dir=raw_data_dir,
        processed_data_dir=processed_data_dir,
        reports_dir=reports_dir,
        classification_rules_path=classification_rules_path,
        log_archive=log_archive,
        output_base_name=output_base_name,
        overwrite_outputs=overwrite_outputs,
        raw_snapshot_formats=raw_snapshot_formats,
        processed_output_formats=processed_output_formats,
        periods=periods,
        raw=raw,
    )


def _required_mapping(settings: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a required mapping section from settings."""
    value = settings.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"Required section '{key}' must be a mapping.")
    return value


def _required_string(settings: dict[str, Any], key: str, *, section: str) -> str:
    """Return a required non-blank string field from a settings section."""
    value = settings.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"Required field '{section}.{key}' must be a non-blank string.")
    return value


def _required_boolean(settings: dict[str, Any], key: str, *, section: str) -> bool:
    """Return a required Boolean field from a settings section.

    Args:
        settings: Settings section containing the expected field.
        key: Field name to retrieve.
        section: Section name used in validation messages.

    Returns:
        The configured Boolean value.

    Raises:
        TypeError: The field is missing or is not a Boolean.
    """
    value = settings.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"Required field '{section}.{key}' must be true or false.")
    return value


def _parse_iso_date(value: Any, *, field_name: str) -> date:
    """Parse a required ISO-8601 date field."""
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"Required field '{field_name}' must be an ISO date string.")

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Field '{field_name}' must be a valid ISO date: {value!r}") from exc


def _parse_optional_iso_date(value: Any, *, field_name: str) -> date | None:
    """Parse an optional ISO-8601 date field."""
    if value is None:
        return None
    return _parse_iso_date(value, field_name=field_name)


def _parse_study_periods(periods_mapping: dict[str, Any]) -> tuple[StudyPeriod, ...]:
    """Create immutable study periods from a validated mapping."""
    if not periods_mapping:
        raise ValueError("Section 'study_periods' must define at least one period.")

    periods: list[StudyPeriod] = []

    for period_key, period_config in periods_mapping.items():
        if not isinstance(period_key, str) or not period_key.strip():
            raise TypeError("Study period keys must be non-blank strings.")
        if not isinstance(period_config, dict):
            raise TypeError(f"Study period '{period_key}' must be a mapping.")

        label = _required_string(period_config, "label", section=f"study_periods.{period_key}")
        start = _parse_iso_date(
            period_config.get("start"),
            field_name=f"study_periods.{period_key}.start",
        )
        end = _parse_optional_iso_date(
            period_config.get("end"),
            field_name=f"study_periods.{period_key}.end",
        )

        if end is not None and end < start:
            raise ValueError(
                f"Study period '{period_key}' has an end date before its start date."
            )

        periods.append(StudyPeriod(name=label, start=start, end=end))

    ordered_periods = tuple(sorted(periods, key=lambda period: period.start))
    _validate_non_overlapping_periods(ordered_periods)
    return ordered_periods


def _parse_storage_formats(
    storage_mapping: dict[str, Any],
    key: str,
    *,
    field_name: str,
) -> tuple[str, ...]:
    """Return normalized, supported storage formats from the configuration.

    Args:
        storage_mapping: Validated storage section from the settings file.
        key: Storage-list key to parse.
        field_name: Fully qualified field name used in validation messages.

    Returns:
        Normalized storage format names in configured order.

    Raises:
        TypeError: The format list is missing or contains non-string values.
        ValueError: The format list is empty, duplicated, or unsupported.
    """
    configured_formats = storage_mapping.get(key)
    if not isinstance(configured_formats, list) or not configured_formats:
        raise TypeError(f"Field '{field_name}' must be a non-empty list.")

    normalized_formats: list[str] = []
    for configured_format in configured_formats:
        if not isinstance(configured_format, str) or not configured_format.strip():
            raise TypeError(f"All values in '{field_name}' must be non-blank strings.")

        normalized_format = configured_format.strip().lower()
        if normalized_format not in SUPPORTED_STORAGE_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_STORAGE_FORMATS))
            raise ValueError(
                f"Unsupported storage format in '{field_name}': "
                f"{configured_format!r}. Supported formats: {supported}."
            )
        if normalized_format in normalized_formats:
            raise ValueError(
                f"Duplicate storage format in '{field_name}': {normalized_format!r}."
            )
        normalized_formats.append(normalized_format)

    return tuple(normalized_formats)


def _parse_output_base_name(storage_mapping: dict[str, Any]) -> str:
    """Return the extension-free output filename stem from storage settings.

    Args:
        storage_mapping: Validated storage section from the settings file.

    Returns:
        Configured output filename stem.

    Raises:
        TypeError: The configured basename is missing or is not a string.
        ValueError: The configured basename is blank, path-like, or includes a suffix.
    """
    output_base_name = _required_string(
        storage_mapping,
        "output_base_name",
        section="storage",
    ).strip()
    output_path = Path(output_base_name)

    if output_path.name != output_base_name or output_path.parent != Path("."):
        raise ValueError("Field 'storage.output_base_name' must not contain directories.")
    if output_path.suffix:
        raise ValueError("Field 'storage.output_base_name' must not include a file extension.")
    if output_base_name in {".", ".."}:
        raise ValueError("Field 'storage.output_base_name' must be a usable file stem.")

    return output_base_name


def _parse_log_archive(
    logging_mapping: dict[str, Any],
    repository_root: Path,
) -> LogArchiveConfig:
    """Return validated pipeline-log archive settings.

    Args:
        logging_mapping: Validated logging section from the settings file.
        repository_root: Absolute project root used to resolve configured paths.

    Returns:
        Immutable logging archive settings.
    """
    log_file = _resolve_repository_path(
        repository_root,
        _required_string(logging_mapping, "log_file", section="logging"),
        field_name="logging.log_file",
    )
    archive_existing = _required_boolean(
        logging_mapping,
        "archive_existing",
        section="logging",
    )
    archive_dir = _resolve_repository_path(
        repository_root,
        _required_string(logging_mapping, "archive_dir", section="logging"),
        field_name="logging.archive_dir",
    )
    archive_timestamp_format = _required_string(
        logging_mapping,
        "archive_timestamp_format",
        section="logging",
    ).strip()

    if archive_dir == log_file or archive_dir.suffix:
        raise ValueError("Field 'logging.archive_dir' must be a directory path.")
    if not archive_timestamp_format:
        raise ValueError("Field 'logging.archive_timestamp_format' cannot be blank.")

    return LogArchiveConfig(
        log_file=log_file,
        archive_existing=archive_existing,
        archive_dir=archive_dir,
        archive_timestamp_format=archive_timestamp_format,
    )


def _validate_non_overlapping_periods(periods: tuple[StudyPeriod, ...]) -> None:
    """Validate that ordered inclusive study periods do not overlap."""
    for previous, current in zip(periods, periods[1:]):
        if previous.end is None:
            raise ValueError(
                f"Open-ended study period '{previous.name}' must be the final period."
            )
        if current.start <= previous.end:
            raise ValueError(
                "Study periods must not overlap: "
                f"'{previous.name}' ends on {previous.end}, "
                f"but '{current.name}' starts on {current.start}."
            )


def _validate_seasons(seasons_mapping: dict[str, Any]) -> None:
    """Validate that months 1 through 12 appear exactly once across seasons."""
    if not seasons_mapping:
        raise ValueError("Section 'seasons' must define at least one season.")

    seen_months: list[int] = []

    for season_key, season_config in seasons_mapping.items():
        if not isinstance(season_key, str) or not season_key.strip():
            raise TypeError("Season keys must be non-blank strings.")
        if not isinstance(season_config, dict):
            raise TypeError(f"Season '{season_key}' must be a mapping.")

        _required_string(season_config, "label", section=f"seasons.{season_key}")

        months = season_config.get("months")
        if not isinstance(months, list) or not months:
            raise TypeError(f"Field 'seasons.{season_key}.months' must be a non-empty list.")

        for month in months:
            if not isinstance(month, int):
                raise TypeError(
                    f"All values in 'seasons.{season_key}.months' must be integers."
                )
            if month < 1 or month > 12:
                raise ValueError(
                    f"Invalid month in 'seasons.{season_key}.months': {month}. "
                    "Months must be between 1 and 12."
                )
            seen_months.append(month)

    expected_months = set(range(1, 13))
    actual_months = set(seen_months)

    if actual_months != expected_months or len(seen_months) != 12:
        duplicates = sorted(month for month in actual_months if seen_months.count(month) > 1)
        missing = sorted(expected_months - actual_months)

        problems = []
        if missing:
            problems.append(f"missing months: {missing}")
        if duplicates:
            problems.append(f"duplicate months: {duplicates}")

        raise ValueError(
            "Season mappings must contain each month from 1 through 12 exactly once"
            + (f" ({'; '.join(problems)})." if problems else ".")
        )


def _resolve_repository_path(repository_root: Path, configured_path: str, *, field_name: str) -> Path:
    """Resolve a configured path and reject paths outside repository_root."""
    candidate = Path(configured_path).expanduser()

    if not candidate.is_absolute():
        candidate = repository_root / candidate

    resolved = candidate.resolve()

    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise ValueError(
            f"Configured path '{field_name}' escapes repository root: {configured_path!r}"
        ) from exc

    return resolved
