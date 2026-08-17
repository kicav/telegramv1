from __future__ import annotations


class TelegramGroupService:
    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def joined_groups(self, account_id: int):
        return await self.gateway.get_joined_groups(account_id)
