"""Tests for geography analysis.

This module verifies the documented contracts and edge cases of the geography analysis
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

from dp_activity.analysis.geography_analysis import GeographyAnalysis


def test_small_baseline_is_flagged_not_deleted() -> None:
    """Verify that small baseline is flagged not deleted."""
    permits = pd.DataFrame(
        {
            "IncludeResidential": [True] * 4,
            "Period": ["Before", "During", "During", "During"],
            "Community": ["Varsity"] * 4,
            "Ward": [1] * 4,
        }
    )

    analysis = GeographyAnalysis(minimum_baseline_count=5)
    community = implemented(analysis.run, permits)["community_summary"]

    assert community.loc[community["Community"] == "Varsity", "SmallBaselineWarning"].iloc[0]
