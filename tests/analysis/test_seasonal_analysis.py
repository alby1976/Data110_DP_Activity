import pandas as pd

from conftest import implemented

from dp_activity.analysis.seasonal_analysis import SeasonalAnalysis


def test_headline_seasonal_table_excludes_partial_seasons() -> None:
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True],
            "Period": ["Before", "Before"],
            "Season": ["Summer", "Fall"],
            "SeasonStartDate": pd.to_datetime(["2022-06-01", "2022-09-01"]),
            "IsCompleteSeason": [False, True],
        }
    )

    tables = implemented(SeasonalAnalysis().run, permits)

    assert tables["complete_seasons"]["IsCompleteSeason"].all()
    assert len(tables["partial_seasons"]) == 1

