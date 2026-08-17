from __future__ import annotations
from .telethon_gateway import TelethonGateway

class MemberActionGateway(TelethonGateway):
    """Adds REMOVE to the same cached-entity mutation lane used by INVITE."""
    async def remove_user(self,account_id:int,target,member)->None:
        if member.telegram_user_id is None or member.access_hash is None:raise ValueError('Missing cached candidate identity')
        client=await self._client(account_id);from telethon.tl import functions,types
        input_user=types.InputUser(member.telegram_user_id,member.access_hash)
        if target.type.lower()=='chat':
            await client(functions.messages.DeleteChatUserRequest(chat_id=target.telegram_id,user_id=input_user,revoke_history=False));return
        await client(functions.channels.EditBannedRequest(channel=self._input_channel(target),participant=input_user,banned_rights=types.ChatBannedRights(until_date=None,view_messages=True)))
