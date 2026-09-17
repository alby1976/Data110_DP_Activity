"""Shared contract for analysis components.

Design pattern:
    Strategy.
Why:
    It defines the interchangeable analysis contract; the pipeline can run any analysis implementation through the same run() interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Analysis(ABC):
    """Transform classified permit-level data into named tidy result tables."""

    name: str

    @abstractmethod
    def run(self, permits: Any) -> dict[str, Any]:
        """Return tables keyed by stable output names."""
        raise NotImplementedError
