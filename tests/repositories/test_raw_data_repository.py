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

from conftest import implemented

from dp_activity.repositories.raw_data_repository import RawDataRepository


def test_snapshot_is_saved_without_overwriting(tmp_path) -> None:
    """Verify that snapshot is saved without overwriting.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    repository = RawDataRepository(tmp_path)
    records = [{"permitnum": "DP1"}]

    path = implemented(repository.save_snapshot, records, {"dataset_id": "6933-unw5"})

    assert path.exists()
    assert "DP1" in path.read_text(encoding="utf-8")
    sidecars = list(tmp_path.glob("*.json"))
    assert sidecars
    assert any("6933-unw5" in item.read_text(encoding="utf-8") for item in sidecars)
