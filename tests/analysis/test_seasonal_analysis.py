"""Tests for seasonal analysis.

This module verifies the documented contracts and edge cases of the seasonal analysis
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

from dp_activity.analysis.seasonal_analysis import SeasonalAnalysis
from dp_activity.config import StudyPeriod
from dp_activity.features.season_features import add_season_features


def test_headline_seasonal_table_excludes_partial_seasons() -> None:
    """Verify that headline seasonal table excludes partial seasons."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True],
            "Period": ["Before", "Before"],
            "Season": ["Summer", "Fall"],
            "SeasonStartDate": pd.to_datetime(["2022-06-01", "2022-09-01"]),
            "IsCompleteSeason": [False, True],
        }
    )

    tables = SeasonalAnalysis().run(permits)

    assert tables["complete_seasons"]["IsCompleteSeason"].all()
    assert len(tables["partial_seasons"]) == 1


def _featured(periods: list[StudyPeriod], dates: list[str], labels: list[str]) -> pd.DataFrame:
    """Build real season features for deterministic analysis fixtures.

    Args:
        periods: Inclusive windows used to determine season completeness.
        dates: Application dates for the sample records.
        labels: Assigned period labels corresponding to the dates.

    Returns:
        Feature-enriched input using standard meteorological seasons.
    """
    permits = pd.DataFrame({"applied_date": dates, "Period": labels,
                            "IncludeResidential": pd.Series([True] * len(dates), dtype=bool)})
    return add_season_features(permits, date_column="applied_date",
                               season_months={"Winter": [12, 1, 2], "Spring": [3, 4, 5],
                                              "Summer": [6, 7, 8], "Fall": [9, 10, 11]},
                               analysis_windows=periods)


def test_cross_year_zero_seasons_and_monthly_exposure() -> None:
    """Include leap winter and zero seasons without treating partial summer as full."""
    periods = [StudyPeriod("Before", date(2023, 12, 1), date(2024, 6, 15))]
    permits = _featured(periods, ["2023-12-10", "2024-01-10", "2024-02-29"], ["Before"] * 3)
    permits.loc[1, "IncludeResidential"] = False
    original = permits.copy(deep=True)
    tables = SeasonalAnalysis(periods).run(permits)
    summary = tables["seasonal_summary"].set_index("Season")
    assert summary.loc["Winter", "PermitCount"] == 2
    assert summary.loc["Winter", "AllPermitCount"] == 3
    assert summary.loc["Winter", "ExcludedCount"] == 1
    assert summary.loc["Winter", "ExposureDays"] == 91
    assert summary.loc["Winter", "DP_Rate30"] == pytest.approx(60 / 91)
    assert summary.loc["Spring", "PermitCount"] == 0
    assert summary.loc["Spring", "IsCompleteSeason"]
    assert summary.loc["Summer", "ExposureDays"] == 15
    assert summary.loc["Summer", "DP_Rate30"] == 0
    assert len(tables["complete_seasons"]) == 2
    assert len(tables["partial_seasons"]) == 1
    assert tables["unknown_seasons"].empty
    months = tables["calendar_month_summary"].set_index("CalendarMonth")
    assert months.loc[3, "MeanCompleteMonthlyCount"] == 0
    assert months.loc[6, "PartialMonthCount"] == 1
    assert pd.isna(months.loc[6, "MeanCompleteMonthlyCount"])
    pd.testing.assert_frame_equal(permits, original)


def test_policy_boundary_splits_one_season() -> None:
    """Never merge partial summer fragments across policy periods."""
    periods = [StudyPeriod("Before", date(2024, 6, 1), date(2024, 8, 5)),
               StudyPeriod("During", date(2024, 8, 6), date(2024, 11, 30))]
    permits = _featured(periods, ["2024-08-05", "2024-08-06"], ["Before", "During"])
    tables = SeasonalAnalysis(periods).run(permits)
    assert len(tables["partial_seasons"]) == 2
    assert tables["partial_seasons"]["DP_Rate30"].tolist() == pytest.approx([30 / 66, 30 / 26])
    assert tables["partial_seasons"]["PermitCount"].tolist() == [1, 1]
    assert tables["complete_seasons"]["Season"].tolist() == ["Fall"]
    assert tables["complete_seasons"]["PermitCount"].item() == 0


def test_unknown_exposure_is_not_partial_or_complete() -> None:
    """Preserve uncertainty in exploratory features and monthly comparisons."""
    permits = _featured([], ["2024-01-10"], ["Post"])
    tables = SeasonalAnalysis().run(permits)
    assert len(tables["unknown_seasons"]) == 1
    assert tables["complete_seasons"].empty
    assert tables["partial_seasons"].empty
    assert tables["seasonal_summary"]["ExposureDays"].isna().all()
    assert tables["seasonal_summary"]["DP_Rate30"].isna().all()
    assert tables["calendar_month_summary"]["DP_Rate30"].isna().all()
    assert tables["calendar_month_summary"]["UnknownMonthCount"].item() == 1


