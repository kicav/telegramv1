from __future__ import annotations
import re
from .models import GroupContext

def invite_hash(reference:str)->str|None:
    ref=reference.strip();m=re.search(r'(?:t\.me/|telegram\.me/)(?:joinchat/|\+)([A-Za-z0-9_-]+)',ref);return m.group(1) if m else None
class GroupService:
    def __init__(self,gateway)->None:self.gateway=gateway
    async def resolve(self,account_id:int,reference:str)->GroupContext:return await self.gateway.resolve_group(account_id,reference)
