from __future__ import annotations
from .enums import InviteResultCode

class DomainError(Exception):
    def __init__(self, code: InviteResultCode, message: str = "", wait_seconds: int | None = None) -> None:
        super().__init__(message or str(code))
        self.code = code
        self.wait_seconds = wait_seconds
