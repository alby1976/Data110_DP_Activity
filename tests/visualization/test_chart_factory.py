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

from datetime import date

import matplotlib as mpl
import numpy as np
import pandas as pd
import pytest

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

    saved = ChartFactory().save(FakeFigure(), path)

    assert saved == path
    assert path.read_text(encoding="utf-8") == "figure"


def test_monthly_chart_preserves_counts_gaps_and_exposure(tmp_path) -> None:
    """Keep periods separate, disclose coverage, and render a real PNG.

    Args:
        tmp_path: Isolated chart destination.
    """
    table = pd.DataFrame({
        "Period": ["Before", "During", "Before", "During"],
        "YearMonth": ["2024-03-01", "2024-04-01", "2024-01-01", "2024-05-01"],
        "PermitCount": [4, 3, 0, 6],
        "IsPartialMonth": pd.array([True, True, False, None], dtype="boolean"),
    })
    original = table.copy(deep=True)
    old_font = mpl.rcParams["font.size"]
    factory = ChartFactory({"font.size": 12})
    figure = factory.monthly_volume(table, policy_boundaries={"Policy change": date(2024, 3, 15)})
    ax = figure.axes[0]
    before = next(line for line in ax.lines if line.get_label() == "Before")
    assert before.get_ydata()[0] == 0
    assert np.isnan(before.get_ydata()[1])
    assert before.get_ydata()[2] == 4
    assert ax.get_ylim()[0] == 0
    labels = ax.get_legend_handles_labels()[1]
    assert labels.count("Partial month") == 1
    assert labels.count("Unknown exposure") == 1
    assert any(text.get_text() == "Policy change" for text in ax.texts)
    assert mpl.rcParams["font.size"] == old_font
    pd.testing.assert_frame_equal(table, original)
    path = factory.save(figure, tmp_path / "monthly.png")
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("extension", ["svg", "pdf"])
def test_real_vector_output(tmp_path, extension) -> None:
    """Save publication-friendly formats without a desktop display.

    Args:
        tmp_path: Isolated output directory.
        extension: Supported vector output format.
    """
    factory = ChartFactory()
    figure = factory.monthly_volume(pd.DataFrame({
        "Period": ["During"], "YearMonth": ["2024-08-01"], "PermitCount": [0],
    }))
    path = factory.save(figure, tmp_path / f"monthly.{extension}")
    assert path.stat().st_size > 100


def test_empty_chart_has_no_fabricated_series() -> None:
    """Explain empty data instead of drawing invented zero counts."""
    figure = ChartFactory().monthly_volume(pd.DataFrame(columns=["Period", "YearMonth", "PermitCount"]))
    assert not figure.axes[0].lines
    assert any(text.get_text() == "No monthly permit data" for text in figure.axes[0].texts)


@pytest.mark.parametrize("field,value", [
    ("PermitCount", -1), ("PermitCount", 1.5), ("PermitCount", float("inf")),
    ("PermitCount", None), ("PermitCount", True), ("PermitCount", "1"),
    ("YearMonth", "2024-08-02"), ("YearMonth", "invalid"),
    ("YearMonth", "2024-08-01T00:00:00Z"), ("YearMonth", 123),
    ("Period", " "), ("IsPartialMonth", "False"),
])
def test_invalid_monthly_values_are_rejected(field, value) -> None:
    """Reject inputs that could misstate counts or exposure.

    Args:
        field: Column to replace with invalid data.
        value: Invalid scalar value.
    """
    table = pd.DataFrame({"Period": ["During"], "YearMonth": ["2024-08-01"], "PermitCount": [1]})
    table[field] = value
    with pytest.raises((ValueError, TypeError)):
        ChartFactory().monthly_volume(table)


def test_invalid_structure_and_save_requests(tmp_path) -> None:
    """Reject ambiguous row keys, invalid boundaries, and unsupported destinations.

    Args:
        tmp_path: Isolated output directory.
    """
    table = pd.DataFrame({"Period": ["During"] * 2, "YearMonth": ["2024-08-01"] * 2, "PermitCount": [1, 2]})
    factory = ChartFactory()
    with pytest.raises(ValueError, match="once"):
        factory.monthly_volume(table)
    with pytest.raises(ValueError, match="columns"):
        factory.monthly_volume(table.drop(columns="Period"))
    with pytest.raises(TypeError, match="DataFrame"):
        factory.monthly_volume([])
    with pytest.raises(TypeError, match="boundaries"):
        factory.monthly_volume(table.iloc[:1], policy_boundaries={"change": "2024-08-06"})
    with pytest.raises(ValueError, match="extension"):
        factory.save(FakeFigure(), tmp_path / "bad.html")
    with pytest.raises(TypeError, match="savefig"):
        factory.save(object(), tmp_path / "bad.png")
    assert not list(tmp_path.iterdir())
