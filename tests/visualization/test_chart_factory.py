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


@pytest.mark.parametrize("method", ["monthly_volume", "monthly_heatmap"])
@pytest.mark.parametrize("field,value", [
    ("PermitCount", -1), ("PermitCount", 1.5), ("PermitCount", float("inf")),
    ("PermitCount", None), ("PermitCount", True), ("PermitCount", "1"),
    ("YearMonth", "2024-08-02"), ("YearMonth", "invalid"),
    ("YearMonth", "2024-08-01T00:00:00Z"), ("YearMonth", 123),
    ("Period", " "), ("IsPartialMonth", "False"),
])
def test_invalid_monthly_values_are_rejected(field, value, method) -> None:
    """Reject inputs that could misstate counts or exposure.

    Args:
        field: Column to replace with invalid data.
        value: Invalid scalar value.
        method: Chart API sharing the monthly data contract.
    """
    table = pd.DataFrame({"Period": ["During"], "YearMonth": ["2024-08-01"], "PermitCount": [1]})
    table[field] = value
    with pytest.raises((ValueError, TypeError)):
        getattr(ChartFactory(), method)(table)


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


def test_heatmap_keeps_period_fragments_and_missing_months_distinct(tmp_path) -> None:
    """Share a scale across panels without summing boundary-month fragments.

    Args:
        tmp_path: Isolated destination for a rendered PNG.
    """
    table = pd.DataFrame({
        "Period": ["During", "Before", "Before", "During"],
        "YearMonth": ["2024-08-01", "2024-08-01", "2023-12-01", "2025-01-01"],
        "PermitCount": [20, 3, 0, 8],
        "IsPartialMonth": pd.array([True, True, False, None], dtype="boolean"),
    })
    original = table.copy(deep=True)
    old_font = mpl.rcParams["font.size"]
    figure = ChartFactory({"font.size": 11}).monthly_heatmap(table)
    before, during = figure.axes[:2]
    assert [before.get_title(), during.get_title()] == ["Before", "During"]
    bvalues = before.images[0].get_array()
    dvalues = during.images[0].get_array()
    assert bvalues[11, 0] == 0
    assert bvalues[7, 1] == 3
    assert dvalues[7, 0] == 20
    assert np.ma.getmaskarray(bvalues)[0, 0]
    assert not np.ma.getmaskarray(bvalues)[11, 0]
    assert before.images[0].norm is during.images[0].norm
    assert before.images[0].norm.vmin == 0
    assert before.images[0].norm.vmax == 20
    assert "3*" in [text.get_text() for text in before.texts]
    assert "8?" in [text.get_text() for text in during.texts]
    assert [tick.get_text() for tick in before.get_yticklabels()] == [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    pd.testing.assert_frame_equal(table, original)
    assert mpl.rcParams["font.size"] == old_font
    path = ChartFactory().save(figure, tmp_path / "heatmap.png")
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("extension", ["svg", "pdf"])
def test_heatmap_zero_only_and_unknown_coverage(tmp_path, extension) -> None:
    """Keep an all-zero heatmap usable and avoid assuming complete exposure.

    Args:
        tmp_path: Isolated output directory.
        extension: Supported vector destination.
    """
    figure = ChartFactory().monthly_heatmap(pd.DataFrame({
        "Period": ["During"], "YearMonth": ["2024-01-01"], "PermitCount": [0],
    }))
    assert figure.axes[0].images[0].norm.vmax == 1
    assert "0?" in [text.get_text() for text in figure.axes[0].texts]
    path = ChartFactory().save(figure, tmp_path / f"heatmap.{extension}")
    assert path.stat().st_size > 100


def test_heatmap_empty_and_duplicate_inputs() -> None:
    """Explain empty data and reject ambiguous keys instead of aggregating silently."""
    empty = pd.DataFrame(columns=["Period", "YearMonth", "PermitCount"])
    figure = ChartFactory().monthly_heatmap(empty)
    assert not figure.axes[0].images
    assert figure.axes[0].texts[0].get_text() == "No monthly permit data"
    duplicate = pd.DataFrame({"Period": ["Before"] * 2,
                              "YearMonth": ["2024-01-01"] * 2, "PermitCount": [1, 2]})
    with pytest.raises(ValueError, match="once"):
        ChartFactory().monthly_heatmap(duplicate)


@pytest.fixture
def seasonal_table() -> pd.DataFrame:
    """Provide unequal exposure, winter rollover, partial seasons, and unknown coverage.

    Returns:
        Seasonal summary with deliberately misleading precomputed rates to verify pooling.
    """
    return pd.DataFrame({
        "Period": ["Before", "Before", "Before", "During", "During", "During"],
        "Season": ["Winter", "Winter", "Summer", "Summer", "Fall", "Spring"],
        "SeasonStartDate": ["2022-12-01", "2023-12-01", "2024-06-01", "2024-06-01", "2024-09-01", "2024-03-01"],
        "PermitCount": [90, 182, 10, 20, 0, 5],
        "ExposureDays": pd.array([90, 91, 20, 40, 91, None], dtype="Int64"),
        "IsCompleteSeason": pd.array([True, True, False, False, True, None], dtype="boolean"),
        "DP_Rate30": [999] * 6,
    })


def test_season_year_orientation_winter_and_default_cohort(seasonal_table, tmp_path) -> None:
    """Label winter by its ending year and retain excluded seasons as missing cells.

    Args:
        seasonal_table: Fixture with complete, partial, and unknown seasons.
        tmp_path: Destination for visual inspection output.
    """
    original = seasonal_table.copy(deep=True)
    factory = ChartFactory()
    figure = factory.seasonal_year_heatmap(seasonal_table)
    before, during = figure.axes[:2]
    assert [v.get_text() for v in before.get_yticklabels()] == ["Winter", "Spring", "Summer", "Fall"]
    assert [v.get_text() for v in before.get_xticklabels()] == ["2023", "2024"]
    assert before.images[0].get_array()[0, 0] == 90
    assert before.images[0].get_array()[0, 1] == 182
    assert np.ma.getmaskarray(before.images[0].get_array())[2, 1]
    assert during.images[0].get_array()[3, 0] == 0
    assert np.ma.getmaskarray(during.images[0].get_array())[1, 0]
    pd.testing.assert_frame_equal(seasonal_table, original)
    factory.save(figure, tmp_path / "season_year.png")


def test_season_period_pools_exposure_and_flags_partial(seasonal_table, tmp_path) -> None:
    """Use pooled exposure rather than averaging rates or mixing policy fragments.

    Args:
        seasonal_table: Unequal winter exposure fixture.
        tmp_path: Destination for visual inspection output.
    """
    factory = ChartFactory()
    figure = factory.seasonal_period_heatmap(seasonal_table)
    values = figure.axes[0].images[0].get_array()
    assert values[0, 0] == pytest.approx(272 / 181 * 30)
    assert np.ma.getmaskarray(values)[2, :].all()
    included = factory.seasonal_period_heatmap(seasonal_table, include_partial=True)
    values = included.axes[0].images[0].get_array()
    assert values[2, 0] == 15
    assert values[2, 1] == 15
    assert np.ma.getmaskarray(values)[1, 1]
    assert "15.0*" in [text.get_text() for text in included.axes[0].texts]
    factory.save(included, tmp_path / "season_period.png")
    year = factory.seasonal_year_heatmap(seasonal_table, metric="DP_Rate30", include_partial=True)
    assert year.axes[0].images[0].get_array()[0, 1] == 60


@pytest.mark.parametrize("exposure", [None, 0])
def test_season_rate_missing_exposure_is_not_zero(seasonal_table, exposure) -> None:
    """Keep the whole pooled rate unknown when contributing exposure is unusable.

    Args:
        seasonal_table: Seasonal summary fixture.
        exposure: Missing or zero exposure for an eligible winter.
    """
    seasonal_table.loc[0, "ExposureDays"] = exposure
    figure = ChartFactory().seasonal_period_heatmap(seasonal_table)
    assert np.ma.getmaskarray(figure.axes[0].images[0].get_array())[0, 0]


@pytest.mark.parametrize("method", ["seasonal_year_heatmap", "seasonal_period_heatmap"])
def test_seasonal_heatmap_empty_and_invalid_inputs(seasonal_table, method) -> None:
    """Reject ambiguous seasonal identity and invalid count contracts.

    Args:
        seasonal_table: Valid seasonal summary to modify independently.
        method: Seasonal chart API under test.
    """
    render = getattr(ChartFactory(), method)
    assert not render(seasonal_table.iloc[:0]).axes[0].images
    with pytest.raises(ValueError, match="once"):
        render(pd.concat([seasonal_table, seasonal_table.iloc[:1]]))
    for field, value in [("Season", "Autumn"), ("SeasonStartDate", "2024-01-01"),
                         ("PermitCount", -1), ("ExposureDays", -1), ("IsCompleteSeason", "True")]:
        invalid = seasonal_table.copy()
        invalid[field] = value
        with pytest.raises((ValueError, TypeError)):
            render(invalid)
    with pytest.raises(TypeError):
        render(seasonal_table, include_partial="yes")
