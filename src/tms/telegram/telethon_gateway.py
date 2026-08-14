from collections.abc import AsyncIterator
from datetime import datetime, timezone
from telethon.tl import functions, types
from .client_manager import ClientManager
from .peer_cache import PeerCache, CachedPeer
from .error_mapper import ErrorMapper
from ..accounts.repository import AccountRepository
from ..groups.models import GroupContext
from ..members.models import Member
from ..members.normalizer import normalize_member


class TelethonGateway:
    def __init__(self, clients: ClientManager, accounts: AccountRepository, peers: PeerCache) -> None:
        self.clients=clients
        self.accounts=accounts
        self.peers=peers
        self.errors=ErrorMapper()

    def _session(self, account_id: int) -> str:
        for account in self.accounts.list_all():
            if account.id == account_id:
                return account.session_path
        raise KeyError(account_id)

    async def _client(self, account_id: int):
        return await self.clients.get(account_id, self._session(account_id))

    async def resolve_group(self, account_id: int, reference: str) -> GroupContext:
        client=await self._client(account_id)
        entity=await client.get_entity(reference)
        peer_id=int(entity.id)
        access_hash=getattr(entity, "access_hash", None)
        self.peers.put(CachedPeer(account_id,peer_id,type(entity).__name__,access_hash,getattr(entity,'username',None),getattr(entity,'title',None)))
        admin_rights=getattr(entity,'admin_rights',None)
        return GroupContext(
            telegram_id=peer_id, access_hash=access_hash,
            title=getattr(entity,'title',getattr(entity,'first_name',str(peer_id))),
            username=getattr(entity,'username',None), type=type(entity).__name__,
            is_member=not bool(getattr(entity,'left',False)),
            is_admin=admin_rights is not None or bool(getattr(entity,'creator',False)),
            can_read=True,
            can_invite=bool(getattr(entity,'creator',False) or getattr(admin_rights,'invite_users',False)),
            can_send=True,
            resolved_at=datetime.now(timezone.utc).isoformat(),
        )

    async def get_joined_groups(self, account_id: int) -> list[GroupContext]:
        client=await self._client(account_id)
        out=[]
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                e=dialog.entity
                out.append(GroupContext(int(e.id),getattr(e,'access_hash',None),dialog.name,getattr(e,'username',None),type(e).__name__,True))
        return out

    async def iter_participant_pages(self, account_id: int, group: GroupContext, offset: int, limit: int) -> AsyncIterator[list[Member]]:
        client=await self._client(account_id)
        entity=await client.get_input_entity(group.telegram_id)
        current=offset
        while True:
            result=await client(functions.channels.GetParticipantsRequest(
                channel=entity, filter=types.ChannelParticipantsSearch(''), offset=current,
                limit=limit, hash=0,
            ))
            users=list(getattr(result,'users',[]))
            if not users:
                return
            members=[]
            for raw in users:
                member=normalize_member(raw)
                members.append(member)
                if member.telegram_user_id is not None:
                    self.peers.put(CachedPeer(account_id,member.telegram_user_id,'User',member.access_hash,member.username,None))
            yield members
            current += len(users)
            if len(users) < limit:
                return

    async def invite_user(self, account_id: int, target: GroupContext, member: Member) -> None:
        client=await self._client(account_id)
        target_entity=await client.get_input_entity(target.telegram_id)
        if member.telegram_user_id is None:
            raise ValueError("Member has no Telegram user id")
        cached=self.peers.get(account_id,member.telegram_user_id)
        if cached is None or cached.access_hash is None:
            raise ValueError("Missing cached access hash for this account")
        input_user=types.InputUser(member.telegram_user_id,cached.access_hash)
        await client(functions.channels.InviteToChannelRequest(target_entity,[input_user]))

    async def join_group(self, account_id: int, reference: str) -> GroupContext:
        client=await self._client(account_id)
        if reference.startswith('+') or 'joinchat/' in reference:
            token=reference.rsplit('/',1)[-1].lstrip('+')
            await client(functions.messages.ImportChatInviteRequest(token))
        else:
            entity=await client.get_entity(reference)
            await client(functions.channels.JoinChannelRequest(entity))
        return await self.resolve_group(account_id,reference)

    async def leave_group(self, account_id: int, group: GroupContext) -> None:
        client=await self._client(account_id)
        entity=await client.get_input_entity(group.telegram_id)
        await client(functions.channels.LeaveChannelRequest(entity))
