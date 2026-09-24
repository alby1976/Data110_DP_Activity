"""Create consistent, accessible charts from analysis tables.

This module centralizes accessible chart construction and explicit figure persistence
for consistent project visuals.

Design Pattern:
    Factory.

Pattern Rationale:
    It centralizes figure construction and styling so callers request a chart type
    without duplicating plotting setup.

Typical Usage:
    Build charts from finalized analysis tables and save the resulting figures
    explicitly.
"""

from __future__ import annotations

from pathlib import Path
from datetime import date
from typing import Any

import matplotlib as mpl
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd


class ChartFactory:
    """Construct consistent charts from finalized analysis tables.

    This class implements a Factory for centralized figure construction and styling;
    saving remains an explicit operation.

    Attributes:
        style: Project-level plotting options applied during chart creation.
    """

    def __init__(self, style: dict[str, Any] | None = None) -> None:
        """Copy Matplotlib rc settings for locally scoped figure construction.

        Args:
            style: Optional Matplotlib rcParams overrides, such as figure.figsize.

        Raises:
            TypeError: Style is not a dictionary.
        """
        if style is not None and not isinstance(style, dict):
            raise TypeError("style must be a dictionary of Matplotlib rc settings.")
        self.style = dict(style or {})

    def monthly_volume(
        self, table: Any, *, policy_boundaries: dict[str, date] | None = None,
    ) -> Figure:
        """Build a period-aware monthly volume chart.

        Args:
            table: DataFrame with Period, YearMonth (timezone-free month starts),
                and finite nonnegative integer PermitCount. Optional nullable
                Boolean IsPartialMonth identifies exposure. One row is allowed
                per period/month. Counts are already aggregated residential records.
            policy_boundaries: Optional labels mapped to exact calendar dates.
                No boundary is inferred from observed applications.

        Returns:
            Headless Figure with chronologically ordered period series, gaps for
            absent months, and zero-based count axis. Triangles mark partial
            months; crosses mark unknown exposure (including absent flags).
            Empty input displays an explicit no-data message. No file is saved.

        Raises:
            TypeError: Table, labels, counts, flags, or boundaries have wrong types.
            ValueError: Required columns, month starts, counts, or row keys are invalid.

        Note:
            Input and global Matplotlib settings are preserved. Counts are not
            normalized for month length; markers disclose partial coverage but
            do not make partial periods equivalent. Policy boundaries annotate
            timing and do not imply causation.
        """
        frame = _monthly_frame(table)
        boundaries = {} if policy_boundaries is None else policy_boundaries
        if not isinstance(boundaries, dict) or any(
            not isinstance(label, str) or not label.strip() or type(value) is not date
            for label, value in boundaries.items()
        ):
            raise TypeError("Policy boundaries must map nonblank labels to calendar dates.")
        defaults = {"figure.figsize": (10, 5), "font.size": 10, "axes.spines.top": False,
                    "axes.spines.right": False, **self.style}
        with mpl.rc_context(defaults):
            figure = Figure()
            FigureCanvasAgg(figure)
            ax = figure.subplots()
            palette = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00")
            ordered = frame.sort_values(["YearMonth", "Period"], kind="stable")
            partial_label = unknown_label = True
            for index, (period, group) in enumerate(ordered.groupby("Period", sort=False, observed=True)):
                color = palette[index % len(palette)]
                series = group.set_index("YearMonth")["PermitCount"].astype(float)
                series = series.reindex(pd.date_range(series.index.min(), series.index.max(), freq="MS"))
                ax.plot(series.index, series.values, color=color, marker="o", label=period,
                        linestyle=("-", "--", "-.", ":")[index % 4], linewidth=1.6)
                for mask, marker, label in (
                    (group["IsPartialMonth"].eq(True).fillna(False), "^", "Partial month"),
                    (group["IsPartialMonth"].isna(), "x", "Unknown exposure"),
                ):
                    points = group.loc[mask]
                    if not points.empty:
                        show = partial_label if marker == "^" else unknown_label
                        ax.scatter(points["YearMonth"], points["PermitCount"], marker=marker,
                                   color=color, s=70, zorder=3, label=label if show else "_nolegend_")
                        if marker == "^":
                            partial_label = False
                        else:
                            unknown_label = False
            for label, boundary in boundaries.items():
                ax.axvline(boundary, color="#666666", linestyle=":", linewidth=1)
                ax.text(boundary, .98, label, transform=ax.get_xaxis_transform(),
                        rotation=90, va="top", ha="right", fontsize=8)
            if frame.empty:
                ax.text(.5, .5, "No monthly permit data", transform=ax.transAxes, ha="center")
            else:
                ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
            locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            ax.set(title="Monthly residential development-permit applications", xlabel="Application month",
                   ylabel="Residential application records", ylim=(0, None))
            ax.grid(axis="y", alpha=.25)
            figure.text(.01, .01, "Counts are not adjusted for month length or partial coverage.", fontsize=8)
            figure.tight_layout(rect=(0, .05, 1, 1))
        return figure

    def monthly_heatmap(self, table: Any) -> Figure:
        """Compare monthly residential counts without merging policy-period fragments.

        Args:
            table: Monthly analysis DataFrame with Period, YearMonth, PermitCount,
                and optional nullable Boolean IsPartialMonth. Counts must be
                finite nonnegative integers, with unique period/month keys and
                timezone-free month starts, as for monthly_volume.

        Returns:
            Headless Figure with a month-by-year panel for each policy period,
            ordered by its earliest observed month, and one shared zero-based
            color scale. Missing months are gray and labelled with a dash;
            supplied zeros are colored and labelled 0. An asterisk marks partial
            exposure and a question mark marks unknown exposure. Empty input
            displays a no-data message. Saving remains explicit.

        Raises:
            TypeError: Table or field types are unsupported.
            ValueError: Required columns, month starts, counts, or row keys are invalid.

        Note:
            Counts are not rates, dwellings, or evidence of policy causation.
            Periods sharing a boundary month remain separate panels. Absent
            exposure flags mean unknown coverage, never complete coverage.
            The input and global Matplotlib settings are preserved.
        """
        frame = _monthly_frame(table)
        groups = list(frame.sort_values(["YearMonth", "Period"], kind="stable").groupby(
            "Period", sort=False, observed=True,
        ))
        panels = []
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for period, group in groups:
            years = list(range(int(group["YearMonth"].dt.year.min()), int(group["YearMonth"].dt.year.max()) + 1))
            values = np.full((12, len(years)), np.nan)
            markers = {}
            for row in group.itertuples(index=False):
                cell = (row.YearMonth.month - 1, row.YearMonth.year - years[0])
                values[cell] = row.PermitCount
                markers[cell] = "?" if pd.isna(row.IsPartialMonth) else "*" if row.IsPartialMonth else ""
            panels.append((str(period), months, years, values, markers))
        return _heatmap_figure(
            panels, self.style, "Monthly residential development-permit applications",
            "Residential application records", "Year", "Month", 0,
            "* Partial month    ? Unknown exposure    – No supplied data\n"
            "Counts are not adjusted for month length or partial coverage.",
        )

    def seasonal_year_heatmap(
        self, table: Any, *, metric: str = "PermitCount", include_partial: bool = False,
    ) -> Figure:
        """Plot meteorological seasons against season years in policy-period panels.

        Args:
            table: SeasonalAnalysis seasonal_summary with Period, Season,
                SeasonStartDate, PermitCount, IsCompleteSeason, and ExposureDays
                when plotting rates. Standard English meteorological seasons apply.
            metric: PermitCount or DP_Rate30, calculated from count and exposure.
            include_partial: Include known partial seasons, marked with an asterisk.
                Unknown completeness is always excluded.

        Returns:
            Figure with Winter/Spring/Summer/Fall rows and season-year columns.
            Winter December 2023 through February 2024 belongs to season year 2024.
            Policy-period fragments remain separate panels with a shared scale.
            Missing/excluded cells remain gray; supplied zero counts remain zero.

        Raises:
            TypeError: Table, flags, counts, or options have unsupported types.
            ValueError: Seasons, dates, metric, exposure, or keys are invalid.

        Note:
            Complete seasons are the default. Rates are permits per 30 exposed
            calendar days, not calendar-month averages. This chart cannot show
            that policy caused the observed changes. Saving remains explicit.
        """
        frame = _seasonal_frame(table, metric, include_partial)
        seasons = ["Winter", "Spring", "Summer", "Fall"]
        panels = []
        for period, group in frame.groupby("Period", sort=False, observed=True):
            years = list(range(int(group["SeasonYear"].min()), int(group["SeasonYear"].max()) + 1))
            values = np.full((4, len(years)), np.nan)
            markers = {}
            for row in group.itertuples(index=False):
                if not row.Eligible:
                    continue
                cell = (seasons.index(row.Season), row.SeasonYear - years[0])
                values[cell] = _season_value(group.loc[group["SeasonStartDate"].eq(row.SeasonStartDate)], metric)
                markers[cell] = "" if row.IsCompleteSeason else "*"
            panels.append((str(period), seasons, years, values, markers))
        return _heatmap_figure(
            panels, self.style, "Residential permits by season and year",
            "Residential application records" if metric == "PermitCount" else "Permits per 30 exposed days",
            "Season year (winter labelled by January/February year)", "Season", 0 if metric == "PermitCount" else 1,
            _season_note(include_partial),
        )

    def seasonal_period_heatmap(self, table: Any, *, include_partial: bool = False) -> Figure:
        """Compare pooled seasonal permit rates across policy periods.

        Args:
            table: SeasonalAnalysis seasonal_summary with the seasonal-year
                heatmap's fields, including ExposureDays.
            include_partial: Include and mark known partial seasons. Unknown
                completeness is excluded even when this option is true.

        Returns:
            Figure with season rows and policy-period columns, ordered by first
            season start. Cells use sum(PermitCount) / sum(ExposureDays) * 30,
            never the mean of individual rates. Any contributing unknown or
            nonpositive exposure leaves the cell missing. Empty cohorts remain
            missing rather than zero. Shared color scale starts at zero.

        Raises:
            TypeError: Inputs or inclusion options have unsupported types.
            ValueError: Seasonal identities, row keys, counts, or exposure are invalid.

        Note:
            Rates adjust exposure length, not confounding or unequal study design.
            A complete season does not make a contextual policy period comparable.
        """
        frame = _seasonal_frame(table, "DP_Rate30", include_partial)
        seasons = ["Winter", "Spring", "Summer", "Fall"]
        periods = list(frame["Period"].drop_duplicates())
        panels = []
        if periods:
            values = np.full((4, len(periods)), np.nan)
            markers = {}
            for (period, season), group in frame.loc[frame["Eligible"]].groupby(
                ["Period", "Season"], sort=False, observed=True,
            ):
                cell = (seasons.index(season), periods.index(period))
                values[cell] = _season_value(group, "DP_Rate30")
                markers[cell] = "*" if group["IsCompleteSeason"].eq(False).any() else ""
            panels.append(("Pooled seasonal rates", seasons, periods, values, markers))
        return _heatmap_figure(
            panels, self.style, "Residential permits by season and policy period",
            "Permits per 30 exposed days", "Policy period", "Season", 1, _season_note(include_partial),
        )

    def save(self, figure: Any, path: Path) -> Path:
        """Save one chart with reproducible dimensions and accessible resolution.

        Args:
            figure: Figure-like object exposing a savefig operation.
            path: Path used by the operation.

        Returns:
            The completed chart path.

        Raises:
            TypeError: Figure has no callable savefig method.
            ValueError: The extension is not PNG, SVG, or PDF.
            OSError: Directory creation or file persistence fails.

        Note:
            Uses 150 DPI and tight bounds. Existing destinations are replaced;
            the caller retains ownership of the figure.
        """
        path = Path(path)
        if path.suffix.lower() not in {".png", ".svg", ".pdf"}:
            raise ValueError("Chart extension must be .png, .svg, or .pdf.")
        if not callable(getattr(figure, "savefig", None)):
            raise TypeError("figure must expose a callable savefig method.")
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, format=path.suffix.lower()[1:], dpi=150, bbox_inches="tight")
        return path


