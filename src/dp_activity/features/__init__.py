"""Derived analytical features.

This package contains deterministic transformations for policy periods, processing
durations, and meteorological seasons.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Apply these transformations to cleaned permit records before running dependent
    analyses.
"""

from .period_features import add_period_features
from .processing_features import add_processing_features
from .season_features import add_season_features

__all__ = [
    "add_period_features",
    "add_processing_features",
    "add_season_features",
]
