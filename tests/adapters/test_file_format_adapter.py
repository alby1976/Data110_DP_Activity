"""Tests for file format adapter.

This module verifies the documented contracts and edge cases of the file format adapter
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

import csv
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from dp_activity.adapters.file_format_adapter import (
    CsvFileAdapter,
    FileFormatAdapter,
    JsonGeoFileAdapter,
    JsonFileAdapter,
    ParquetFileAdapter,
    ReflectiveFileAdapterFactory,
    SocrataFileWriter,
)

Record = dict[str, Any]


SAMPLE_RECORDS = [
    {"permitnum": "DP1", "category": "Residential"},
    {"permitnum": "DP2", "description": "Rowhouse"},
]


def test_writer_infers_csv_adapter_from_extension(tmp_path) -> None:
    """Verify that writer infers csv adapter from extension.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(SAMPLE_RECORDS, tmp_path / "snapshot.csv")

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert output.name == "snapshot.csv"
    assert rows[0]["permitnum"] == "DP1"
    assert rows[1]["description"] == "Rowhouse"
    assert set(rows[0]) == {"permitnum", "category", "description"}


def test_csv_adapter_writes_empty_iterable_as_empty_file(tmp_path) -> None:
    """Verify that the CSV adapter handles an empty source snapshot.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = CsvFileAdapter().save([], tmp_path / "empty.csv")

    assert output.read_text(encoding="utf-8") == ""


def test_writer_can_select_json_adapter_explicitly(tmp_path) -> None:
    """Verify that writer can select json adapter explicitly.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.data",
        adapter="json",
    )

    assert json.loads(output.read_text(encoding="utf-8")) == SAMPLE_RECORDS


def test_json_adapter_preserves_non_ascii_text_and_serializes_dates(tmp_path) -> None:
    """Verify that the JSON adapter produces readable UTF-8 output.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    from datetime import date

    records = [{"permitnum": "DP1", "description": "Backyard suite", "date": date(2026, 9, 19)}]

    output = JsonFileAdapter().save(records, tmp_path / "snapshot.json")

    assert json.loads(output.read_text(encoding="utf-8")) == [
        {"permitnum": "DP1", "description": "Backyard suite", "date": "2026-09-19"}
    ]


def test_jsongeo_adapter_writes_geojson_feature_collection(tmp_path) -> None:
    """Verify that JsonGeo output uses GeoJSON point coordinate order.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    records = [
        {
            "permitnum": "DP1",
            "latitude": "51.0447",
            "longitude": "-114.0719",
            "description": "Backyard suite",
        }
    ]

    output = JsonGeoFileAdapter().save(records, tmp_path / "snapshot.geojson")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["type"] == "FeatureCollection"
    assert payload["features"][0]["type"] == "Feature"
    assert payload["features"][0]["geometry"] == {
        "type": "Point",
        "coordinates": [-114.0719, 51.0447],
    }
    assert payload["features"][0]["properties"]["permitnum"] == "DP1"


def test_jsongeo_adapter_keeps_records_without_coordinates(tmp_path) -> None:
    """Verify that missing or invalid coordinates become null geometry.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    records = [{"permitnum": "DP1", "latitude": "", "longitude": "not-a-number"}]

    output = JsonGeoFileAdapter().save(records, tmp_path / "snapshot.jsongeo")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["features"][0]["geometry"] is None
    assert payload["features"][0]["properties"]["permitnum"] == "DP1"


def test_jsongeo_adapter_accepts_configured_coordinate_fields(tmp_path) -> None:
    """Verify that GeoJSON coordinate field names can be supplied as options.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        [{"permitnum": "DP1", "lat": 51.0, "lon": -114.0}],
        tmp_path / "snapshot.data",
        adapter="jsongeo",
        adapter_options={"latitude_field": "lat", "longitude_field": "lon"},
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["features"][0]["geometry"]["coordinates"] == [-114.0, 51.0]


def test_jsongeo_adapter_rejects_blank_coordinate_field_names() -> None:
    """Verify that GeoJSON coordinate field names are meaningful."""
    with pytest.raises(ValueError, match="coordinate field names"):
        JsonGeoFileAdapter(latitude_field=" ", longitude_field="longitude")