def _monthly_frame(table: Any) -> pd.DataFrame:
    """Validate and copy monthly counts for consistent chart semantics.

    Args:
        table: Monthly analysis DataFrame with period, month, count, and optional exposure flag.

    Returns:
        Independent table with parsed month starts and an explicit nullable exposure flag.

    Raises:
        TypeError: Table or field types are unsupported.
        ValueError: Required columns, month starts, counts, or row keys are invalid.
    """
    if not isinstance(table, pd.DataFrame):
        raise TypeError("table must be a pandas DataFrame.")
    required = {"Period", "YearMonth", "PermitCount"}
    if not table.columns.is_unique or not required.issubset(table.columns):
        raise ValueError("Monthly charts require unique Period, YearMonth, PermitCount columns.")
    frame = table.copy(deep=True)
    if any(not isinstance(v, str) or not v.strip() for v in frame["Period"]):
        raise ValueError("Periods must be nonblank strings.")
    if len(frame) and (not pd.api.types.is_numeric_dtype(frame["PermitCount"])
                       or pd.api.types.is_bool_dtype(frame["PermitCount"])):
        raise TypeError("PermitCount must be numeric.")
    counts = frame["PermitCount"].to_numpy(dtype=float, na_value=np.nan)
    if not np.isfinite(counts).all() or (counts < 0).any() or (counts % 1 != 0).any():
        raise ValueError("PermitCount must contain finite nonnegative integers.")
    if any(not isinstance(value, (str, date)) for value in frame["YearMonth"]):
        raise TypeError("YearMonth must contain calendar dates.")
    months = pd.to_datetime(frame["YearMonth"], format="ISO8601", errors="coerce")
    if months.isna().any() or months.dt.tz is not None or not months.eq(months.dt.normalize()).all() or not months.dt.day.eq(1).all():
        raise ValueError("YearMonth must contain timezone-free month starts.")
    frame["YearMonth"] = months
    if frame.duplicated(["Period", "YearMonth"]).any():
        raise ValueError("Each period/month must appear once.")
    if "IsPartialMonth" in frame:
        if len(frame) and not pd.api.types.is_bool_dtype(frame["IsPartialMonth"]):
            raise TypeError("IsPartialMonth must have Boolean dtype.")
    else:
        frame["IsPartialMonth"] = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    return frame


