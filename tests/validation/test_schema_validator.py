import pandas as pd

from conftest import implemented

from dp_activity.validation.schema_validator import SchemaValidator


def test_missing_required_column_is_an_error() -> None:
    table = pd.DataFrame({"permit_number": ["DP1"]})

    issues = implemented(
        SchemaValidator().validate,
        table,
        ["permit_number", "applied_date"],
    )

    assert any(
        issue.column == "applied_date" and issue.severity.lower() == "error"
        for issue in issues
    )

