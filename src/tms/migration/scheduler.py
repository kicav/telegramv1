from __future__ import annotations
from ..core.clock import Clock,RealClock
from ..core.constants import DEFAULT_INVITE_INTERVAL_SECONDS,MAX_INVITE_INTERVAL_SECONDS,MIN_INVITE_INTERVAL_SECONDS,RECOVERY_INVITE_INTERVAL_SECONDS

class InviteScheduler:
    """Monotonic attempt scheduler. Telegram/server waits always override local cadence."""
    def __init__(self,interval_seconds:float=DEFAULT_INVITE_INTERVAL_SECONDS,clock:Clock|None=None)->None:
        if not MIN_INVITE_INTERVAL_SECONDS<=interval_seconds<=MAX_INVITE_INTERVAL_SECONDS:raise ValueError('Invite interval must be between 3 and 10 seconds')
        self.interval=float(interval_seconds);self.target_interval=float(interval_seconds);self.clock=clock or RealClock();self._last_attempt=None;self._server_wait_until=0.0;self._recovery_steps=[]
    def apply_server_wait(self,seconds:float)->None:
        self._server_wait_until=max(self._server_wait_until,self.clock.monotonic()+max(0.0,seconds));self._recovery_steps=[RECOVERY_INVITE_INTERVAL_SECONDS,8.0,self.target_interval]
    def server_wait_remaining(self)->float:return max(0.0,self._server_wait_until-self.clock.monotonic())
    def remaining_delay(self)->float:
        now=self.clock.monotonic();local_next=self._last_attempt+self.interval if self._last_attempt is not None else now;return max(0.0,max(local_next,self._server_wait_until)-now)
    async def wait_before_next(self)->None:await self.clock.sleep(self.remaining_delay())
    def mark_attempt(self)->None:self._last_attempt=self.clock.monotonic()
    def mark_stable_candidate(self)->None:
        if self.server_wait_remaining()>0 or not self._recovery_steps:return
        self.interval=float(self._recovery_steps.pop(0))
    def reset_target(self,seconds:float)->None:
        if not MIN_INVITE_INTERVAL_SECONDS<=seconds<=MAX_INVITE_INTERVAL_SECONDS:raise ValueError('Invite interval must be between 3 and 10 seconds')
        self.target_interval=float(seconds)
        if not self._recovery_steps:self.interval=float(seconds)
