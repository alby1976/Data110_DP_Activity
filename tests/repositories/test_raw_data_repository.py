import json

from conftest import implemented

from dp_activity.repositories.raw_data_repository import RawDataRepository


def test_snapshot_is_saved_without_overwriting(tmp_path) -> None:
    repository = RawDataRepository(tmp_path)
    records = [{"permitnum": "DP1"}]

    path = implemented(repository.save_snapshot, records, {"dataset_id": "6933-unw5"})

    assert path.exists()
    assert "DP1" in path.read_text(encoding="utf-8")
    sidecars = list(tmp_path.glob("*.json"))
    assert sidecars
    assert any("6933-unw5" in item.read_text(encoding="utf-8") for item in sidecars)

