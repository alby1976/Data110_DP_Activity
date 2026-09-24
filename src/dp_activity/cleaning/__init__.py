"""Development-permit data-cleaning components.

This package contains deterministic transformations that standardize raw City permit
records before classification.

Design Pattern:
    None

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Apply these components to a raw snapshot before classification and feature
    derivation.
"""

from .permit_cleaner import PermitCleaner

__all__ = [
    "PermitCleaner",
]
