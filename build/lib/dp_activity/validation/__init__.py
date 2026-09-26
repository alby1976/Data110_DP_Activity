"""Permit-data validation components.

This package contains schema, data-quality, and classification-validation services.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Run these components at the appropriate pipeline boundary and retain their
    structured findings.
"""

from .classification_validator import ClassificationValidator
from .data_quality_validator import DataQualityValidator, QualityCheckResult
from .schema_validator import SchemaIssue, SchemaValidator

__all__ = [
    "ClassificationValidator",
    "DataQualityValidator",
    "QualityCheckResult",
    "SchemaIssue",
    "SchemaValidator",
]
