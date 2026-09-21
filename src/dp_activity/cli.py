"""Command-line entry point for the development-permit pipeline.

This module defines the user-facing command entry point and keeps dependency assembly at
the application boundary.

Design Pattern:
    Composition Root and Command.

Pattern Rationale:
    The CLI is the single place that assembles concrete dependencies, then dispatches
    the user's selected command to the appropriate workflow.

Typical Usage:
    Invoke main() through the module entry point to dispatch a configured project
    workflow.

Implementation Outline:
    1. Build an argument parser with commands such as download, profile, analyse, and run.
    2. Accept an optional settings-file path; default to config/settings.yaml.
    3. Load and validate configuration.
    4. Construct repositories, pipeline stages, analyses, and exporters.
    5. Execute the requested command.
    6. Print a short success summary; convert expected project errors to friendly messages.
    7. Return a non-zero exit code on failure.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from functools import partial
from pathlib import Path

from dp_activity.adapters.socrata_adapter import SocrataAdapter
from dp_activity.analysis.geography_analysis import GeographyAnalysis
from dp_activity.analysis.processing_analysis import ProcessingAnalysis
from dp_activity.analysis.rezoning_analysis import RezoningAnalysis
from dp_activity.analysis.seasonal_analysis import SeasonalAnalysis
from dp_activity.analysis.sensitivity_analysis import SensitivityAnalysis
from dp_activity.analysis.type_analysis import TypeAnalysis
from dp_activity.analysis.volume_analysis import VolumeAnalysis
from dp_activity.classification.classifier import PermitClassifier
from dp_activity.classification.rule_loader import RuleLoader
from dp_activity.cleaning.permit_cleaner import PermitCleaner
from dp_activity.config import LogArchiveConfig, ProjectConfig, load_config
from dp_activity.export.powerbi_exporter import PowerBIExporter
from dp_activity.features.period_features import add_period_features
from dp_activity.features.processing_features import add_processing_features
from dp_activity.features.season_features import add_season_features
from dp_activity.pipeline.analysis_pipeline import AnalysisPipeline, PipelineResult
from dp_activity.repositories.output_repository import OutputRepository
from dp_activity.repositories.raw_data_repository import RawDataRepository
from dp_activity.validation.classification_validator import ClassificationValidator
from dp_activity.validation.data_quality_validator import DataQualityValidator
from dp_activity.validation.schema_validator import SchemaValidator


DEFAULT_SETTINGS_PATH = Path("config/settings.yaml")


@dataclass(frozen=True)
class DownloadCommand:
    """Acquire configured study records and persist immutable raw snapshots.

    This Command composes the source Adapter and persistence Repositories so
    neither component needs to read project configuration itself.

    Attributes:
        adapter: Configured source adapter used for one download.
        repositories: One persistence destination per configured raw format.
        where: SoQL filter built from configured study periods and date field.
        page_size: Configured maximum records requested per API page.
    """

    adapter: SocrataAdapter
    repositories: tuple[RawDataRepository, ...]
    where: str
    page_size: int

    def execute(self) -> tuple[int, tuple[Path, ...]]:
        """Download once and save the same records in every requested format.

        Returns:
            Downloaded row count and paths to completed raw snapshots.

        Raises:
            requests.RequestException: Source retrieval fails.
            ValueError: The adapter rejects the response or serialization fails.
            OSError: A snapshot cannot be persisted. Earlier successful format
                writes may remain if a later format fails.
        """
        records, metadata = self.adapter.download(where=self.where, page_size=self.page_size)
        paths = tuple(
            repository.save_snapshot(records, asdict(metadata))
            for repository in self.repositories
        )
        return len(records), paths


@dataclass(frozen=True)
class RunPipelineCommand:
    """Execute the full analysis pipeline for one raw snapshot.

    This object is the CLI's Command-pattern representation of the ``run`` action. It
    receives already assembled dependencies from the composition root and exposes a
    single execution method to keep dispatch logic simple.

    Attributes:
        pipeline: Fully assembled analysis-pipeline facade.
        snapshot_path: Raw snapshot path supplied by the user.
    """

    pipeline: AnalysisPipeline
    snapshot_path: Path

    def execute(self) -> PipelineResult:
        """Run the pipeline command and return the pipeline result.

        Returns:
            Structured outputs reported by the analysis pipeline.
        """
        return self.pipeline.run(self.snapshot_path)


def build_parser() -> argparse.ArgumentParser:
    """Create and return the project's command-line parser.

    Returns:
        The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="dp-activity",
        description="Run Calgary development-permit activity workflows.",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=DEFAULT_SETTINGS_PATH,
        help="Path to the project settings YAML file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "download", help="Download configured study periods and save raw snapshots."
    )
    run_parser = subparsers.add_parser(
        "run",
        help="Run the complete analysis pipeline for a raw snapshot.",
    )
    run_parser.add_argument(
        "snapshot_path",
        nargs="?",
        type=Path,
        help="Path to the immutable raw snapshot to analyze.",
    )

    return parser


