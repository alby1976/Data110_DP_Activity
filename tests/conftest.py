"""Shared pytest configuration and implementation-aware helpers.

This module makes the source package importable during tests and records unfinished
scaffold behavior as expected failures.

Design Pattern:
    None

Pattern Rationale:
    The module supports test discovery and fixtures; it does not implement an
    application design pattern.

Typical Usage:
    Pytest imports this module automatically, and tests call implemented() when
    exercising scaffolded behavior.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

T = TypeVar("T")


def implemented(call: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run implemented behavior or mark an unfinished scaffold as expected.

    Args:
        call: Callable containing implemented or scaffolded behavior.
        args: Positional arguments forwarded to the callable.
        kwargs: Keyword arguments forwarded to the callable.

    Returns:
        The value returned by call when its behavior is implemented.

    Note:
        NotImplementedError is converted to pytest.xfail so unfinished scaffolds do
        not appear to pass. Other exceptions propagate normally.
    """
    try:
        return call(*args, **kwargs)
    except NotImplementedError:
        pytest.xfail("Target behavior has not been implemented yet")
