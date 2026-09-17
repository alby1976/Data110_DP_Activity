import pandas as pd

from conftest import implemented

from dp_activity.validation.data_quality_validator import DataQualityValidator


def test_duplicate_permit_numbers_are_reported() -> None:
    permits = pd.DataFrame(
        {
            "permit_number": ["DP1", "DP1"],
            "applied_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        }
    )

    results = implemented(DataQualityValidator().validate, permits, {})

    duplicate_check = next(item for item in results if "duplicate" in item.check_name.lower())
    assert duplicate_check.affected_rows == 2
    assert duplicate_check.status.lower() in {"warn", "fail"}