def test_open_window_requires_horizon() -> None:
    """Require a stated observation cutoff before generating open-ended exposure."""
    periods = [StudyPeriod("Post", date(2024, 9, 1), None)]
    permits = _featured(periods, ["2024-09-10"], ["Post"])
    with pytest.raises(ValueError, match="observation_end"):
        SeasonalAnalysis(periods).run(permits)
    permits["IsCompleteSeason"] = pd.array([False], dtype="boolean")
    permits["IsPartialSeason"] = pd.array([True], dtype="boolean")
    summary = SeasonalAnalysis(periods, observation_end=date(2024, 10, 1)).run(permits)["partial_seasons"]
    assert summary["ExposureDays"].item() == 31


def test_processing_statistics_follow_residential_eligibility() -> None:
    """Exclude pending cases and nonresidential outliers from seasonal medians."""
    periods = [StudyPeriod("Before", date(2024, 3, 1), date(2024, 8, 31))]
    permits = _featured(periods, ["2024-03-10"] * 3, ["Before"] * 3)
    permits["IncludeResidential"] = [True, True, False]
    permits["ProcessingDays"] = [10, None, 1000]
    permits["HasValidProcessingDays"] = [True, False, True]
    permits["IsPending"] = [False, True, False]
    permits["IsRightCensored"] = [False, True, False]
    summary = SeasonalAnalysis(periods).run(permits)["seasonal_summary"].set_index("Season")
    assert summary.loc["Spring", "MedianProcessingDays"] == 10
    assert summary.loc["Spring", "PendingCount"] == 1
    assert summary.loc["Spring", "ValidCount"] == 1
    assert pd.isna(summary.loc["Summer", "MedianProcessingDays"])


@pytest.mark.parametrize("configured", [True, False])
def test_empty_inputs_keep_schemas(configured: bool) -> None:
    """Retain empty calendar seasons only when exposure is explicitly known.

    Args:
        configured: Whether a full season window is supplied.
    """
    periods = [StudyPeriod("Before", date(2024, 3, 1), date(2024, 5, 31))]
    permits = _featured(periods, [], [])
    tables = SeasonalAnalysis(periods if configured else None).run(permits)
    assert len(tables["seasonal_summary"]) == int(configured)
    assert tables["seasonal_summary"]["PermitCount"].sum() == 0
    assert "IsCompleteSeason" in tables["unknown_seasons"]
    assert "DP_Rate30" in tables["unknown_seasons"]


def test_calendar_month_rate_pools_exposure() -> None:
    """Weight unequal February exposure rather than averaging monthly rates."""
    periods = [StudyPeriod("Before", date(2023, 2, 15), date(2024, 2, 29))]
    permits = _featured(periods, ["2023-02-15", "2024-02-01", "2024-02-29"], ["Before"] * 3)
    result = SeasonalAnalysis(periods).run(permits)["calendar_month_summary"]
    february = result.loc[result["CalendarMonth"].eq(2)].iloc[0]
    assert february["ExposureDays"] == 43
    assert february["DP_Rate30"] == pytest.approx(90 / 43)
    assert february["CompleteMonthCount"] == 1
    assert february["PartialMonthCount"] == 1


@pytest.mark.parametrize("field,value", [("Season", "Winter"), ("SeasonStartDate", "2024-03-02"),
                                          ("Period", None), ("SeasonStartDate", None)])
def test_invalid_season_identity(field: str, value: object) -> None:
    """Reject season identities that cannot support a calendar comparison.

    Args:
        field: Season identity column to corrupt.
        value: Invalid label or date.
    """
    periods = [StudyPeriod("Before", date(2024, 3, 1), date(2024, 5, 31))]
    permits = _featured(periods, ["2024-03-10"], ["Before"])
    permits[field] = value
    with pytest.raises(ValueError):
        SeasonalAnalysis(periods).run(permits)


def test_inconsistent_flags_and_dates_are_rejected() -> None:
    """Prevent contradictory exposure from entering headline comparisons."""
    periods = [StudyPeriod("Before", date(2024, 3, 1), date(2024, 5, 31))]
    permits = _featured(periods, ["2024-03-10"] * 2, ["Before"] * 2)
    permits.loc[0, "IsCompleteSeason"] = False
    permits.loc[0, "IsPartialSeason"] = True
    with pytest.raises(ValueError):
        SeasonalAnalysis().run(permits)
    with pytest.raises(ValueError):
        SeasonalAnalysis(periods).run(permits)


def test_configuration_and_schema_validation() -> None:
    """Validate definitions and prerequisites before producing summaries."""
    with pytest.raises(ValueError):
        SeasonalAnalysis(season_months={"Winter": [12, 1, 2]})
    with pytest.raises(TypeError):
        SeasonalAnalysis().run([])
    with pytest.raises(ValueError):
        SeasonalAnalysis().run(pd.DataFrame())
