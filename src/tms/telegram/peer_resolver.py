from __future__ import annotations

from ..groups.service import normalize_group_reference


class PeerResolver:
    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def resolve_group(self, account_id: int, reference: str):
        return await self.gateway.resolve_group(
            account_id, normalize_group_reference(reference)
        )
