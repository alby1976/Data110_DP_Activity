"""Tests for raw data repository.

This module verifies the documented contracts and edge cases of the raw data repository
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

from dp_activity.repositories.raw_data_repository import RawDataRepository


def test_snapshot_is_saved_without_overwriting(tmp_path) -> None:
    """Verify that snapshot is saved without overwriting.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = RawDataRepository(tmp_path)
    records = [{"permitnum": "DP1"}]

    path = repository.save_snapshot(records, {"dataset_id": "6933-unw5"})

    assert path.exists()
    assert "DP1" in path.read_text(encoding="utf-8")
    sidecars = list(tmp_path.glob("*.json"))
    assert sidecars
    assert any("6933-unw5" in item.read_text(encoding="utf-8") for item in sidecars)


def test_snapshot_metadata_records_count_and_checksum(tmp_path) -> None:
    """Verify that snapshot metadata preserves reproducibility facts.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = RawDataRepository(tmp_path)

    path = repository.save_snapshot(
        [{"permitnum": "DP1"}, {"permitnum": "DP2"}],
        {"dataset_id": "6933-unw5"},
    )

    sidecar = json.loads(path.with_suffix(f"{path.suffix}.metadata.json").read_text())
    assert sidecar["dataset_id"] == "6933-unw5"
    assert sidecar["row_count"] == 2
    assert sidecar["snapshot_file"] == path.name
    assert len(sidecar["sha256"]) == 64


def test_load_snapshot_returns_raw_csv_dataframe(tmp_path) -> None:
    """Verify that a saved CSV snapshot can be loaded without cleaning.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = RawDataRepository(tmp_path)
    path = repository.save_snapshot(
        [{"permitnum": "DP1", "proposedusedescription": " Backyard suite "}],
        {"dataset_id": "6933-unw5"},
    )

    loaded = repository.load_snapshot(path)

    assert isinstance(loaded, pd.DataFrame)
    assert loaded.to_dict(orient="records") == [
        {"permitnum": "DP1", "proposedusedescription": " Backyard suite "}
    ]
