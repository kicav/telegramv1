from datetime import datetime, timedelta, timezone
from ..core.constants import TRANSIENT_RETRY_DELAYS_SECONDS
from ..core.enums import AccountState, JobState, MigrationItemState, InviteResultCode
from ..core.errors import DomainError
from ..core.events import DomainEvent
from ..telegram.error_mapper import ErrorMapper
from .candidate_buffer import CandidateBuffer
from .result_classifier import ResultClassifier


class MigrationExecutor:
    """Hot path: RAM candidate -> cached InputUser -> one invite RPC -> classify -> buffered state -> scheduler."""
    def __init__(self,gateway,jobs,accounts,governor,events,scheduler) -> None:
        self.gateway=gateway; self.jobs=jobs; self.accounts=accounts; self.governor=governor; self.events=events; self.scheduler=scheduler
        self.errors=ErrorMapper(); self.classifier=ResultClassifier(); self._stop=False; self._pause=False

    def stop(self) -> None: self._stop=True
    def pause(self) -> None: self._pause=True
    def resume(self) -> None: self._pause=False

    async def run(self, job_id: int, account_id: int, target) -> None:
        self.governor.enable_performance_mode(); self.jobs.set_state(job_id,JobState.RUNNING); self.accounts.set_state(account_id,AccountState.BUSY)
        buffer=CandidateBuffer(self.jobs,job_id)
        try:
            async with self.governor.mutation_lock(account_id):
                while not self._stop:
                    if self._pause:
                        self.jobs.set_state(job_id,JobState.PAUSED); return
                    item=buffer.pop()
                    if item is None: break
                    ordinal,member=item; attempts=0; final_state=None; last_error=None
                    while attempts < 3:
                        await self.scheduler.wait_before_next(); self.scheduler.mark_attempt(); attempts+=1
                        try:
                            await self.gateway.invite_user(account_id,target,member); error=None
                        except Exception as exc:
                            error=self.errors.map(exc)
                        classified=self.classifier.classify(error)
                        if error and error.code == InviteResultCode.RATE_LIMIT:
                            wait=classified.wait_seconds or 0; self.scheduler.apply_server_wait(wait)
                            until=(datetime.now(timezone.utc)+timedelta(seconds=wait)).isoformat()
                            self.accounts.set_state(account_id,AccountState.WAITING_SERVER,str(error)); self.jobs.set_state(job_id,JobState.WAITING_SERVER,until)
                            await self.scheduler.wait_before_next(); self.accounts.set_state(account_id,AccountState.BUSY); self.jobs.set_state(job_id,JobState.RUNNING)
                            continue
                        if classified.pause_job:
                            self.jobs.update_item(job_id,ordinal,MigrationItemState.FAILED,attempts,error.code if error else None,str(error) if error else None)
                            self.accounts.set_state(account_id,AccountState.ERROR,str(error)); self.jobs.set_state(job_id,JobState.PAUSED); return
                        if classified.retry and error and error.code in {InviteResultCode.NETWORK_TRANSIENT,InviteResultCode.SERVER_TRANSIENT}:
                            if attempts < 3:
                                await self.scheduler.clock.sleep(TRANSIENT_RETRY_DELAYS_SECONDS[attempts-1]); continue
                        final_state=classified.state; last_error=error; break
                    if final_state is None: final_state=MigrationItemState.FAILED
                    self.jobs.update_item(job_id,ordinal,final_state,attempts,last_error.code if last_error else None,str(last_error) if last_error else None)
                    self.jobs.checkpoint(job_id,{'last_ordinal':ordinal})
                    self.events.publish(DomainEvent('MigrationItemCompleted',{'job_id':job_id,'ordinal':ordinal,'state':final_state}))
            self.jobs.set_state(job_id,JobState.CANCELLED if self._stop else JobState.COMPLETED)
        finally:
            self.accounts.set_state(account_id,AccountState.READY); self.governor.disable_performance_mode()
