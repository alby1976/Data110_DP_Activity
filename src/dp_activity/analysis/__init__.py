"""Permit-analysis strategies.

This package contains interchangeable analyses that convert classified permit records
into tidy result tables.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Instantiate the analysis and supply it to the pipeline through the shared Analysis
    contract.
"""

from .base import Analysis
from .geography_analysis import GeographyAnalysis
from .processing_analysis import ProcessingAnalysis
from .rezoning_analysis import RezoningAnalysis
from .seasonal_analysis import SeasonalAnalysis
from .sensitivity_analysis import SensitivityAnalysis
from .type_analysis import TypeAnalysis
from .volume_analysis import VolumeAnalysis

__all__ = [
    "Analysis",
    "GeographyAnalysis",
    "ProcessingAnalysis",
    "RezoningAnalysis",
    "SeasonalAnalysis",
    "SensitivityAnalysis",
    "TypeAnalysis",
    "VolumeAnalysis",
]
