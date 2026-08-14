from collections.abc import AsyncIterator
from ..groups.models import GroupContext
from ..members.models import Member

class FakeTelegramGateway:
    def __init__(self,pages=None,invite_effects=None):
        self.pages=pages or [];self.invite_effects=list(invite_effects or []);self.invites=[];self.resolve_calls=0
    async def resolve_group(self,account_id:int,reference:str)->GroupContext:
        self.resolve_calls+=1;return GroupContext(100,10,reference,reference,'Channel',True,True,True,True,True)
    async def get_joined_groups(self,account_id:int):return []
    async def iter_participant_pages(self,account_id:int,group:GroupContext,offset:int,limit:int)->AsyncIterator[list[Member]]:
        for page in self.pages: yield page
    async def invite_user(self,account_id:int,target:GroupContext,member:Member)->None:
        self.invites.append(member.telegram_user_id)
        if self.invite_effects:
            effect=self.invite_effects.pop(0)
            if isinstance(effect,Exception):raise effect
    async def join_group(self,account_id:int,reference:str):return await self.resolve_group(account_id,reference)
    async def leave_group(self,account_id:int,group:GroupContext)->None:return None
