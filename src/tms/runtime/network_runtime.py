import asyncio
from concurrent.futures import Future
import threading
from collections.abc import Coroutine
from typing import Any


class NetworkRuntime:
    """Single dedicated asyncio loop for every Telegram client and RPC."""
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.thread_id: int | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="TMS-TelegramRuntime", daemon=True)
        self.thread.start()
        if not self._ready.wait(5):
            raise RuntimeError("Network runtime failed to start")

    def _run(self) -> None:
        self.thread_id = threading.get_ident()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending:
            task.cancel()
        if pending:
            self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def submit(self, coro: Coroutine[Any, Any, Any]) -> Future[Any]:
        if not self.loop:
            raise RuntimeError("Network runtime is not running")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def assert_network_thread(self) -> None:
        if threading.get_ident() != self.thread_id:
            raise RuntimeError("Telegram operation attempted outside network runtime thread")

    def stop(self) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.join(timeout=5)
