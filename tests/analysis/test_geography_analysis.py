import pandas as pd

from conftest import implemented

from dp_activity.analysis.geography_analysis import GeographyAnalysis


def test_small_baseline_is_flagged_not_deleted() -> None:
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True] * 4,
            "Period": ["Before", "During", "During", "During"],
            "Community": ["Varsity"] * 4,
            "Ward": [1] * 4,
        }
    )

    analysis = GeographyAnalysis(minimum_baseline_count=5)
    community = implemented(analysis.run, permits)["community_summary"]

    assert community.loc[community["Community"] == "Varsity", "SmallBaselineWarning"].iloc[0]