def build_download_command(config: ProjectConfig) -> DownloadCommand:
    """Assemble acquisition dependencies using the loaded YAML settings.

    Args:
        config: Project configuration including source, local token, and storage.

    Returns:
        A download command using every configured raw snapshot format.

    Raises:
        ValueError: Source settings, page size, or study-date settings are invalid.
    """
    source = config.raw["data_source"]
    for key in ("source_type", "api_base_url", "dataset_id", "format"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"data_source.{key} must be a nonblank string.")
    if source["source_type"] != "socrata":
        raise ValueError("The download command requires data_source.source_type: socrata.")
    if source["format"] != "json":
        raise ValueError("The Socrata adapter requires data_source.format: json.")
    page_size = source.get("page_size", 50_000)
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
        raise ValueError("data_source.page_size must be a positive integer.")
    endpoint = f"{source['api_base_url'].rstrip('/')}/{source['dataset_id']}.{source['format']}"
    adapter = SocrataAdapter(endpoint, app_token=config.socrata_app_token)
    repositories = tuple(
        RawDataRepository(
            config.raw_data_dir, file_format=file_format, base_name=config.output_base_name
        )
        for file_format in config.raw_snapshot_formats
    )
    return DownloadCommand(adapter, repositories, _download_where(config), page_size)


def _download_where(config: ProjectConfig) -> str:
    """Translate configured inclusive study dates into a source-field filter.

    Args:
        config: Validated study periods and analysis settings.

    Returns:
        OR-joined study intervals using exclusive midnight upper bounds.

    Raises:
        ValueError: The primary date field is unsupported, the inclusion flag is
            not Boolean, or no study periods remain selected.
    """
    analysis = config.raw.get("analysis", {})
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping.")
    primary_field = analysis.get("primary_date_field")
    date_fields = {
        "applied_date": "applieddate", "decision_date": "decisiondate",
        "released_date": "releaseddate", "completed_date": "completeddate",
    }
    if not isinstance(primary_field, str) or primary_field not in date_fields:
        raise ValueError("analysis.primary_date_field must name a supported permit date field.")
    source_field = date_fields[primary_field]
    include_post = analysis.get("include_early_post_repeal", True)
    if not isinstance(include_post, bool):
        raise ValueError("analysis.include_early_post_repeal must be Boolean.")
    intervals = []
    for key, period in config.raw["study_periods"].items():
        if key == "post_repeal" and not include_post:
            continue
        start = date.fromisoformat(period["start"])
        clause = f"{source_field} >= '{start.isoformat()}T00:00:00'"
        if period.get("end") is not None:
            exclusive_end = date.fromisoformat(period["end"]) + timedelta(days=1)
            clause += f" AND {source_field} < '{exclusive_end.isoformat()}T00:00:00'"
        intervals.append(f"({clause})")
    if not intervals:
        raise ValueError("At least one study period must be included for download.")
    return " OR ".join(intervals)


