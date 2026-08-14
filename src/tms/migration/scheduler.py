from ..core.clock import Clock, RealClock
from ..core.constants import MIN_INVITE_INTERVAL_SECONDS, MAX_INVITE_INTERVAL_SECONDS, DEFAULT_INVITE_INTERVAL_SECONDS


class InviteScheduler:
    def __init__(self, interval_seconds: float=DEFAULT_INVITE_INTERVAL_SECONDS, clock: Clock | None=None) -> None:
        if not MIN_INVITE_INTERVAL_SECONDS <= interval_seconds <= MAX_INVITE_INTERVAL_SECONDS:
            raise ValueError("Invite interval must be between 3 and 8 seconds")
        self.interval=interval_seconds; self.clock=clock or RealClock(); self._last_attempt:float|None=None; self._server_wait_until:float=0.0

    def apply_server_wait(self, seconds: float) -> None:
        self._server_wait_until=max(self._server_wait_until,self.clock.monotonic()+max(0,seconds))

    async def wait_before_next(self) -> None:
        local_next=(self._last_attempt+self.interval) if self._last_attempt is not None else self.clock.monotonic()
        next_allowed=max(local_next,self._server_wait_until)
        await self.clock.sleep(max(0.0,next_allowed-self.clock.monotonic()))

    def mark_attempt(self) -> None: self._last_attempt=self.clock.monotonic()
