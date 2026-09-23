"""Tests for rezoning analysis.

This module verifies the documented contracts and edge cases of the rezoning analysis
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

from dp_activity.analysis.rezoning_analysis import RezoningAnalysis


def test_rezoning_share_uses_all_residential_permits() -> None:
    """Verify that rezoning share uses all residential permits."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True, True, True, False],
            "Period": ["During"] * 4,
            "RezoningRelevant": [True, True, False, True],
            "ClassificationRule": ["A", "A", "B", "C"],
            "ResidentialType": ["Rowhouse", "Duplex", "Apartment", "Commercial"],
        }
    )

    summary = implemented(RezoningAnalysis().run, permits)["rezoning_summary"].iloc[0]

    assert summary["RezoningRelevantShare"] == pytest.approx(2 / 3)
