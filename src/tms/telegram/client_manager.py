import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from ..runtime.network_runtime import NetworkRuntime


@dataclass(slots=True)
class ClientSlot:
    client: Any
    last_used: float


class ClientManager:
    def __init__(self, network: NetworkRuntime, api_id: int, api_hash: str, idle_timeout: float = 300.0) -> None:
        self.network=network
        self.api_id=api_id
        self.api_hash=api_hash
        self.idle_timeout=idle_timeout
        self._clients: dict[int, ClientSlot] = {}

    async def get(self, account_id: int, session_path: str) -> Any:
        self.network.assert_network_thread()
        loop=asyncio.get_running_loop()
        if account_id in self._clients:
            slot=self._clients[account_id]
            slot.last_used=loop.time()
            return slot.client
        from telethon import TelegramClient
        client=TelegramClient(str(Path(session_path)), self.api_id, self.api_hash)
        await client.connect()
        self._clients[account_id]=ClientSlot(client, loop.time())
        return client

    async def disconnect_idle(self) -> None:
        self.network.assert_network_thread()
        now=asyncio.get_running_loop().time()
        stale=[k for k,v in self._clients.items() if now-v.last_used >= self.idle_timeout]
        for account_id in stale:
            slot=self._clients.pop(account_id)
            await slot.client.disconnect()

    async def close_all(self) -> None:
        self.network.assert_network_thread()
        for slot in list(self._clients.values()):
            await slot.client.disconnect()
        self._clients.clear()
