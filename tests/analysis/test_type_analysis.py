"""Tests for type analysis.

This module verifies the documented contracts and edge cases of the type analysis
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

from conftest import implemented

from dp_activity.analysis.type_analysis import TypeAnalysis


def test_type_share_uses_period_residential_total() -> None:
    """Verify that type share uses period residential total."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True, True],
            "Period": ["Before", "Before", "Before"],
            "ResidentialType": ["Rowhouse", "Rowhouse", "Duplex"],
        }
    )

    table = implemented(TypeAnalysis().run, permits)["type_summary"]
    rowhouse = table.loc[table["ResidentialType"] == "Rowhouse"].iloc[0]
    assert rowhouse["TypeShare"] == pytest.approx(2 / 3)
