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
