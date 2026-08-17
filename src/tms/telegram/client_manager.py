from __future__ import annotations
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ..runtime.network_runtime import NetworkRuntime

@dataclass(slots=True)
class ClientSlot:
    client:Any; last_used:float

class ClientManager:
    """Owns Telethon clients on the dedicated network loop; application owns RPC retry/FloodWait policy."""
    def __init__(self,network:NetworkRuntime,api_id:int|None,api_hash:str|None,idle_timeout:float=300.0)->None:
        self.network=network;self.api_id=api_id;self.api_hash=api_hash;self.idle_timeout=max(30.0,idle_timeout);self._clients={};self._reaper_task=None
    def update_credentials(self,api_id:int,api_hash:str)->None:
        if self._clients:raise RuntimeError('Disconnect active Telegram clients before changing API credentials')
        self.api_id=api_id;self.api_hash=api_hash
    def _require_credentials(self)->tuple[int,str]:
        if self.api_id is None or not self.api_hash:raise RuntimeError('Telegram API credentials are not configured. Set API ID/API Hash in Accounts.')
        return self.api_id,self.api_hash
    async def get(self,account_id:int,session_path:str)->Any:
        self.network.assert_network_thread();loop=asyncio.get_running_loop()
        if self._reaper_task is None or self._reaper_task.done():self._reaper_task=loop.create_task(self._idle_reaper(),name='TMS-TelegramIdleReaper')
        if account_id in self._clients:
            slot=self._clients[account_id];slot.last_used=loop.time()
            if not slot.client.is_connected():await slot.client.connect()
            return slot.client
        api_id,api_hash=self._require_credentials();from telethon import TelegramClient
        Path(session_path).parent.mkdir(parents=True,exist_ok=True)
        client=TelegramClient(str(Path(session_path)),api_id,api_hash,request_retries=0,flood_sleep_threshold=0,connection_retries=5,auto_reconnect=True,raise_last_call_error=True)
        await client.connect();self._clients[account_id]=ClientSlot(client,loop.time());return client
    async def is_authorized(self,account_id:int,session_path:str)->bool:return bool(await (await self.get(account_id,session_path)).is_user_authorized())
    async def disconnect(self,account_id:int)->None:
        self.network.assert_network_thread();slot=self._clients.pop(account_id,None)
        if slot is not None:await slot.client.disconnect()
    async def disconnect_idle(self)->None:
        self.network.assert_network_thread();now=asyncio.get_running_loop().time();stale=[i for i,s in self._clients.items() if now-s.last_used>=self.idle_timeout]
        for i in stale:await self.disconnect(i)
    async def _idle_reaper(self)->None:
        try:
            while True:await asyncio.sleep(min(60.0,max(15.0,self.idle_timeout/2)));await self.disconnect_idle()
        except asyncio.CancelledError:raise
    async def close_all(self)->None:
        self.network.assert_network_thread();task=self._reaper_task;self._reaper_task=None
        if task is not None and task is not asyncio.current_task():task.cancel();await asyncio.gather(task,return_exceptions=True)
        for i in list(self._clients):await self.disconnect(i)
