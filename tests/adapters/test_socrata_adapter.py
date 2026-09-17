"""Tests for socrata adapter.

This module verifies the documented contracts and edge cases of the socrata adapter
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

from conftest import implemented

from dp_activity.adapters.socrata_adapter import SocrataAdapter


def test_download_materializes_records_and_metadata(monkeypatch) -> None:
    """Verify that download materializes records and metadata.

    Args:
        monkeypatch: Pytest fixture used to replace behavior during the test.
    """
    adapter = SocrataAdapter("https://example.test/resource/6933-unw5.json")
    rows = [{"permitnum": "DP1"}, {"permitnum": "DP2"}]
    monkeypatch.setattr(adapter, "iter_records", lambda **query: iter(rows))

    downloaded, metadata = implemented(adapter.download, where="applieddate is not null")

    assert downloaded == rows
    assert metadata.row_count == 2
    assert metadata.dataset_id == "6933-unw5"
