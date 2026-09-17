"""Shared contract for analysis components.

This module defines the contract shared by every analysis that produces named, tidy
output tables.

Design Pattern:
    Strategy.

Pattern Rationale:
    It defines the interchangeable analysis contract; the pipeline can run any analysis
    implementation through the same run() interface.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Analysis(ABC):
    """Define the interchangeable analysis contract.

    This abstract class is the Strategy interface used by the pipeline. Each concrete
    analysis converts classified permit-level data into named tidy result tables.

    Attributes:
        name: Stable identifier used to register and collect analysis outputs.
    """

    name: str

    @abstractmethod
    def run(self, permits: Any) -> dict[str, Any]:
        """Return tables keyed by stable output names.

        Args:
            permits: DataFrame-like table of permit records.

        Returns:
            Stable output names mapped to tidy result tables.

        Raises:
            NotImplementedError: The scaffolded behavior has not yet been implemented.
        """
        raise NotImplementedError
