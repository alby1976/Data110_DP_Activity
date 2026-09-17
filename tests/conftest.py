"""Shared pytest helpers for implementation-driven tests."""

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
    """Run behavior or mark it unfinished only when the scaffold says so."""
    try:
        return call(*args, **kwargs)
    except NotImplementedError:
        pytest.xfail("Target behavior has not been implemented yet")