def _seasonal_frame(table: Any, metric: str, include_partial: bool) -> pd.DataFrame:
    """Validate seasonal identity and retain excluded cells for honest chart axes.

    Args:
        table: Seasonal summary, one row per period and season instance.
        metric: Requested count or standardized rate.
        include_partial: Whether known partial seasons are eligible.

    Returns:
        Independent sorted frame with SeasonYear and Eligible columns.

    Raises:
        TypeError: Unsupported input, flag, count, or option types.
        ValueError: Missing columns, invalid seasonal dates, duplicate keys, or
            invalid nonnegative counts/exposure.
    """
    if not isinstance(table, pd.DataFrame) or type(include_partial) is not bool:
        raise TypeError("Expected a DataFrame and Boolean include_partial.")
    if metric not in {"PermitCount", "DP_Rate30"}:
        raise ValueError("metric must be PermitCount or DP_Rate30.")
    required = {"Period", "Season", "SeasonStartDate", "PermitCount", "IsCompleteSeason"}
    if metric == "DP_Rate30":
        required.add("ExposureDays")
    if not table.columns.is_unique or not required.issubset(table.columns):
        raise ValueError("Seasonal heatmap requires unique seasonal-summary columns.")
    frame = table.copy(deep=True)
    if any(not isinstance(p, str) or not p.strip() for p in frame["Period"]):
        raise ValueError("Periods must be nonblank strings.")
    if len(frame) and not pd.api.types.is_bool_dtype(frame["IsCompleteSeason"]):
        raise TypeError("IsCompleteSeason must have Boolean dtype.")
    frame["IsCompleteSeason"] = frame["IsCompleteSeason"].astype("boolean")
    for field in ("PermitCount", "ExposureDays"):
        if field not in frame:
            continue
        if len(frame) and not (field == "ExposureDays" and frame[field].isna().all()) and (not pd.api.types.is_numeric_dtype(frame[field])
                           or pd.api.types.is_bool_dtype(frame[field])):
            raise TypeError(f"{field} must be numeric (use nullable numeric dtype for missing values).")
        values = frame[field].to_numpy(dtype=float, na_value=np.nan)
        known = values[~np.isnan(values)]
        if (field == "PermitCount" and np.isnan(values).any()) or not np.isfinite(known).all() or (known < 0).any() or (known % 1 != 0).any():
            raise ValueError(f"{field} must contain nonnegative integer values.")
    if any(not isinstance(v, (str, date)) for v in frame["SeasonStartDate"]):
        raise TypeError("Season starts must be calendar dates.")
    starts = pd.to_datetime(frame["SeasonStartDate"], format="ISO8601", errors="coerce")
    if starts.isna().any() or starts.dt.tz is not None or not starts.eq(starts.dt.normalize()).all():
        raise ValueError("Season starts must be timezone-free dates.")
    definitions = {"Winter": 12, "Spring": 3, "Summer": 6, "Fall": 9}
    for season, start in zip(frame["Season"], starts):
        if not isinstance(season, str) or season not in definitions or start.month != definitions[season] or start.day != 1:
            raise ValueError("Season names and starts must match meteorological seasons.")
    frame["SeasonStartDate"] = starts
    if frame.duplicated(["Period", "SeasonStartDate"]).any():
        raise ValueError("Each period/season instance must appear once.")
    frame["SeasonYear"] = starts.dt.year + starts.dt.month.eq(12).astype(int)
    complete = frame["IsCompleteSeason"]
    frame["Eligible"] = complete.notna() if include_partial else complete.fillna(False)
    return frame.sort_values(["SeasonStartDate", "Period"], kind="stable")


