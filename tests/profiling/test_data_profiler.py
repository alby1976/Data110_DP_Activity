import pandas as pd

from conftest import implemented

from dp_activity.profiling.data_profiler import DataProfiler


def test_profile_includes_shape_missingness_and_value_counts() -> None:
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP2"],
            "category": ["Residential", None],
        }
    )

    profile = implemented(DataProfiler().profile, permits, ["category"])

    assert {"summary", "missingness"}.issubset(profile)
    assert profile["summary"].iloc[0]["row_count"] == 2
    assert "category" in profile

