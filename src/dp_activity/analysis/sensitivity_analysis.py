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
from typing import Any

from .base import Analysis


class SensitivityAnalysis(Analysis):
    """Evaluate named alternative analytical scenarios.

    This concrete Strategy accepts scenario callables through dependency injection so
    alternative definitions can be added without modifying the orchestrator.

    Attributes:
        scenarios: Scenario names mapped to callables that evaluate permit data.
    """

    name = "sensitivity"

    def __init__(self, scenarios: dict[str, Callable[[Any], Any]]) -> None:
        self.scenarios = scenarios

    def run(self, permits: Any) -> dict[str, Any]:
        """Recalculate headline metrics under named alternative scenarios.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Scenario comparison tables keyed by stable output names.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        # TODO: Define the configured primary result as the reference scenario.
        # TODO: Run broader/narrower residential or rezoning classifications.
        # TODO: Test alternate relevant dates without rewriting the primary classification.
        # TODO: Test complete-period/complete-season restrictions.
        # TODO: Compare direction and magnitude with the reference result.
        # TODO: Retain scenarios that weaken the headline finding.
        raise NotImplementedError
