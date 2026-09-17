import pandas as pd

from conftest import implemented

from dp_activity.analysis.processing_analysis import ProcessingAnalysis


def test_invalid_processing_rows_are_excluded_but_counted() -> None:
    permits = pd.DataFrame(
        {
            "Period": ["Before", "Before", "Before"],
            "HasValidProcessingDays": [True, False, False],
            "ProcessingDays": [10, -1, None],
            "IsPending": [False, False, True],
        }
    )

    tables = implemented(ProcessingAnalysis().run, permits)

    summary = tables["processing_summary"].iloc[0]
    assert summary["ValidCount"] == 1
    assert summary["MedianProcessingDays"] == 10
    assert summary["PendingCount"] == 1

