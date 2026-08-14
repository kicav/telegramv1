from collections.abc import Callable
from typing import Any


class CommandBus:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        self._handlers[name] = handler

    def dispatch(self, name: str, **payload: Any) -> Any:
        if name not in self._handlers:
            raise KeyError(f"No command handler for {name}")
        return self._handlers[name](**payload)
