"""Tests for sensitivity analysis.

This module verifies the documented contracts and edge cases of the sensitivity analysis
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

import pandas as pd

from conftest import implemented

from dp_activity.analysis.sensitivity_analysis import SensitivityAnalysis


def test_all_named_scenarios_are_retained() -> None:
    """Verify that all named scenarios are retained."""
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
