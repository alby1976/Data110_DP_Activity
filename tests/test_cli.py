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

from datetime import date, datetime
import hashlib
import json

import pandas as pd
import pytest
import yaml

from conftest import implemented

from dp_activity import cli
from dp_activity.cli import build_parser
from dp_activity.pipeline.analysis_pipeline import PipelineResult


@pytest.fixture
def download_settings(tmp_path):
    """Write an isolated configuration with deliberately nondefault source values.

    Args:
        tmp_path: Temporary repository root provided by pytest.

    Returns:
        Settings path and its mapping for further per-test customization.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")
    (tmp_path / "test.env").write_text("CUSTOM_TOKEN=fixture-token\n", encoding="utf-8")
    settings = yaml.safe_load(cli.DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))
    settings["data_source"].update({
        "api_base_url": "https://source.example.test/resource/",
        "dataset_id": "abcd-1234", "format": "json", "source_type": "socrata",
        "app_token_env": "CUSTOM_TOKEN", "page_size": 2,
    })
    settings["paths"].update({"env_file": "test.env", "raw_data": "snapshots/custom"})
    settings["storage"].update({
        "output_base_name": "custom_permits", "raw_snapshot_formats": ["json", "csv"],
    })
    settings["study_periods"] = {
        "before": {"label": "Before", "start": "2020-01-01", "end": "2020-12-31"},
        "during": {"label": "During", "start": "2021-01-01", "end": "2021-12-31"},
        "post_repeal": {"label": "After", "start": "2022-01-01"},
    }
    settings["analysis"]["primary_date_field"] = "decision_date"
    path = config_dir / "settings.yaml"
    path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    return path, settings


@pytest.mark.parametrize("include_post", [True, False])
def test_download_uses_settings_end_to_end(
    download_settings, requests_mock, capsys, include_post
) -> None:
    """Honor configured source, credentials, intervals, and all snapshot formats.

    Args:
        download_settings: Isolated configuration path and settings mapping.
        requests_mock: Mock transport used by the real sodapy adapter.
        capsys: Captured output used to verify summaries do not expose tokens.
        include_post: Configured inclusion of the open-ended context period.
    """
    settings_path, settings = download_settings
    settings["analysis"]["include_early_post_repeal"] = include_post
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    rows = [{"permitnum": "DP1"}, {"permitnum": "DP2"}]
    headers = {"Content-Type": "application/json"}
    requests_mock.get("https://source.example.test/resource/abcd-1234.json", [
        {"json": rows, "headers": headers}, {"json": [], "headers": headers},
    ])

    assert cli.main(["--settings", str(settings_path), "download"]) == 0

    assert requests_mock.call_count == 2
    for offset, request in zip((0, 2), requests_mock.request_history):
        assert request.headers["X-App-Token"] == "fixture-token"
        assert request.qs["$limit"] == ["2"]
        assert request.qs["$offset"] == [str(offset)]
        where = request.qs["$where"][0]
        assert "decisiondate >= '2020-01-01t00:00:00'" in where
        assert "decisiondate < '2021-01-01t00:00:00'" in where
        assert "decisiondate < '2022-01-01t00:00:00'" in where
        assert ("decisiondate >= '2022-01-01t00:00:00'" in where) == include_post
        assert "applieddate" not in where

    raw_dir = settings_path.parent.parent / "snapshots/custom"
    snapshots = [path for path in raw_dir.iterdir() if not path.name.endswith(".metadata.json")]
    assert len(snapshots) == 2
    assert {path.suffix for path in snapshots} == {".json", ".csv"}
    for snapshot in snapshots:
        assert snapshot.name.startswith("custom_permits_")
        sidecar_text = snapshot.with_suffix(snapshot.suffix + ".metadata.json").read_text()
        assert "fixture-token" not in sidecar_text
        metadata = json.loads(sidecar_text)
        assert metadata["dataset_id"] == "abcd-1234"
        assert metadata["row_count"] == 2
        assert metadata["sha256"] == hashlib.sha256(snapshot.read_bytes()).hexdigest()
        assert json.loads(metadata["query"])["page_size"] == 2
        if snapshot.suffix == ".json":
            assert json.loads(snapshot.read_text()) == rows
    output = capsys.readouterr()
    assert "Downloaded 2 records" in output.out
    assert "fixture-token" not in output.out + output.err


@pytest.mark.parametrize("section,key,value", [
    ("data_source", "source_type", "csv"),
    ("data_source", "format", "csv"),
    ("data_source", "dataset_id", "invalid"),
    ("data_source", "page_size", 0),
    ("data_source", "page_size", True),
    ("analysis", "primary_date_field", "not_a_date"),
    ("analysis", "include_early_post_repeal", "false"),
])
def test_download_rejects_invalid_settings_before_network(
    download_settings, requests_mock, section, key, value
) -> None:
    """Fail configuration errors before fetching or writing a snapshot.

    Args:
        download_settings: Temporary settings file and mapping.
        requests_mock: Transport fixture recording unexpected requests.
        section: Configuration section to alter.
        key: Invalid field within the section.
        value: Unsupported value supplied by the configuration.
    """
    settings_path, settings = download_settings
    settings[section][key] = value
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    assert cli.main(["--settings", str(settings_path), "download"]) == 1
    assert not requests_mock.called
    assert not (settings_path.parent.parent / "snapshots/custom").exists()


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


def test_main_archives_existing_pipeline_log(monkeypatch, tmp_path) -> None:
    """Verify that main archives an existing log before running the command.

    Args:
        monkeypatch: Pytest fixture used to replace pipeline assembly during the test.
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """

    class StubRunCommand:
        """Provide a successful command double for archive tests."""

        def execute(self) -> PipelineResult:
            """Return an empty pipeline result.

            Returns:
                Empty pipeline output collections suitable for summary printing.
            """
            return PipelineResult(
                cleaned_permits=[],
                analysis_tables={},
                validation_reports={},
                output_paths={},
            )

    class FixedDateTime:
        """Provide a deterministic timestamp for archived log filenames."""

        @staticmethod
        def now(timezone):
            """Return the fixed datetime used by this test.

            Args:
                timezone: Timezone argument supplied by the production code.

            Returns:
                Fixed datetime used to build the archive filename.
            """
            return datetime(2026, 9, 18, 14, 30, 22)

    config_dir = tmp_path / "config"
    reports_dir = tmp_path / "reports"
    config_dir.mkdir()
    reports_dir.mkdir()
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")
    log_file = reports_dir / "pipeline.log"
    log_file.write_text("previous run\n", encoding="utf-8")

    settings = yaml.safe_load(cli.DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))
    settings["paths"]["classification_rules"] = "config/classification_rules.csv"
    settings["logging"]["archive_timestamp_format"] = "%Y%m%d_%H%M%S"
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")

    monkeypatch.setattr(cli, "build_run_command", lambda config, snapshot_path: StubRunCommand())
    monkeypatch.setattr(cli, "datetime", FixedDateTime)

    assert cli.main(["--settings", str(settings_path), "run", "snapshot.csv"]) == 0
    assert not log_file.exists()
    archived_log = tmp_path / "reports/logs/archive/pipeline_20260918_143022.log"
    assert archived_log.read_text(encoding="utf-8") == "previous run\n"


def test_build_pipeline_wires_storage_settings(monkeypatch, tmp_path) -> None:
    """Verify that repository and exporter construction uses storage config.

    Args:
        monkeypatch: Pytest fixture used to replace unfinished pipeline collaborators.
        tmp_path: Pytest fixture providing an isolated repository-like directory.
    """

    class StubRuleLoader:
        """Avoid loading real classification rules in a composition-root wiring test."""

        def load(self, path):
            """Return no rules while preserving the loader interface.

            Args:
                path: Classification-rule path supplied by the config.

            Returns:
                Empty rule list for dependency construction.
            """
            return []

    class CapturingPipeline:
        """Capture assembled dependencies without running scaffolded pipeline code."""

        def __init__(self, **dependencies):
            """Store dependencies passed by the CLI composition root.

            Args:
                dependencies: Keyword dependencies supplied to AnalysisPipeline.
            """
            self.dependencies = dependencies

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "classification_rules.csv").write_text("RuleID\n", encoding="utf-8")

    settings = yaml.safe_load(cli.DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8"))
    settings["paths"]["classification_rules"] = "config/classification_rules.csv"
    settings["storage"]["output_base_name"] = "configured_permits"
    settings["storage"]["overwrite_outputs"] = False
    settings["storage"]["include_timestamp"] = True
    settings["storage"]["timestamp_format"] = "%Y%m%dT%H%M%SZ"
    settings["storage"]["raw_snapshot_formats"] = ["json"]
    settings["storage"]["processed_output_formats"] = ["json", "csv"]
    settings["analysis"]["classification"]["case_sensitive"] = True
    settings_path = config_dir / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    config = cli.load_config(settings_path)

    monkeypatch.setattr(cli, "RuleLoader", StubRuleLoader)
    monkeypatch.setattr(cli, "AnalysisPipeline", CapturingPipeline)

    cutoff = date(2026, 9, 22)
    pipeline = cli._build_pipeline(config, observation_end=cutoff)

    source_repository = pipeline.dependencies["source_repository"]
    exporter = pipeline.dependencies["exporter"]
    geography = next(analysis for analysis in pipeline.dependencies["analyses"]
                     if isinstance(analysis, cli.GeographyAnalysis))
    assert geography.period_order == tuple(period.name for period in config.periods)
    assert geography.community_column == "community"
    assert geography.ward_column == "ward"
    processing = next(analysis for analysis in pipeline.dependencies["analyses"]
                      if isinstance(analysis, cli.ProcessingAnalysis))
    assert processing.period_order == tuple(period.name for period in config.periods)
    seasonal = next(analysis for analysis in pipeline.dependencies["analyses"]
                    if isinstance(analysis, cli.SeasonalAnalysis))
    assert seasonal.periods == list(config.periods)
    assert seasonal.observation_end == cutoff
    assert seasonal.volume.observation_end == cutoff
    volume = next(analysis for analysis in pipeline.dependencies["analyses"]
                  if isinstance(analysis, cli.VolumeAnalysis))
    assert volume.observation_end == cutoff
    assert pipeline.dependencies["feature_builders"][1].keywords["observation_end"] == cutoff
    assert pipeline.dependencies["feature_builders"][2].keywords["observation_end"] == cutoff
    assert seasonal.date_column == settings["analysis"]["primary_date_field"]
    assert seasonal.season_months == {value.get("label", key): value["months"]
                                     for key, value in settings["seasons"].items()}
    assert geography.minimum_baseline_count == settings["analysis"]["community_analysis"]["minimum_baseline_count"]
    assert pipeline.dependencies["classifier"].case_sensitive is True
    assert source_repository.raw_directory == config.raw_data_dir
    assert source_repository.file_format == "json"
    assert source_repository.base_name == "configured_permits"
    assert exporter.output_repository.output_directory == config.processed_data_dir
    assert exporter.output_repository.overwrite_outputs is False
    assert exporter.output_formats == ("json", "csv")
    assert exporter.base_name == "configured_permits"
    assert exporter.include_timestamp is True
    assert pipeline.dependencies["feature_builders"][2].keywords["minimum_days"] == settings["analysis"]["processing_time"]["minimum_days"]
    assert exporter.timestamp_format == "%Y%m%dT%H%M%SZ"


@pytest.mark.parametrize("timestamp,expected", [
    ("2026-09-22T12:30:00Z", date(2026, 9, 22)),
    ("2026-09-22T23:30:00-06:00", date(2026, 9, 23)),
])
def test_snapshot_cutoff_uses_utc_retrieval_date(tmp_path, timestamp, expected) -> None:
    """Use retrieval metadata consistently even when its offset crosses midnight.

    Args:
        tmp_path: Isolated snapshot directory.
        timestamp: Timezone-aware metadata timestamp.
        expected: Corresponding UTC calendar date.
    """
    snapshot = tmp_path / "frozen.csv"
    snapshot.with_suffix(".csv.metadata.json").write_text(
        json.dumps({"retrieved_at_utc": timestamp}), encoding="utf-8",
    )
    assert cli._snapshot_observation_end(snapshot, None) == expected


@pytest.mark.parametrize("metadata", [None, "{", "[]", "{}",
    '{"retrieved_at_utc": 123}', '{"retrieved_at_utc": "2026-09-22"}',
    '{"retrieved_at_utc": "bad"}'])
def test_missing_or_invalid_cutoff_requires_explicit_date(tmp_path, metadata) -> None:
    """Reject unknown horizons rather than substituting wall-clock time.

    Args:
        tmp_path: Isolated snapshot directory.
        metadata: Missing or invalid sidecar content.
    """
    snapshot = tmp_path / "frozen.csv"
    if metadata is not None:
        snapshot.with_suffix(".csv.metadata.json").write_text(metadata, encoding="utf-8")
    with pytest.raises(ValueError, match="--observation-end"):
        cli._snapshot_observation_end(snapshot, None)
    assert cli._snapshot_observation_end(snapshot, date(2026, 9, 21)) == date(2026, 9, 21)


def test_explicit_cutoff_validation_and_cli_dispatch(monkeypatch, tmp_path) -> None:
    """Pass a validated CLI date through command construction.

    Args:
        monkeypatch: Replaces execution with a capture of the requested date.
        tmp_path: Isolated path for cutoff validation.
    """
    with pytest.raises(TypeError, match="calendar date"):
        cli._snapshot_observation_end(tmp_path / "x.csv", datetime(2026, 9, 22))
    assert cli.main(["run", "x.csv", "--observation-end", "2026-02-30"]) == 2
    received = {}

    def capture(config, snapshot_path, *, observation_end):
        """Record the cutoff before interrupting unfinished downstream execution.

        Args:
            config: Loaded project settings.
            snapshot_path: Selected immutable snapshot.
            observation_end: Parsed inclusive cutoff.

        Raises:
            ValueError: Stops this dispatch-only test after capture.
        """
        received["cutoff"] = observation_end
        raise ValueError("captured")

    monkeypatch.setattr(cli, "build_run_command", capture)
    monkeypatch.setattr(cli, "_archive_existing_log", lambda config: None)
    assert cli.main(["run", "x.csv", "--observation-end", "2026-09-22"]) == 1
    assert received["cutoff"] == date(2026, 9, 22)


def test_snapshot_horizon_controls_real_features_and_rates(tmp_path) -> None:
    """Apply one frozen horizon to season exposure and processing censoring.

    Args:
        tmp_path: Directory holding synthetic retrieval metadata.
    """
    snapshot = tmp_path / "frozen.csv"
    snapshot.with_suffix(".csv.metadata.json").write_text(
        json.dumps({"retrieved_at_utc": "2026-09-22T12:00:00Z"}), encoding="utf-8",
    )
    command = cli.build_run_command(cli.load_config(cli.DEFAULT_SETTINGS_PATH), snapshot)
    frame = pd.DataFrame({
        "applied_date": ["2026-09-01"], "decision_date": ["2026-10-01"],
        "IncludeResidential": [True],
    })
    for builder in command.pipeline.feature_builders:
        frame = builder(frame)
    assert bool(frame.iloc[0]["IsRightCensored"])
    assert not bool(frame.iloc[0]["HasValidProcessingDays"])
    assert not bool(frame.iloc[0]["IsCompleteSeason"])
    volume = next(a for a in command.pipeline.analyses if isinstance(a, cli.VolumeAnalysis))
    monthly = volume.run(frame)["monthly_volume"]
    september = monthly.loc[monthly["YearMonth"].eq(pd.Timestamp("2026-09-01"))].iloc[0]
    assert september["ExposureDays"] == 22
    assert september["DP_Rate30"] == pytest.approx(30 / 22)
    seasonal = next(a for a in command.pipeline.analyses if isinstance(a, cli.SeasonalAnalysis))
    fall = seasonal.run(frame)["partial_seasons"]
    fall = fall.loc[fall["SeasonStartDate"].eq(pd.Timestamp("2026-09-01"))].iloc[0]
    assert fall["ExposureDays"] == 22
    assert fall["DP_Rate30"] == pytest.approx(30 / 22)
    override = cli.build_run_command(
        cli.load_config(cli.DEFAULT_SETTINGS_PATH), snapshot, observation_end=date(2026, 9, 21),
    )
    assert override.pipeline.feature_builders[1].keywords["observation_end"] == date(2026, 9, 21)
