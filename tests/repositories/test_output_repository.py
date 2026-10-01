"""Tests for output repository.

This module verifies the documented contracts and edge cases of the output repository
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

import json
from xml.etree import ElementTree
from zipfile import ZipFile

import pandas as pd
import pytest

from dp_activity.repositories.output_repository import OutputRepository


def test_excel_sheets_have_matching_tables_and_preserve_empty_inputs(tmp_path) -> None:
    """Verify real workbook table metadata and zero-row report preservation.

    Args:
        tmp_path: Isolated directory for inspecting generated workbook archives.
    """
    repository = OutputRepository(tmp_path)
    path = repository.write_workbook({
        "permits_clean": pd.DataFrame({"permit": ["=1+1"], "included": [True]}),
        "validation_schema": pd.DataFrame(columns=["severity", "message"]),
    }, "report.xlsx")
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheets = [sheet.attrib["name"] for sheet in workbook.find("s:sheets", namespace)]
        tables = [ElementTree.fromstring(archive.read(f"xl/tables/table{index}.xml"))
                  for index in (1, 2)]
        assert [table.attrib["displayName"] for table in tables] == sheets
        assert [table.attrib["ref"] for table in tables] == ["A1:B2", "A1:B2"]
        assert all(b"<table " in archive.read(f"xl/tables/table{index}.xml")
                   for index in (1, 2))
        empty_sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet2.xml"))
        assert len(empty_sheet.findall("s:sheetData/s:row", namespace)) == 1
        assert empty_sheet.find("s:tableParts", namespace).attrib["count"] == "1"
    single = repository.write_table(pd.DataFrame({"value": [1]}), "single.xlsx")
    with ZipFile(single) as archive:
        assert ElementTree.fromstring(archive.read("xl/tables/table1.xml")).attrib["name"] == "Data"


def test_invalid_excel_table_name_preserves_existing_workbook(tmp_path) -> None:
    """Verify rejected table names never replace an existing output.

    Args:
        tmp_path: Isolated output directory.
    """
    target = tmp_path / "report.xlsx"
    target.write_bytes(b"previous workbook")
    with pytest.raises(ValueError, match="valid Excel table name"):
        OutputRepository(tmp_path).write_workbook(
            {"invalid name": pd.DataFrame({"value": [1]})}, target.name,
        )
    assert target.read_bytes() == b"previous workbook"
    assert not list(tmp_path.glob("*.tmp"))


def test_table_is_written_without_an_index_column(tmp_path) -> None:
    """Verify that table is written without an index column.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = OutputRepository(tmp_path)
    table = pd.DataFrame({"permit_number": ["DP1"]})

    path = repository.write_table(table, "permits.csv")

    loaded = pd.read_csv(path)
    assert loaded.columns.tolist() == ["permit_number"]
    assert loaded.loc[0, "permit_number"] == "DP1"


def test_manifest_is_written_as_stable_json(tmp_path) -> None:
    """Verify that run manifests are readable and sorted for reproducibility.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = OutputRepository(tmp_path)

    path = repository.write_manifest(
        {"snapshot": "raw.csv", "row_count": 1},
        "manifest.json",
    )

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "row_count": 1,
        "snapshot": "raw.csv",
    }
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_existing_output_is_preserved_when_overwrite_is_false(tmp_path) -> None:
    """Verify that repeated writes can preserve an earlier generated artifact.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = OutputRepository(tmp_path, overwrite_outputs=False)

    first_path = repository.write_table(pd.DataFrame({"permit_number": ["DP1"]}), "permits.csv")
    second_path = repository.write_table(pd.DataFrame({"permit_number": ["DP2"]}), "permits.csv")

    assert first_path.name == "permits.csv"
    assert second_path.name == "permits_001.csv"
    assert pd.read_csv(first_path).loc[0, "permit_number"] == "DP1"
    assert pd.read_csv(second_path).loc[0, "permit_number"] == "DP2"
