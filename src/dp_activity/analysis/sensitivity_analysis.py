"""Sensitivity checks for defensible alternative definitions.

Design pattern:
    Strategy with injected functions.
Why:
    Named scenario callables supply alternative algorithms at runtime, allowing sensitivity definitions to change without modifying the orchestrator.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import Analysis


class SensitivityAnalysis(Analysis):
    name = "sensitivity"

    def __init__(self, scenarios: dict[str, Callable[[Any], Any]]) -> None:
        self.scenarios = scenarios

    def run(self, permits: Any) -> dict[str, Any]:
        """Recalculate headline metrics under named alternative scenarios."""
        # TODO: Define the configured primary result as the reference scenario.
        # TODO: Run broader/narrower residential or rezoning classifications.
        # TODO: Test alternate relevant dates without rewriting the primary classification.
        # TODO: Test complete-period/complete-season restrictions.
        # TODO: Compare direction and magnitude with the reference result.
        # TODO: Retain scenarios that weaken the headline finding.
        raise NotImplementedError
