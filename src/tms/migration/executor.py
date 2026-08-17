from __future__ import annotations
import asyncio
from datetime import datetime,timedelta,timezone
from time import monotonic
from ..core.clock import RealClock
from ..core.constants import MIGRATION_DB_BATCH_SIZE,MIGRATION_DB_MAX_FLUSH_SECONDS,RPC_WATCHDOG_SECONDS,TRANSIENT_RETRY_DELAYS_SECONDS
from ..core.enums import AccountState,InviteResultCode,JobState,MigrationItemState
from ..core.events import DomainEvent
from ..jobs.repository import ItemUpdate
from ..telegram.error_mapper import ErrorMapper
from .candidate_buffer import BufferedCandidate,CandidateBuffer
from .result_classifier import ResultClassifier

class MigrationExecutor:
    """Shared one-candidate mutation executor for INVITE and REMOVE. No resolve/file/large-query work lives here."""
    def __init__(self,gateway,jobs,accounts,governor,events,scheduler,workers,metrics=None,action:str='INVITE')->None:
        self.gateway=gateway;self.jobs=jobs;self.accounts=accounts;self.governor=governor;self.events=events;self.scheduler=scheduler;self.workers=workers;self.metrics=metrics;self.action=action.upper();self.errors=ErrorMapper();self.classifier=ResultClassifier();self._stop_event=None;self._pause_event=None;self._running_job_id=None;self._result_buffer=[];self._last_flush=monotonic();self._flush_task=None
        if self.action not in {'INVITE','REMOVE'}:raise ValueError('Action must be INVITE or REMOVE')
    async def request_stop(self):
        if self._stop_event:self._stop_event.set()
    async def request_pause(self):
        if self._pause_event:self._pause_event.set()
    async def request_resume(self):
        if self._pause_event:self._pause_event.clear()
    @staticmethod
    def _utc_wait_until(seconds:float)->str:return (datetime.now(timezone.utc)+timedelta(seconds=max(0,seconds))).isoformat()
    @staticmethod
    async def _await_write(future):return await asyncio.wrap_future(future)
    async def _set_account(self,account_id,state,error=None):
        await self._await_write(self.accounts.submit_set_state(account_id,state,error));self.events.publish(DomainEvent('AccountStateChanged',{'account_id':account_id,'state':str(state),'error':error}))
    async def _set_job(self,job_id,state,waiting_until=None,checkpoint=None,clear_waiting=False):
        await self._await_write(self.jobs.submit_set_state(job_id,state,waiting_until,checkpoint=checkpoint,clear_waiting=clear_waiting));self.events.publish(DomainEvent('JobStateChanged',{'job_id':job_id,'state':str(state),'waiting_until':waiting_until}))
    def _control(self):
        if self._stop_event and self._stop_event.is_set():return 'stop'
        if self._pause_event and self._pause_event.is_set():return 'pause'
        return None
    async def _sleep(self,seconds):
        if not isinstance(self.scheduler.clock,RealClock):await self.scheduler.clock.sleep(max(0,seconds));return self._control()
        deadline=self.scheduler.clock.monotonic()+max(0,seconds)
        while True:
            c=self._control()
            if c:return c
            left=deadline-self.scheduler.clock.monotonic()
            if left<=0:return None
            await asyncio.sleep(min(.25,left))
    async def _flush(self,job_id,force=False):
        if not self._result_buffer:return
        if not force and len(self._result_buffer)<MIGRATION_DB_BATCH_SIZE and monotonic()-self._last_flush<MIGRATION_DB_MAX_FLUSH_SECONDS:return
        updates=self._result_buffer;self._result_buffer=[];await self._await_write(self.jobs.submit_update_items_batch(job_id,updates,checkpoint={'last_ordinal':updates[-1].ordinal}));self._last_flush=monotonic()
    def _schedule_flush(self,job_id):
        if not isinstance(self.scheduler.clock,RealClock) or (self._flush_task and not self._flush_task.done()):return
        async def delayed():
            try:await asyncio.sleep(MIGRATION_DB_MAX_FLUSH_SECONDS);await self._flush(job_id,True)
            finally:self._flush_task=None
        self._flush_task=asyncio.create_task(delayed())
    async def _handle_control(self,control,job_id,account_id):
        if control=='stop':await self._flush(job_id,True);await self._set_job(job_id,JobState.CANCELLED,clear_waiting=True);await self._set_account(account_id,AccountState.READY);return True
        if control=='pause':await self._flush(job_id,True);await self._set_job(job_id,JobState.PAUSED);await self._set_account(account_id,AccountState.WAITING_SERVER if self.scheduler.server_wait_remaining()>0 else AccountState.READY);return True
        return False
    async def _rpc(self,account_id,target,member):
        coro=self.gateway.invite_user(account_id,target,member) if self.action=='INVITE' else self.gateway.remove_user(account_id,target,member)
        return await asyncio.wait_for(coro,timeout=RPC_WATCHDOG_SECONDS)
    async def _attempt(self,job_id,account_id,target,candidate:BufferedCandidate):
        member=candidate.member;attempts=candidate.persisted_attempts
        if member.telegram_user_id is None or member.access_hash is None:return ItemUpdate(candidate.ordinal,MigrationItemState.FAILED,attempts,str(InviteResultCode.INVALID_USER),'Candidate lacks user id/access hash'),False
        transient=0
        while True:
            control=await self._sleep(self.scheduler.remaining_delay())
            if await self._handle_control(control,job_id,account_id):return None,True
            self.scheduler.mark_attempt();attempts+=1;started=monotonic();error=None
            try:await self._rpc(account_id,target,member)
            except Exception as exc:error=self.errors.map(exc)
            if self.metrics:self.metrics.observe('rpc_latency_ms',(monotonic()-started)*1000)
            result=self.classifier.classify(error)
            if error is None:
                self.scheduler.mark_stable_candidate();return ItemUpdate(candidate.ordinal,MigrationItemState.SUCCESS,attempts),False
            if error.code==InviteResultCode.RATE_LIMIT:
                wait=int(error.wait_seconds or 0);self.scheduler.apply_server_wait(wait);until=self._utc_wait_until(wait);await self._flush(job_id,True);await self._await_write(self.jobs.submit_mark_retry(job_id,candidate.ordinal,attempts,str(error.code),str(error),next_retry_at=until));await self._set_account(account_id,AccountState.WAITING_SERVER,str(error));await self._set_job(job_id,JobState.WAITING_SERVER,until,{'last_ordinal':candidate.ordinal-1});await self._await_write(self.jobs.submit_event(job_id,'WARN','FLOOD_WAIT',f'WAIT {wait}s; retry same candidate',member_id=member.telegram_user_id,critical=True));control=await self._sleep(self.scheduler.remaining_delay())
                if await self._handle_control(control,job_id,account_id):return None,True
                await self._set_job(job_id,JobState.RUNNING,clear_waiting=True);await self._set_account(account_id,AccountState.BUSY);continue
            if error.code==InviteResultCode.RATE_LIMIT_INDEFINITE:
                await self._flush(job_id,True);await self._await_write(self.jobs.submit_mark_retry(job_id,candidate.ordinal,attempts,str(error.code),str(error)));await self._set_job(job_id,JobState.RATE_LIMITED,checkpoint={'last_ordinal':candidate.ordinal-1});await self._set_account(account_id,AccountState.ERROR,'Telegram rate limit has no resume time');await self._await_write(self.jobs.submit_event(job_id,'WARN','RATE_LIMIT_INDEFINITE','Telegram did not provide a resume duration. Job paused safely.',member_id=member.telegram_user_id,critical=True));return None,True
            if result.pause_job:
                await self._flush(job_id,True);await self._await_write(self.jobs.submit_mark_retry(job_id,candidate.ordinal,attempts,str(error.code),str(error)));await self._set_job(job_id,JobState.PAUSED,checkpoint={'last_ordinal':candidate.ordinal-1});await self._set_account(account_id,AccountState.AUTH_REQUIRED if error.code==InviteResultCode.AUTH else AccountState.ERROR,str(error));return None,True
            if result.retry and error.code in {InviteResultCode.NETWORK_TRANSIENT,InviteResultCode.SERVER_TRANSIENT}:
                if transient<len(TRANSIENT_RETRY_DELAYS_SECONDS):
                    delay=TRANSIENT_RETRY_DELAYS_SECONDS[transient];transient+=1;control=await self._sleep(delay)
                    if await self._handle_control(control,job_id,account_id):return None,True
                    if transient>=len(TRANSIENT_RETRY_DELAYS_SECONDS):return ItemUpdate(candidate.ordinal,MigrationItemState.FAILED,attempts,str(error.code),str(error)),False
                    continue
                return ItemUpdate(candidate.ordinal,MigrationItemState.FAILED,attempts,str(error.code),str(error)),False
            self.scheduler.mark_stable_candidate();return ItemUpdate(candidate.ordinal,result.state,attempts,str(error.code),str(error)),False
    async def run(self,job_id:int,account_id:int,target)->None:
        if self._running_job_id is not None:raise RuntimeError('This executor already has a running mutation job')
        self._running_job_id=job_id;self._stop_event=asyncio.Event();self._pause_event=asyncio.Event();self._result_buffer=[];self._last_flush=monotonic();self.governor.enable_performance_mode();await self._set_job(job_id,JobState.RUNNING);await self._set_account(account_id,AccountState.BUSY);buffer=CandidateBuffer(self.jobs,self.workers,job_id,account_id);await buffer.prime();interrupted=False
        try:
            async with self.governor.mutation_lock(account_id):
                while True:
                    if await self._handle_control(self._control(),job_id,account_id):interrupted=True;break
                    candidate=await buffer.pop()
                    if candidate is None:break
                    update,stop=await self._attempt(job_id,account_id,target,candidate)
                    if stop:interrupted=True;break
                    if update:self._result_buffer.append(update);await self._flush(job_id);self._schedule_flush(job_id);self.events.publish(DomainEvent('MigrationItemCompleted',{'job_id':job_id,'ordinal':update.ordinal,'state':str(update.state),'candidate_cache_depth':buffer.depth}))
            if not interrupted:
                await self._flush(job_id,True);summary=self.jobs.summary(job_id);final=JobState.COMPLETED_WITH_ERRORS if summary['failed'] else JobState.COMPLETED;await self._set_job(job_id,final,clear_waiting=True);await self._set_account(account_id,AccountState.READY);self.events.publish(DomainEvent('MigrationCompleted',{'job_id':job_id,**summary,'state':str(final)}))
        except Exception as exc:
            await self._flush(job_id,True);await self._set_job(job_id,JobState.FAILED,clear_waiting=True);await self._set_account(account_id,AccountState.ERROR,str(exc));raise
        finally:
            if self._flush_task and not self._flush_task.done():self._flush_task.cancel();await asyncio.gather(self._flush_task,return_exceptions=True)
            self.governor.disable_performance_mode();self._running_job_id=None;self._stop_event=None;self._pause_event=None
