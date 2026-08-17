from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def intersection(a: Iterable[T], b: Iterable[T]) -> set[T]:
    """Return members present in both collections."""
    return set(a) & set(b)
