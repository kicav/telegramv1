from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def union(a: Iterable[T], b: Iterable[T]) -> set[T]:
    """Return the mathematical union of two member-id collections."""
    return set(a) | set(b)
