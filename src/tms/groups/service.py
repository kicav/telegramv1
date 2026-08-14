import re
from .models import GroupContext


def normalize_group_reference(value: str) -> str:
    value=value.strip()
    value=re.sub(r"^https?://", "", value, flags=re.I)
    value=re.sub(r"^t\.me/", "", value, flags=re.I)
    if value.startswith("@"):
        value=value[1:]
    return value.strip()


class GroupService:
    def __init__(self, gateway: object) -> None:
        self.gateway=gateway

    async def resolve(self, account_id: int, reference: str) -> GroupContext:
        return await self.gateway.resolve_group(account_id, normalize_group_reference(reference))
