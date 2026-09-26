"""Pipeline orchestration.

This package contains orchestration components for assembling and running the end-to-end
workflow.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Construct the pipeline with concrete collaborators and run it for one immutable
    snapshot.
"""

from .analysis_pipeline import AnalysisPipeline, PipelineResult

__all__ = [
    "AnalysisPipeline",
    "PipelineResult",
]
