"""Shared contract for analysis components."""

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

