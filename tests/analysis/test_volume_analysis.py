import pandas as pd

from conftest import implemented

from dp_activity.analysis.volume_analysis import VolumeAnalysis


def test_monthly_volume_includes_zero_months() -> None:
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True],
            "Period": ["Before", "Before"],
            "YearMonth": pd.to_datetime(["2024-01-01", "2024-03-01"]),
        }
    )

    tables = implemented(VolumeAnalysis().run, permits)

    monthly = tables["monthly_volume"]
    assert monthly.loc[monthly["YearMonth"] == pd.Timestamp("2024-02-01"), "PermitCount"].iloc[0] == 0

