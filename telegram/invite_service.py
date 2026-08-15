from __future__ import annotations


class InviteService:
    """Thin single-candidate invite boundary used by MigrationExecutor."""

    def __init__(self, gateway) -> None:
        self.gateway = gateway

    async def invite(self, account_id: int, target, member) -> None:
        await self.gateway.invite_user(account_id, target, member)
