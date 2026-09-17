from conftest import implemented

from dp_activity.adapters.socrata_adapter import SocrataAdapter


def test_download_materializes_records_and_metadata(monkeypatch) -> None:
    adapter = SocrataAdapter("https://example.test/resource/6933-unw5.json")
    rows = [{"permitnum": "DP1"}, {"permitnum": "DP2"}]
    monkeypatch.setattr(adapter, "iter_records", lambda **query: iter(rows))

    downloaded, metadata = implemented(adapter.download, where="applieddate is not null")

    assert downloaded == rows
    assert metadata.row_count == 2
    assert metadata.dataset_id == "6933-unw5"

