"""Python chart creation.

This package contains centralized chart construction and export utilities for finalized
analysis tables.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Build charts from finalized analysis tables and save the resulting figures
    explicitly.
"""

from .chart_factory import ChartFactory

__all__ = [
    "ChartFactory",
]
