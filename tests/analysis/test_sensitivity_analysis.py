import pandas as pd

from conftest import implemented

from dp_activity.analysis.sensitivity_analysis import SensitivityAnalysis


def test_all_named_scenarios_are_retained() -> None:
    permits = pd.DataFrame({"value": [1, 2]})
    analysis = SensitivityAnalysis(
        {
            "reference": lambda frame: len(frame),
            "narrow": lambda frame: len(frame.iloc[:1]),
        }
    )

    table = implemented(analysis.run, permits)["sensitivity_summary"]

    assert set(table["Scenario"]) == {"reference", "narrow"}
    assert table.set_index("Scenario").loc["narrow", "Result"] == 1

