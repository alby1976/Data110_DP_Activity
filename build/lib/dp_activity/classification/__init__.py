"""Permit-classification components.

This package contains rule definitions, rule loading, and ordered permit-classification
services.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Import and use these components during the permit-classification stage.
"""

from .classifier import PermitClassifier
from .rule import ClassificationRule, InvalidRuleError, MatchType
from .rule_loader import RuleLoader

__all__ = [
    "ClassificationRule",
    "InvalidRuleError",
    "MatchType",
    "PermitClassifier",
    "RuleLoader",
]