def test_concrete_adapters_reject_directory_output(tmp_path) -> None:
    """Verify that concrete adapters share output-path validation.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output_directory = tmp_path / "existing"
    output_directory.mkdir()

    with pytest.raises(IsADirectoryError, match="Output path is a directory"):
        CsvFileAdapter().save(SAMPLE_RECORDS, output_directory)


def test_factory_loads_adapter_with_reflection() -> None:
    """Verify that factory loads adapter with reflection."""
    factory = ReflectiveFileAdapterFactory()

    adapter = factory.create(
        "dp_activity.adapters.file_format_adapter:CsvFileAdapter"
    )

    assert isinstance(adapter, CsvFileAdapter)


def test_factory_rejects_reflected_class_outside_adapter_contract() -> None:
    """Verify that factory rejects reflected class outside adapter contract."""
    factory = ReflectiveFileAdapterFactory()

    with pytest.raises(TypeError, match="FileFormatAdapter subclass"):
        factory.create("pathlib:Path")


def test_unknown_extension_has_clear_error(tmp_path) -> None:
    """Verify that unknown extension has clear error.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    with pytest.raises(ValueError, match="No file adapter"):
        SocrataFileWriter().save(SAMPLE_RECORDS, tmp_path / "snapshot.unknown")


def test_builtin_factory_aliases() -> None:
    """Verify that builtin factory aliases."""
    factory = ReflectiveFileAdapterFactory()
    assert isinstance(factory.create("csv"), CsvFileAdapter)
    assert isinstance(factory.create(".json"), JsonFileAdapter)
    assert isinstance(factory.create("geojson"), JsonGeoFileAdapter)
    assert isinstance(factory.create("jgeojson"), JsonGeoFileAdapter)
    assert isinstance(factory.create("JsonGeo"), JsonGeoFileAdapter)


def test_writer_accepts_adapter_instance_strategy(tmp_path) -> None:
    """Verify that writer can execute an already constructed adapter strategy.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    adapter = JsonFileAdapter()

    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.anything",
        adapter=adapter,
    )

    assert json.loads(output.read_text(encoding="utf-8")) == SAMPLE_RECORDS


def test_writer_can_include_current_datetime_in_output_name(tmp_path) -> None:
    """Verify that output filenames can include a deterministic UTC timestamp.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.json",
        include_timestamp=True,
        now=datetime(2026, 9, 19, 14, 30, 22, tzinfo=timezone.utc),
    )

    assert output.name == "snapshot_20260919_143022.json"
    assert json.loads(output.read_text(encoding="utf-8")) == SAMPLE_RECORDS


def test_writer_can_include_label_period_and_datetime_in_output_name(tmp_path) -> None:
    """Verify timestamped output names include label and data-period parts.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "development_permits.csv",
        include_timestamp=True,
        label="clean permits",
        data_period="Before: 2022-08-06 to 2024-08-05",
        now=datetime(2026, 9, 19, 14, 30, 22, tzinfo=timezone.utc),
    )

    assert (
        output.name
        == "development_permits_clean_permits_Before_2022-08-06_to_2024-08-05_"
        "20260919_143022.csv"
    )


def test_writer_ignores_label_and_period_without_timestamp(tmp_path) -> None:
    """Verify label and period are filename parts only for timestamped output.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "development_permits.json",
        label="clean permits",
        data_period="Before",
    )

    assert output.name == "development_permits.json"


