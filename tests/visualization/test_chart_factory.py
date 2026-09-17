"""Tests for chart factory.

This module verifies the documented contracts and edge cases of the chart factory
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

from conftest import implemented

from dp_activity.visualization.chart_factory import ChartFactory


class FakeFigure:
    """Provide a minimal figure test double.

    The stub records save requests as text files so chart persistence can be tested
    without a plotting dependency.
    """

    def savefig(self, path, **kwargs):
        """Record a figure-save request as a text file.

        Args:
            path: Snapshot or figure path supplied by the caller.
            kwargs: Keyword arguments forwarded to the callable.
        """
        path.write_text("figure", encoding="utf-8")


def test_save_creates_the_requested_chart_file(tmp_path) -> None:
    """Verify that save creates the requested chart file.

    Args:
        tmp_path: Pytest-provided temporary directory isolated to the test.
    """
    path = tmp_path / "figures" / "monthly.png"

    saved = implemented(ChartFactory().save, FakeFigure(), path)

    assert saved == path
    assert path.read_text(encoding="utf-8") == "figure"
