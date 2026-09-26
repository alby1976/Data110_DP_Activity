"""Sensitivity checks for defensible alternative definitions.

This module evaluates named alternative definitions and reports how analytical
conclusions change under each scenario.

Design Pattern:
    Strategy with injected functions.

Pattern Rationale:
    Named scenario callables supply alternative algorithms at runtime, allowing
    sensitivity definitions to change without modifying the orchestrator.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import math
from numbers import Real
from typing import Any

import pandas as pd

from .base import Analysis


class SensitivityAnalysis(Analysis):
    """Evaluate named alternative analytical scenarios.

    This concrete Strategy accepts scenario callables through dependency injection so
    alternative definitions can be added without modifying the orchestrator.

    Attributes:
        scenarios: Scenario names mapped to callables that evaluate permit data.
        reference: Name of the primary scenario used for comparisons.
    """

    name = "sensitivity"

    def __init__(
        self, scenarios: dict[str, Callable[[Any], Any]], *, reference: str = "reference",
    ) -> None:
        """Configure named evaluations of the same scalar headline metric.

        Args:
            scenarios: Ordered names mapped to callables returning finite real
                numbers or missing results. Empty means no checks configured.
            reference: Primary scenario name, required in nonempty scenarios.

        Raises:
            TypeError: Scenarios are not a dictionary of named callables.
            ValueError: Names are blank or the reference is absent.
        """
        if not isinstance(scenarios, dict):
            raise TypeError("scenarios must be a dictionary of named callables.")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("reference must be a nonblank scenario name.")
        for name, scenario in scenarios.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Scenario names must be nonblank strings.")
            if not callable(scenario):
                raise TypeError(f"Scenario {name!r} must be callable.")
        if scenarios and reference not in scenarios:
            raise ValueError("The reference scenario must be configured.")
        self.scenarios = dict(scenarios)
        self.reference = reference

    def run(self, permits: Any) -> dict[str, Any]:
        """Recalculate headline metrics under named alternative scenarios.

        Args:
            permits: DataFrame of permit records. Each callable receives an
                independent copy, including recursively copied object cells.

        Returns:
            ``sensitivity_summary`` has one row per configured scenario in
            insertion order, including unfavorable or missing results. Result
            is the supplied scalar metric. ReferenceResult is the primary
            value; AbsoluteChange is Result minus ReferenceResult (signed).
            PercentChange divides that change by abs(ReferenceResult) and
            multiplies by 100; it is null for zero or missing references.
            ChangeDirection is increased, decreased, unchanged, or unknown.
            Empty configuration returns an empty table with the same columns;
            it is not evidence that any sensitivity checks were performed.

        Raises:
            TypeError: Input is not a DataFrame or a result is not a real scalar.
            ValueError: A scenario fails or returns an infinite result.

        Note:
            Callers define comparable metrics, alternative populations, and
            exposure denominators. This runner does not invent classification
            rules, reassign dates, or implement minimum-follow-up eligibility.
            Scenario errors stop execution with the name and original cause;
            unsuccessful scenarios are never silently omitted.
        """
        if not isinstance(permits, pd.DataFrame):
            raise TypeError("permits must be a pandas DataFrame.")
        values = {}
        for name, scenario in self.scenarios.items():
            frame = permits.copy(deep=True)
            for position, dtype in enumerate(frame.dtypes):
                if pd.api.types.is_object_dtype(dtype):
                    frame.isetitem(position, frame.iloc[:, position].map(deepcopy))
            try:
                result = scenario(frame)
            except Exception as exc:
                raise ValueError(f"Sensitivity scenario {name!r} failed: {exc}") from exc
            if result is None or result is pd.NA:
                values[name] = None
            elif isinstance(result, bool) or not isinstance(result, Real):
                raise TypeError(f"Scenario {name!r} must return a real scalar or missing value.")
            elif math.isnan(result):
                values[name] = None
            elif not math.isfinite(result):
                raise ValueError(f"Scenario {name!r} returned an infinite result.")
            else:
                values[name] = result
        baseline = values.get(self.reference)
        rows = []
        for name, value in values.items():
            change = value - baseline if value is not None and baseline is not None else None
            direction = "unknown" if change is None else (
                "increased" if change > 0 else "decreased" if change < 0 else "unchanged"
            )
            rows.append({
                "Scenario": name, "Result": value, "ReferenceScenario": self.reference,
                "IsReference": name == self.reference, "ReferenceResult": baseline,
                "AbsoluteChange": change,
                "PercentChange": change / abs(baseline) * 100
                if change is not None and baseline != 0 else None,
                "ChangeDirection": direction,
            })
        columns = ["Scenario", "Result", "ReferenceScenario", "IsReference", "ReferenceResult",
                   "AbsoluteChange", "PercentChange", "ChangeDirection"]
        return {"sensitivity_summary": pd.DataFrame(rows, columns=columns).convert_dtypes()}