def build_run_command(config: ProjectConfig, snapshot_path: Path) -> RunPipelineCommand:
    """Assemble concrete dependencies for the run workflow.

    Args:
        config: Validated project configuration.
        snapshot_path: Raw snapshot path supplied by the user.

    Returns:
        A command object that can execute the configured pipeline.
    """
    pipeline = _build_pipeline(config)
    return RunPipelineCommand(pipeline=pipeline, snapshot_path=snapshot_path)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process exit code.

    Args:
        argv: Command-line arguments excluding the executable name, or None to read the
            process arguments.

    Returns:
        A process exit code; zero indicates success.
    """
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    try:
        config = load_config(arguments.settings)

        if arguments.command == "download":
            download_command = build_download_command(config)
            row_count, paths = download_command.execute()
            print(f"Downloaded {row_count} records.")
            for path in paths:
                print(f"Saved raw snapshot: {path}")
            return 0

        if arguments.command == "run":
            if arguments.snapshot_path is None:
                print("error: the run command requires snapshot_path", file=sys.stderr)
                return 2
            _archive_existing_log(config.log_archive)
            command = build_run_command(config, arguments.snapshot_path)
            result = command.execute()
            _print_run_summary(result)
            return 0

        print(f"error: unknown command: {arguments.command}", file=sys.stderr)
        return 2
    except (FileNotFoundError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except NotImplementedError as exc:
        message = str(exc) or "The selected workflow is not implemented yet."
        print(f"error: {message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _build_pipeline(config: ProjectConfig) -> AnalysisPipeline:
    """Construct the concrete pipeline graph at the application boundary.

    Args:
        config: Validated project configuration.

    Returns:
        A fully assembled analysis-pipeline facade.
    """
    rules = RuleLoader().load(config.classification_rules_path)
    analysis_settings = config.raw.get("analysis", {})
    seasons_settings = config.raw.get("seasons", {})
    quality_settings = config.raw.get("quality_checks", {})

    source_repository = RawDataRepository(
        config.raw_data_dir,
        file_format=config.raw_snapshot_formats[0],
        base_name=config.output_base_name,
    )
    cleaner = PermitCleaner(
        column_map=_default_column_map(),
        date_columns=[
            analysis_settings.get("primary_date_field", "applied_date"),
            analysis_settings.get("processing_time", {}).get("end_field", "decision_date"),
        ],
    )
    classifier = PermitClassifier(
        rules=rules,
        field_map=_default_classification_field_map(),
        unmatched_action=analysis_settings.get("classification", {}).get(
            "unmatched_action",
            "Review",
        ),
        case_sensitive=analysis_settings.get("classification", {}).get("case_sensitive", False),
    )
    feature_builders = [
        partial(
            add_period_features,
            date_column=analysis_settings.get("primary_date_field", "applied_date"),
            periods=list(config.periods),
        ),
        partial(
            add_season_features,
            date_column=analysis_settings.get("primary_date_field", "applied_date"),
            season_months={
                key: value["months"]
                for key, value in seasons_settings.items()
                if isinstance(value, dict) and "months" in value
            },
            analysis_windows=list(config.periods),
        ),
        partial(
            add_processing_features,
            applied_date_column=analysis_settings.get("processing_time", {}).get(
                "start_field",
                "applied_date",
            ),
            decision_date_column=analysis_settings.get("processing_time", {}).get(
                "end_field",
                "decision_date",
            ),
        ),
    ]
    validators = [
        partial(
            SchemaValidator().validate,
            required_columns=quality_settings.get("required_columns", []),
        ),
        partial(DataQualityValidator().validate, settings=quality_settings),
        partial(ClassificationValidator().validate, rules=rules),
    ]
    analyses = [
        VolumeAnalysis(),
        TypeAnalysis(),
        GeographyAnalysis(
            minimum_baseline_count=analysis_settings.get("community_analysis", {}).get(
                "minimum_baseline_count",
                5,
            )
        ),
        ProcessingAnalysis(),
        RezoningAnalysis(),
        SeasonalAnalysis(),
        SensitivityAnalysis(scenarios={}),
    ]
    output_repository = OutputRepository(
        config.processed_data_dir,
        overwrite_outputs=config.overwrite_outputs,
    )
    exporter = PowerBIExporter(
        output_repository=output_repository,
        output_formats=config.processed_output_formats,
        base_name=config.output_base_name,
        include_timestamp=config.output_include_timestamp,
        timestamp_format=config.output_timestamp_format,
    )

    return AnalysisPipeline(
        source_repository=source_repository,
        cleaner=cleaner,
        classifier=classifier,
        feature_builders=feature_builders,
        validators=validators,
        analyses=analyses,
        exporter=exporter,
    )


def _default_column_map() -> dict[str, str]:
    """Return Socrata-to-project column mappings used by the default pipeline."""
    return {
        "permitnum": "permit_number",
        "applieddate": "applied_date",
        "decisiondate": "decision_date",
        "releaseddate": "released_date",
        "completeddate": "completed_date",
        "category": "category",
        "description": "description",
        "proposedusecode": "proposed_use_code",
        "proposedusedescription": "proposed_use_description",
        "landusedistrict": "land_use_district",
        "communityname": "community",
        "ward": "ward",
        "latitude": "latitude",
        "longitude": "longitude",
    }


def _default_classification_field_map() -> dict[str, str]:
    """Return rule-field mappings against cleaned permit columns."""
    return {
        "category": "category",
        "description": "description",
        "proposedusecode": "proposed_use_code",
        "proposedusedescription": "proposed_use_description",
        "landusedistrict": "land_use_district",
    }


def _print_run_summary(result: PipelineResult) -> None:
    """Print a concise success summary for a completed pipeline run.

    Args:
        result: Structured pipeline result returned by the run command.
    """
    print("Pipeline completed successfully.")
    print(f"Analysis tables: {len(result.analysis_tables)}")
    print(f"Validation reports: {len(result.validation_reports)}")
    print(f"Output paths: {len(result.output_paths)}")


def _archive_existing_log(
    log_archive: LogArchiveConfig,
    *,
    now: datetime | None = None,
) -> Path | None:
    """Archive the current pipeline log before a new run starts.

    Args:
        log_archive: Validated logging archive settings.
        now: Optional timestamp used for deterministic tests.

    Returns:
        The archived log path, or None when no archive was needed.

    Raises:
        IsADirectoryError: The configured active log path is a directory.
    """
    if not log_archive.archive_existing or not log_archive.log_file.exists():
        return None
    if log_archive.log_file.is_dir():
        raise IsADirectoryError(f"Log file path is a directory: {log_archive.log_file}")

    timestamp = (now or datetime.now(timezone.utc)).strftime(
        log_archive.archive_timestamp_format
    )
    archive_path = (
        log_archive.archive_dir
        / f"{log_archive.log_file.stem}_{timestamp}{log_archive.log_file.suffix}"
    )
    archive_path = _unique_archive_path(archive_path)

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    log_archive.log_file.replace(archive_path)
    return archive_path


def _unique_archive_path(path: Path) -> Path:
    """Return path or a numbered sibling that does not already exist.

    Args:
        path: Preferred archive path.

    Returns:
        A collision-free archive path.
    """
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


if __name__ == "__main__":
    raise SystemExit(main())
