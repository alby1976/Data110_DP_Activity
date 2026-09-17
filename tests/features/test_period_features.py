from datetime import date

import pandas as pd

from conftest import implemented

from dp_activity.config import StudyPeriod
from dp_activity.features.period_features import add_period_features


def test_period_boundaries_are_inclusive() -> None:
    permits = pd.DataFrame(
        {"applied_date": pd.to_datetime(["2024-08-05", "2024-08-06", "2026-08-04"])}
    )
    periods = [
        StudyPeriod("Before", date(2022, 8, 6), date(2024, 8, 5)),
        StudyPeriod("During", date(2024, 8, 6), date(2026, 8, 3)),
        StudyPeriod("Early Post-Repeal", date(2026, 8, 4), None),
    ]

    result = implemented(
        add_period_features,
        permits,
        date_column="applied_date",
        periods=periods,
    )

    assert result["Period"].tolist() == ["Before", "During", "Early Post-Repeal"]

