from __future__ import annotations


class JoinLeaveService:
    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def join(self, account_id: int, reference: str):
        return await self.gateway.join_group(account_id, reference)

    async def leave(self, account_id: int, group) -> None:
        await self.gateway.leave_group(account_id, group)
