from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import GroupContext


def normalize_group_reference(reference: str) -> str:
    """Normalize public Telegram group references without resolving them on the network."""
    value = reference.strip()
    if not value:
        return ""
    if value.startswith("@"):
        return value[1:]
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if parsed.netloc.lower() in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}:
        path = parsed.path.strip("/")
        if path and not path.startswith("+") and not path.startswith("joinchat/"):
            return path.split("/", 1)[0]
    return value


def invite_hash(reference: str) -> str | None:
    ref = reference.strip()
    match = re.search(
        r"(?:t\.me/|telegram\.me/)(?:joinchat/|\+)([A-Za-z0-9_-]+)",
        ref,
    )
    return match.group(1) if match else None


class GroupService:
    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def resolve(self, account_id: int, reference: str) -> GroupContext:
        return await self.gateway.resolve_group(account_id, reference)
