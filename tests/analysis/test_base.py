"""Tests for base.

This module verifies the documented contracts and edge cases of the base component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

import inspect

from dp_activity.analysis.base import Analysis


def test_analysis_is_an_abstract_contract() -> None:
    """Verify that analysis is an abstract contract."""
    assert inspect.isabstract(Analysis)
    assert "run" in Analysis.__abstractmethods__
