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
import pytest

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

    table = analysis.run(permits)["sensitivity_summary"]

    assert set(table["Scenario"]) == {"reference", "narrow"}
    assert table.set_index("Scenario").loc["narrow", "Result"] == 1


def test_classification_and_complete_season_alternatives() -> None:
    """Retain narrower populations and express their changes against all residential records."""
    permits = pd.DataFrame({
        "IncludeResidential": [True, True, True, False],
        "ClassificationNeedsReview": [False, True, False, False],
        "IsCompleteSeason": pd.array([True, False, None, True], dtype="boolean"),
    })
    analysis = SensitivityAnalysis({
        "reference": lambda frame: frame["IncludeResidential"].sum(),
        "review_excluded": lambda frame: (
            frame["IncludeResidential"] & ~frame["ClassificationNeedsReview"]
        ).sum(),
        "complete_seasons": lambda frame: (
            frame["IncludeResidential"] & frame["IsCompleteSeason"].fillna(False)
        ).sum(),
    })
    table = analysis.run(permits)["sensitivity_summary"].set_index("Scenario")
    assert table.loc["reference", "Result"] == 3
    assert table.loc["review_excluded", "Result"] == 2
    assert table.loc["complete_seasons", "Result"] == 1
    assert table.loc["complete_seasons", "AbsoluteChange"] == -2
    assert table.loc["complete_seasons", "PercentChange"] == pytest.approx(-200 / 3)
    assert table.loc["complete_seasons", "ChangeDirection"] == "decreased"
    assert table.loc["reference", "IsReference"]


def test_scenarios_cannot_mutate_input_or_each_other() -> None:
    """Isolate scalar and nested-object mutations between injected scenarios."""
    permits = pd.DataFrame({"value": [2], "audit": [["original"]]})

    def mutate(frame: pd.DataFrame) -> int:
        """Exercise the copy boundary before returning a hypothetical alternative.

        Args:
            frame: Private scenario input.

        Returns:
            Modified scalar value for comparison.
        """
        frame.loc[0, "value"] = 99
        frame.loc[0, "audit"].append("changed")
        return 99

    scenarios = {"alternative": mutate, "primary": lambda frame: int(frame["value"].sum())}
    analysis = SensitivityAnalysis(scenarios, reference="primary")
    scenarios.clear()
    table = analysis.run(permits)["sensitivity_summary"].set_index("Scenario")
    assert list(table.index) == ["alternative", "primary"]
    assert table.loc["primary", "Result"] == 2
    assert table.loc["alternative", "AbsoluteChange"] == 97
    assert table.loc["alternative", "ChangeDirection"] == "increased"
    assert permits.loc[0, "value"] == 2
    assert permits.loc[0, "audit"] == ["original"]


@pytest.mark.parametrize("baseline", [0, None, pd.NA, float("nan")])
def test_undefined_percentage_changes_remain_missing(baseline: object) -> None:
    """Avoid infinite or fabricated percentage changes for unavailable baselines.

    Args:
        baseline: Zero or unavailable primary metric.
    """
    table = SensitivityAnalysis({"reference": lambda frame: baseline,
                                 "alternative": lambda frame: 2}).run(pd.DataFrame())["sensitivity_summary"]
    assert table["PercentChange"].isna().all()
    if baseline is None or baseline is pd.NA or pd.isna(baseline):
        assert table["AbsoluteChange"].isna().all()
        assert table["ChangeDirection"].eq("unknown").all()


def test_negative_reference_and_missing_alternative() -> None:
    """Use reference magnitude for signed metrics and retain unavailable alternatives."""
    table = SensitivityAnalysis({"reference": lambda frame: -4,
                                 "weaker": lambda frame: -2,
                                 "unknown": lambda frame: None}).run(pd.DataFrame())["sensitivity_summary"]
    weaker = table.set_index("Scenario").loc["weaker"]
    assert weaker["AbsoluteChange"] == 2
    assert weaker["PercentChange"] == 50
    assert table.set_index("Scenario").loc["unknown", "ChangeDirection"] == "unknown"


def test_empty_configuration_is_explicitly_empty() -> None:
    """An unconfigured runner supplies a schema without inventing completed checks."""
    table = SensitivityAnalysis({}).run(pd.DataFrame())["sensitivity_summary"]
    assert table.empty
    assert {"Scenario", "Result", "ReferenceResult", "PercentChange"}.issubset(table.columns)


@pytest.mark.parametrize("scenarios,error", [
    ([], TypeError), ({"reference": 2}, TypeError), ({"": lambda frame: 1}, ValueError),
    ({1: lambda frame: 1}, ValueError), ({"alternative": lambda frame: 1}, ValueError),
])
def test_invalid_configuration_is_rejected(scenarios: object, error: type[Exception]) -> None:
    """Require named callables and an explicit primary comparator.

    Args:
        scenarios: Invalid scenario configuration.
        error: Expected contract exception.
    """
    with pytest.raises(error):
        SensitivityAnalysis(scenarios)


@pytest.mark.parametrize("result,error", [
    (True, TypeError), ("2", TypeError), ([2], TypeError),
    (pd.Series([2]), TypeError), (float("inf"), ValueError),
])
def test_invalid_results_are_rejected(result: object, error: type[Exception]) -> None:
    """Reject ambiguous metrics instead of reporting misleading comparisons.

    Args:
        result: Unsupported scenario output.
        error: Expected contract exception.
    """
    with pytest.raises(error, match="reference"):
        SensitivityAnalysis({"reference": lambda frame: result}).run(pd.DataFrame())


def test_scenario_failure_names_the_scenario_and_preserves_cause() -> None:
    """Surface an unsuccessful alternative without silently discarding it."""
    with pytest.raises(ValueError, match="broken") as caught:
        SensitivityAnalysis({"reference": lambda frame: 1,
                             "broken": lambda frame: 1 / 0}).run(pd.DataFrame())
    assert isinstance(caught.value.__cause__, ZeroDivisionError)
    with pytest.raises(TypeError, match="DataFrame"):
        SensitivityAnalysis({}).run([])
