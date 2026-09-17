import pandas as pd
import pytest

from conftest import implemented

from dp_activity.analysis.type_analysis import TypeAnalysis


def test_type_share_uses_period_residential_total() -> None:
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True, True],
            "Period": ["Before", "Before", "Before"],
            "ResidentialType": ["Rowhouse", "Rowhouse", "Duplex"],
        }
    )

    table = implemented(TypeAnalysis().run, permits)["type_summary"]
    rowhouse = table.loc[table["ResidentialType"] == "Rowhouse"].iloc[0]
    assert rowhouse["TypeShare"] == pytest.approx(2 / 3)

