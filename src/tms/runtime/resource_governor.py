import asyncio
from collections import defaultdict


class ResourceGovernor:
    """One mutating Telegram operation per account; limited concurrent reads."""
    def __init__(self, max_reads: int = 3) -> None:
        self._mutation_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.read_semaphore = asyncio.Semaphore(max_reads)
        self.performance_mode = False

    def mutation_lock(self, account_id: int) -> asyncio.Lock:
        return self._mutation_locks[account_id]

    def enable_performance_mode(self) -> None:
        self.performance_mode = True

    def disable_performance_mode(self) -> None:
        self.performance_mode = False
