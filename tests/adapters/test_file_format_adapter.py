import csv
import json

import pytest

from dp_activity.adapters.file_format_adapter import (
    CsvFileAdapter,
    JsonFileAdapter,
    ReflectiveFileAdapterFactory,
    SocrataFileWriter,
)


SAMPLE_RECORDS = [
    {"permitnum": "DP1", "category": "Residential"},
    {"permitnum": "DP2", "description": "Rowhouse"},
]


def test_writer_infers_csv_adapter_from_extension(tmp_path) -> None:
    output = SocrataFileWriter().save(SAMPLE_RECORDS, tmp_path / "snapshot.csv")

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert output.name == "snapshot.csv"
    assert rows[0]["permitnum"] == "DP1"
    assert rows[1]["description"] == "Rowhouse"
    assert set(rows[0]) == {"permitnum", "category", "description"}


def test_writer_can_select_json_adapter_explicitly(tmp_path) -> None:
    output = SocrataFileWriter().save(
        SAMPLE_RECORDS,
        tmp_path / "snapshot.data",
        adapter="json",
    )

    assert json.loads(output.read_text(encoding="utf-8")) == SAMPLE_RECORDS


def test_factory_loads_adapter_with_reflection() -> None:
    factory = ReflectiveFileAdapterFactory()

    adapter = factory.create(
        "dp_activity.adapters.file_format_adapter:CsvFileAdapter"
    )

    assert isinstance(adapter, CsvFileAdapter)


def test_factory_rejects_reflected_class_outside_adapter_contract() -> None:
    factory = ReflectiveFileAdapterFactory()

    with pytest.raises(TypeError, match="FileFormatAdapter subclass"):
        factory.create("pathlib:Path")


def test_unknown_extension_has_clear_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="No file adapter"):
        SocrataFileWriter().save(SAMPLE_RECORDS, tmp_path / "snapshot.unknown")


def test_builtin_factory_aliases() -> None:
    factory = ReflectiveFileAdapterFactory()
    assert isinstance(factory.create("csv"), CsvFileAdapter)
    assert isinstance(factory.create(".json"), JsonFileAdapter)
