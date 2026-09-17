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

import pandas as pd

from conftest import implemented

from dp_activity.repositories.output_repository import OutputRepository


def test_table_is_written_without_an_index_column(tmp_path) -> None:
    """Verify that table is written without an index column.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = OutputRepository(tmp_path)
    table = pd.DataFrame({"permit_number": ["DP1"]})

    path = implemented(repository.write_table, table, "permits.csv")

    loaded = pd.read_csv(path)
    assert loaded.columns.tolist() == ["permit_number"]
    assert loaded.loc[0, "permit_number"] == "DP1"
