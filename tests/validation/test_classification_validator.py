import pandas as pd

from conftest import implemented

from dp_activity.validation.classification_validator import ClassificationValidator


def test_validation_reports_unmatched_records() -> None:
    permits = pd.DataFrame(
        {
            "ClassificationRule": ["HF-001", None],
            "ClassificationNeedsReview": [False, True],
        }
    )

    report = implemented(ClassificationValidator().validate, permits, [])

    assert "unmatched_count" in report.columns
    assert int(report["unmatched_count"].sum()) == 1