def _season_value(group: pd.DataFrame, metric: str) -> float:
    """Calculate one pooled cell without averaging rates or hiding missing exposure.

    Args:
        group: Eligible seasonal records for one chart cell.
        metric: Count or standardized 30-day rate.

    Returns:
        Sum of counts or pooled rate, NaN for unusable rate exposure.
    """
    count = float(group["PermitCount"].sum())
    if metric == "PermitCount":
        return count
    exposure = group["ExposureDays"]
    if exposure.isna().any() or exposure.le(0).any():
        return float("nan")
    return count / float(exposure.sum()) * 30


def _season_note(include_partial: bool) -> str:
    """Return the displayed cohort rule for seasonal heatmaps.

    Args:
        include_partial: Whether known partial seasons enter cells.

    Returns:
        Cohort and missing-cell explanation for the figure footer.
    """
    cohort = "Complete and known partial seasons (*); unknown completeness excluded." if include_partial else "Complete seasons only; partial and unknown completeness excluded."
    return cohort + "\n– No eligible data or unavailable exposure. Winter year = January/February year."


def _heatmap_figure(
    panels: list, style: dict[str, Any], title: str, value_label: str,
    xlabel: str, ylabel: str, decimals: int, note: str,
) -> Figure:
    """Render labelled matrices with a shared scale and explicit missing cells.

    Args:
        panels: Tuples of title, row labels, column labels, values, and cell markers.
        style: Local Matplotlib rc settings.
        title: Figure heading.
        value_label: Colorbar measurement and units.
        xlabel: Column-axis description.
        ylabel: Row-axis description.
        decimals: Decimal places in numeric annotations.
        note: Visible coverage and interpretation guidance.

    Returns:
        Headless Figure ready for Jupyter display or explicit saving.
    """
    height = sum(len(panel[1]) * .38 + 1.0 for panel in panels) + 1.4
    width = max((len(panel[2]) for panel in panels), default=1)
    defaults = {"figure.figsize": (max(8, width * 1.1 + 3), max(3.5, height)),
                "font.size": 10, **style}
    with mpl.rc_context(defaults):
        figure = Figure(layout="constrained")
        FigureCanvasAgg(figure)
        if not panels:
            ax = figure.subplots()
            ax.text(.5, .5, "No monthly permit data" if ylabel == "Month" else "No seasonal permit data",
                    transform=ax.transAxes, ha="center")
            ax.set_axis_off()
            return figure
        axes = figure.subplots(len(panels), 1, squeeze=False,
                               gridspec_kw={"height_ratios": [len(p[1]) for p in panels]}).ravel()
        finite = [p[3][np.isfinite(p[3])] for p in panels]
        maximum = max([1] + [float(v.max()) for v in finite if v.size])
        norm = mpl.colors.Normalize(vmin=0, vmax=maximum)
        cmap = mpl.colormaps["viridis"].with_extremes(bad="#E5E7EB")
        for ax, (name, rows, columns, values, markers) in zip(axes, panels):
            artist = ax.imshow(np.ma.masked_invalid(values), aspect="auto", cmap=cmap, norm=norm)
            for y, x in np.ndindex(values.shape):
                value = values[y, x]
                label = "–" if np.isnan(value) else f"{value:,.{decimals}f}{markers.get((y, x), '')}"
                color = "#555555" if np.isnan(value) else "black" if norm(value) > .55 else "white"
                ax.text(x, y, label, ha="center", va="center", color=color, fontsize=9)
            ax.set_xticks(range(len(columns)), columns)
            ax.set_yticks(range(len(rows)), rows)
            ax.set(title=name, xlabel=xlabel, ylabel=ylabel)
            ax.set_xticks(np.arange(-.5, len(columns), 1), minor=True)
            ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
            ax.grid(which="minor", color="white", linewidth=1)
            ax.tick_params(which="minor", bottom=False, left=False)
        figure.colorbar(artist, ax=list(axes), label=value_label, shrink=.85)
        figure.suptitle(title)
        figure.supxlabel(note, fontsize=9)
        return figure
