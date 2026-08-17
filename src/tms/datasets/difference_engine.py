from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def difference(a: Iterable[T], b: Iterable[T]) -> set[T]:
    """Return members present in A and absent from B."""
    return set(a) - set(b)
