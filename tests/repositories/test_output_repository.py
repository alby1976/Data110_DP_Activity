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

import pandas as pd

from dp_activity.repositories.output_repository import OutputRepository


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