def test_writer_uses_configured_timestamp_format(tmp_path) -> None:
    """Verify that callers can choose the timestamp string format.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.csv",
        include_timestamp=True,
        timestamp_format="%Y%m%dT%H%M%SZ",
        now=datetime(2026, 9, 19, 14, 30, 22, tzinfo=timezone.utc),
    )

    assert output.name == "snapshot_20260919T143022Z.csv"


@pytest.mark.parametrize("timestamp_format", ["", " ", "%Y/%m/%d"])
def test_writer_rejects_invalid_timestamp_format(tmp_path, timestamp_format: str) -> None:
    """Verify that timestamped paths cannot create blank or nested filenames.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
        timestamp_format: Invalid timestamp format under test.
    """
    with pytest.raises(ValueError, match="timestamp_format"):
        SocrataFileWriter().save(
            SAMPLE_RECORDS,
            tmp_path / "snapshot.json",
            include_timestamp=True,
            timestamp_format=timestamp_format,
            now=datetime(2026, 9, 19, 14, 30, 22, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ("label", "data_period", "message"),
    [
        (" ", "Before", "label"),
        ("clean", "///", "data_period"),
        (123, "Before", "label"),
    ],
)
def test_writer_rejects_invalid_timestamp_filename_parts(
    tmp_path,
    label,
    data_period,
    message: str,
) -> None:
    """Verify timestamp filename label and period parts are filename-safe.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
        label: Candidate label value.
        data_period: Candidate period value.
        message: Expected validation-message fragment.
    """
    with pytest.raises((TypeError, ValueError), match=message):
        SocrataFileWriter().save(
            SAMPLE_RECORDS,
            tmp_path / "snapshot.json",
            include_timestamp=True,
            label=label,
            data_period=data_period,
            now=datetime(2026, 9, 19, 14, 30, 22, tzinfo=timezone.utc),
        )


def test_writer_rejects_options_without_named_adapter(tmp_path) -> None:
    """Verify that constructor options are not silently ignored.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    with pytest.raises(ValueError, match="explicit adapter name"):
        SocrataFileWriter().save(
            SAMPLE_RECORDS,
            tmp_path / "snapshot.csv",
            adapter_options={"unused": True},
        )


def test_writer_rejects_adapter_options_with_instance(tmp_path) -> None:
    """Verify that instances cannot receive construction-only options.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    with pytest.raises(ValueError, match="adapter_options"):
        SocrataFileWriter().save(
            SAMPLE_RECORDS,
            tmp_path / "snapshot.json",
            adapter=JsonFileAdapter(),
            adapter_options={"unused": True},
        )


def test_adapter_validates_records_are_mapping_like(tmp_path) -> None:
    """Verify that all concrete serializers reject non-mapping records clearly.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    with pytest.raises(TypeError, match="Record at position 1"):
        SocrataFileWriter().save(
            [{"permitnum": "DP1"}, "not-a-record"],
            tmp_path / "snapshot.json",
        )


def test_factory_registers_custom_strategy_alias(tmp_path) -> None:
    """Verify that custom adapter strategies can be registered without branching.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """

    class TextFileAdapter(FileFormatAdapter):
        """Minimal custom strategy used to verify alias registration."""

        extensions = (".txt",)

        def __init__(self, prefix: str = "") -> None:
            """Store a deterministic line prefix for the test serializer.

            Args:
                prefix: Text prepended to each serialized permit number.
            """
            self.prefix = prefix

        def save(self, records: Iterable[Record], output_path: Path) -> Path:
            """Write permit numbers as newline-delimited text.

            Args:
                records: Mapping-like permit records.
                output_path: Destination text path.

            Returns:
                The completed text output path.
            """
            path = self.prepare_output_path(output_path)
            rows = self.materialize_records(records)
            path.write_text(
                "\n".join(f"{self.prefix}{row['permitnum']}" for row in rows),
                encoding="utf-8",
            )
            return path

    factory = ReflectiveFileAdapterFactory()
    factory.register("txt", TextFileAdapter)

    output = SocrataFileWriter(factory).save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.txt",
        adapter="txt",
        adapter_options={"prefix": "permit:"},
    )

    assert output.read_text(encoding="utf-8") == "permit:DP1\npermit:DP2"


def test_factory_rejects_non_string_adapter_specification() -> None:
    """Verify that reflected adapter specifications must be strings."""
    with pytest.raises(TypeError, match="must be a string"):
        ReflectiveFileAdapterFactory().create(123)


def test_parquet_adapter_writes_columnar_file(tmp_path) -> None:
    """Verify that the Parquet strategy delegates to the installed engine.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")

    output = ParquetFileAdapter().save(SAMPLE_RECORDS, tmp_path / "snapshot.parquet")

    rows = pd.read_parquet(output).to_dict(orient="records")
    assert rows[0]["permitnum"] == "DP1"
    assert rows[1]["description"] == "Rowhouse"


def test_parquet_adapter_supports_pq_extension(tmp_path) -> None:
    """Verify that the Parquet adapter supports the compact `.pq` suffix.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")

    output = ParquetFileAdapter().save(SAMPLE_RECORDS, tmp_path / "snapshot.pq")

    assert output.suffix == ".pq"
    assert len(pd.read_parquet(output)) == 2
