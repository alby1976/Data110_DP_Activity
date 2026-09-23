"""Tests for volume analysis.

This module verifies the documented contracts and edge cases of the volume analysis
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
from datetime import date
from pandas.testing import assert_frame_equal

from dp_activity.config import StudyPeriod

from dp_activity.analysis.volume_analysis import VolumeAnalysis


def test_monthly_volume_includes_zero_months() -> None:
    """Verify that monthly volume includes zero months."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True],
            "Period": ["Before", "Before"],
            "YearMonth": pd.to_datetime(["2024-01-01", "2024-03-01"]),
        }
    )

    tables = VolumeAnalysis().run(permits)

    monthly = tables["monthly_volume"]
    assert monthly.loc[monthly["YearMonth"] == pd.Timestamp("2024-02-01"), "PermitCount"].iloc[0] == 0


def test_configured_edges_denominators_and_partial_months() -> None:
    """Include zero edge months and count excluded records in the denominator."""
    table = pd.DataFrame({"Period": ["Before"] * 3, "IncludeResidential": [True, False, True],
                          "applied_date": ["2024-02-01", "2024-02-02", "2024-02-03"]}, index=[2, 2, 8])
    before = table.copy(deep=True)
    tables = VolumeAnalysis([StudyPeriod("Before", date(2024, 1, 15), date(2024, 3, 5))]).run(table)
    monthly = tables["monthly_volume"]
    assert monthly["PermitCount"].tolist() == [0, 2, 0]
    assert monthly["AllPermitCount"].tolist() == [0, 3, 0]
    assert monthly["ExposureDays"].tolist() == [17, 29, 5]
    assert monthly["IsPartialMonth"].tolist() == [True, False, True]
    assert monthly["DP_Rate30"].tolist() == pytest.approx([0, 60 / 29, 0])
    total = tables["permit_volume"].iloc[0]
    assert total["MeanMonthlyCount"] == pytest.approx(2 / 3)
    assert total["MedianMonthlyCount"] == 0
    assert total["ResidentialShare"] == pytest.approx(2 / 3)
    assert total["ExposureDays"] == 51
    assert total["DP_Rate30"] == pytest.approx(60 / 51)
    assert_frame_equal(table, before)


def test_zero_baseline_and_empty_configured_periods() -> None:
    """Retain a period with no records and leave its percentage change undefined."""
    periods = [StudyPeriod("Before", date(2023, 1, 1), date(2023, 1, 31)),
               StudyPeriod("During", date(2024, 1, 1), date(2024, 1, 31))]
    table = pd.DataFrame({"Period": ["During"], "IncludeResidential": [True], "applied_date": ["2024-01-01"]})
    totals = VolumeAnalysis(periods).run(table)["permit_volume"]
    assert totals["PermitCount"].tolist() == [0, 1]
    assert totals["DP_Rate30"].tolist() == pytest.approx([0, 30 / 31])
    assert totals.iloc[1]["AbsoluteChange"] == 1
    assert pd.isna(totals.iloc[1]["PercentChange"])
    empty = VolumeAnalysis(periods).run(table.iloc[:0])
    assert empty["monthly_volume"]["PermitCount"].tolist() == [0, 0]


def test_change_and_contextual_third_period() -> None:
    """Compare only the first two ordered study windows with explicit percent units."""
    periods = [StudyPeriod(name, date(year, 1, 1), date(year, 1, 31))
               for name, year in [("Before", 2022), ("During", 2023), ("Post", 2024)]]
    table = pd.DataFrame({"Period": ["Before", "During", "During", "Post"],
                          "IncludeResidential": [True] * 4,
                          "applied_date": ["2022-01-01", "2023-01-01", "2023-01-02", "2024-01-01"]})
    result = VolumeAnalysis(periods).run(table)["permit_volume"]
    assert result.iloc[1]["PercentChange"] == 100
    assert pd.isna(result.iloc[2]["PercentChange"])


def test_open_period_requires_horizon() -> None:
    """Do not infer complete exposure from the last available application."""
    periods = [StudyPeriod("Post", date(2024, 1, 15), None)]
    table = pd.DataFrame({"Period": ["Post"], "IncludeResidential": [True], "applied_date": ["2024-01-16"]})
    with pytest.raises(ValueError, match="observation_end"):
        VolumeAnalysis(periods).run(table)
    monthly = VolumeAnalysis(periods, observation_end=date(2024, 2, 5)).run(table)["monthly_volume"]
    assert monthly["ExposureDays"].tolist() == [17, 5]
    assert monthly["PermitCount"].tolist() == [1, 0]
    assert monthly["DP_Rate30"].tolist() == pytest.approx([30 / 17, 0])


def test_inferred_exposure_remains_unknown() -> None:
    """Exploratory month inference must not claim complete exposure."""
    table = pd.DataFrame({"Period": ["A"], "IncludeResidential": [False], "YearMonth": ["2024-01-01"]})
    monthly = VolumeAnalysis().run(table)["monthly_volume"]
    assert monthly["ExposureDays"].isna().all()
    assert monthly["IsPartialMonth"].isna().all()
    assert monthly.iloc[0]["PermitCount"] == 0
    assert monthly["DP_Rate30"].isna().all()
    assert VolumeAnalysis().run(table)["permit_volume"]["DP_Rate30"].isna().all()


def test_single_day_exposure_rate() -> None:
    """Count one inclusive exposed day rather than a zero-length interval."""
    table = pd.DataFrame({"Period": ["A"] * 3, "IncludeResidential": [True, True, False],
                          "applied_date": ["2024-02-29"] * 3})
    result = VolumeAnalysis([StudyPeriod("A", date(2024, 2, 29), date(2024, 2, 29))]).run(table)
    for key in ("permit_volume", "monthly_volume"):
        assert result[key]["ExposureDays"].item() == 1
        assert result[key]["DP_Rate30"].item() == 60


@pytest.mark.parametrize("value", [None, "bad", 20240101, "2024-02-01"])
def test_unusable_or_outside_dates_raise(value: object) -> None:
    """Reject silent exclusions from denominators and monthly counts."""
    table = pd.DataFrame({"Period": ["A"], "IncludeResidential": [True], "applied_date": [value]})
    with pytest.raises(ValueError):
        VolumeAnalysis([StudyPeriod("A", date(2024, 1, 1), date(2024, 1, 31))]).run(table)


def test_invalid_configuration_and_inclusion_raise() -> None:
    """Reject overlapping windows and truthy text used as inclusion flags."""
    with pytest.raises(ValueError):
        VolumeAnalysis([StudyPeriod("A", date(2024, 1, 1), None), StudyPeriod("B", date(2024, 2, 1), None)])
    with pytest.raises(TypeError):
        VolumeAnalysis().run(pd.DataFrame({"Period": ["A"], "IncludeResidential": ["False"], "YearMonth": ["2024-01-01"]}))
