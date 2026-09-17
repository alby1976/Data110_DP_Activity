"""Tests for permit cleaner.

This module verifies the documented contracts and edge cases of the permit cleaner
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

from dp_activity.cleaning.permit_cleaner import PermitCleaner


def test_cleaner_maps_columns_trims_text_and_parses_dates() -> None:
    """Verify that cleaner maps columns trims text and parses dates."""
    source = pd.DataFrame(
        {
            "permitnum": [" DP1 "],
            "applieddate": ["2024-08-06T00:00:00.000"],
            "communityname": [" Varsity "],
        }
    )
    cleaner = PermitCleaner(
        {"permitnum": "permit_number", "applieddate": "applied_date", "communityname": "community"},
        ["applied_date"],
    )

    cleaned = implemented(cleaner.clean, source)

    assert cleaned.loc[0, "permit_number"] == "DP1"
    assert cleaned.loc[0, "community"] == "Varsity"
    assert pd.api.types.is_datetime64_any_dtype(cleaned["applied_date"])
    assert source.loc[0, "permitnum"] == " DP1 "
