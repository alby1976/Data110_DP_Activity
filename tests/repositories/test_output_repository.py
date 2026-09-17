import pandas as pd

from conftest import implemented

from dp_activity.repositories.output_repository import OutputRepository


def test_table_is_written_without_an_index_column(tmp_path) -> None:
    repository = OutputRepository(tmp_path)
    table = pd.DataFrame({"permit_number": ["DP1"]})

    path = implemented(repository.write_table, table, "permits.csv")

    loaded = pd.read_csv(path)
    assert loaded.columns.tolist() == ["permit_number"]
    assert loaded.loc[0, "permit_number"] == "DP1"

