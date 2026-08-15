from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from time import monotonic

from ..core.clock import RealClock
from ..core.constants import (
    MIGRATION_DB_BATCH_SIZE,
    MIGRATION_DB_MAX_FLUSH_SECONDS,
    TRANSIENT_RETRY_DELAYS_SECONDS,
)
from ..core.enums import (
    AccountState,
    InviteResultCode,
    JobState,
    MigrationItemState,
)
from ..core.events import DomainEvent
from ..jobs.repository import ItemUpdate
from ..telegram.error_mapper import ErrorMapper
from .candidate_buffer import BufferedCandidate, CandidateBuffer
from .result_classifier import ResultClassifier


class MigrationExecutor:
    """Priority hot path for one resumable migration job."""

    def __init__(
        self,
        gateway,
        jobs,
        accounts,
        governor,
        events,
        scheduler,
        workers,
        metrics=None,
    ) -> None:
        self.gateway = gateway
        self.jobs = jobs
        self.accounts = accounts
        self.governor = governor
        self.events = events
        self.scheduler = scheduler
        self.workers = workers
        self.metrics = metrics
        self.errors = ErrorMapper()
        self.classifier = ResultClassifier()
        self._stop_event: asyncio.Event | None = None
        self._pause_event: asyncio.Event | None = None
        self._running_job_id: int | None = None
        self._result_buffer: list[ItemUpdate] = []
        self._last_flush = monotonic()
        self._flush_task: asyncio.Task[None] | None = None

    async def request_stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()

    async def request_pause(self) -> None:
        if self._pause_event is not None:
            self._pause_event.set()

    async def request_resume(self) -> None:
        if self._pause_event is not None:
            self._pause_event.clear()

    @staticmethod
    def _utc_wait_until(seconds: float) -> str:
        return (
            datetime.now(timezone.utc) + timedelta(seconds=max(0.0, seconds))
        ).isoformat()

    async def _await_write(self, future):
        return await asyncio.wrap_future(future)

    async def _set_account_state(
        self,
        account_id: int,
        state: AccountState,
        error: str | None = None,
    ) -> None:
        await self._await_write(self.accounts.submit_set_state(account_id, state, error))
        self.events.publish(
            DomainEvent(
                "AccountStateChanged",
                {"account_id": account_id, "state": str(state), "error": error},
            )
        )

    async def _set_job_state(
        self,
        job_id: int,
        state: JobState,
        waiting_until: str | None = None,
        checkpoint: dict | None = None,
        *,
        clear_waiting: bool = False,
    ) -> None:
        await self._await_write(
            self.jobs.submit_set_state(
                job_id,
                state,
                waiting_until,
                checkpoint=checkpoint,
                clear_waiting=clear_waiting,
            )
        )
        self.events.publish(
            DomainEvent(
                "JobStateChanged",
                {
                    "job_id": job_id,
                    "state": str(state),
                    "waiting_until": waiting_until,
                },
            )
        )

    def _control_state(self) -> str | None:
        if self._stop_event is not None and self._stop_event.is_set():
            return "stop"
        if self._pause_event is not None and self._pause_event.is_set():
            return "pause"
        return None

    async def _controlled_sleep(self, seconds: float) -> str | None:
        seconds = max(0.0, seconds)
        if seconds <= 0:
            return self._control_state()
        # FakeClock advances immediately; RealClock waits can be interrupted by UI commands.
        if not isinstance(self.scheduler.clock, RealClock):
            await self.scheduler.clock.sleep(seconds)
            return self._control_state()

        deadline = self.scheduler.clock.monotonic() + seconds
        while True:
            control = self._control_state()
            if control is not None:
                return control
            remaining = deadline - self.scheduler.clock.monotonic()
            if remaining <= 0:
                return None
            await asyncio.sleep(min(0.25, remaining))

    async def _wait_scheduler(self) -> str | None:
        return await self._controlled_sleep(self.scheduler.remaining_delay())

    async def _flush_results(self, job_id: int, *, force: bool = False) -> None:
        if not self._result_buffer:
            return
        elapsed = monotonic() - self._last_flush
        if (
            not force
            and len(self._result_buffer) < MIGRATION_DB_BATCH_SIZE
            and elapsed < MIGRATION_DB_MAX_FLUSH_SECONDS
        ):
            return
        updates = self._result_buffer
        self._result_buffer = []
        last_ordinal = updates[-1].ordinal
        await self._await_write(
            self.jobs.submit_update_items_batch(
                job_id,
                updates,
                checkpoint={"last_ordinal": last_ordinal},
            )
        )
        self._last_flush = monotonic()

    def _schedule_result_flush(self, job_id: int) -> None:
        """Ensure a partial result batch is persisted after at most ~1 second."""
        if not isinstance(self.scheduler.clock, RealClock):
            return
        if self._flush_task is not None and not self._flush_task.done():
            return

        async def delayed_flush() -> None:
            try:
                await asyncio.sleep(MIGRATION_DB_MAX_FLUSH_SECONDS)
                await self._flush_results(job_id, force=True)
            finally:
                self._flush_task = None

        self._flush_task = asyncio.create_task(
            delayed_flush(),
            name=f"TMS-MigrationFlush-{job_id}",
        )

    async def _pause_current_candidate(
        self,
        job_id: int,
        candidate: BufferedCandidate,
        attempts: int,
        error,
        account_id: int,
    ) -> None:
        await self._flush_results(job_id, force=True)
        await self._await_write(
            self.jobs.submit_mark_retry(
                job_id,
                candidate.ordinal,
                attempts,
                str(error.code) if error else None,
                str(error) if error else None,
            )
        )
        await self._await_write(
            self.jobs.submit_event(
                job_id,
                "WARN",
                "MIGRATION_PAUSED",
                str(error) if error else "Migration paused",
                member_id=member_id if (member_id := candidate.member.telegram_user_id) else None,
                critical=True,
            )
        )
        account_state = (
            AccountState.AUTH_REQUIRED
            if error and error.code == InviteResultCode.AUTH
            else AccountState.ERROR
        )
        await self._set_account_state(account_id, account_state, str(error) if error else None)
        await self._set_job_state(
            job_id,
            JobState.PAUSED,
            checkpoint={"last_ordinal": candidate.ordinal - 1},
        )

    async def _handle_control(
        self,
        control: str | None,
        job_id: int,
        account_id: int,
    ) -> bool:
        if control == "stop":
            await self._flush_results(job_id, force=True)
            await self._set_job_state(job_id, JobState.CANCELLED, clear_waiting=True)
            await self._await_write(
                self.jobs.submit_event(job_id, "INFO", "MIGRATION_CANCELLED", critical=True)
            )
            await self._set_account_state(account_id, AccountState.READY)
            return True
        if control == "pause":
            await self._flush_results(job_id, force=True)
            await self._set_job_state(job_id, JobState.PAUSED)
            await self._await_write(
                self.jobs.submit_event(job_id, "INFO", "MIGRATION_PAUSED_BY_USER", critical=True)
            )
            account_state = (
                AccountState.WAITING_SERVER
                if self.scheduler.server_wait_remaining() > 0
                else AccountState.READY
            )
            await self._set_account_state(account_id, account_state)
            return True
        return False

    async def _attempt_candidate(
        self,
        job_id: int,
        account_id: int,
        target,
        candidate: BufferedCandidate,
    ) -> tuple[ItemUpdate | None, bool]:
        attempts = candidate.persisted_attempts
        transient_failures = 0
        member = candidate.member

        if member.telegram_user_id is None or member.access_hash is None:
            return (
                ItemUpdate(
                    candidate.ordinal,
                    MigrationItemState.FAILED,
                    attempts,
                    str(InviteResultCode.INVALID_USER),
                    "Candidate lacks Telegram user id or account-scoped access hash",
                ),
                False,
            )

        while True:
            control = await self._wait_scheduler()
            if await self._handle_control(control, job_id, account_id):
                return None, True

            local_prepare_started = monotonic()
            self.scheduler.mark_attempt()
            attempts += 1
            rpc_started = monotonic()
            error = None
            try:
                await self.gateway.invite_user(account_id, target, member)
            except Exception as exc:
                error = self.errors.map(exc)
            rpc_elapsed_ms = (monotonic() - rpc_started) * 1000.0
            local_prepare_ms = (rpc_started - local_prepare_started) * 1000.0
            if self.metrics is not None:
                self.metrics.observe("rpc_latency_ms", rpc_elapsed_ms)
                self.metrics.observe("local_prepare_ms", local_prepare_ms)

            classified = self.classifier.classify(error)
            if error is None:
                return ItemUpdate(
                    candidate.ordinal,
                    MigrationItemState.SUCCESS,
                    attempts,
                ), False

            if error.code == InviteResultCode.RATE_LIMIT:
                wait = max(0, classified.wait_seconds or 0)
                self.scheduler.apply_server_wait(wait)
                wait_until = self._utc_wait_until(wait)
                await self._flush_results(job_id, force=True)
                await self._await_write(
                    self.jobs.submit_mark_retry(
                        job_id,
                        candidate.ordinal,
                        attempts,
                        str(error.code),
                        str(error),
                        next_retry_at=wait_until,
                    )
                )
                await self._set_account_state(
                    account_id,
                    AccountState.WAITING_SERVER,
                    str(error),
                )
                await self._set_job_state(
                    job_id,
                    JobState.WAITING_SERVER,
                    wait_until,
                    checkpoint={"last_ordinal": candidate.ordinal - 1},
                )
                await self._await_write(
                    self.jobs.submit_event(
                        job_id,
                        "WARN",
                        "RATE_LIMIT_WAIT",
                        f"Waiting {wait} seconds before retrying the same candidate",
                        member_id=member.telegram_user_id,
                        critical=True,
                    )
                )
                control = await self._wait_scheduler()
                if await self._handle_control(control, job_id, account_id):
                    return None, True
                await self._set_account_state(account_id, AccountState.BUSY)
                await self._set_job_state(job_id, JobState.RUNNING, clear_waiting=True)
                # Rate limits never consume the transient retry budget and the same
                # candidate remains current.
                continue

            if classified.pause_job:
                await self._pause_current_candidate(
                    job_id,
                    candidate,
                    attempts,
                    error,
                    account_id,
                )
                return None, True

            if classified.retry and error.code in {
                InviteResultCode.NETWORK_TRANSIENT,
                InviteResultCode.SERVER_TRANSIENT,
            }:
                transient_failures += 1
                if transient_failures < 3:
                    retry_delay = TRANSIENT_RETRY_DELAYS_SECONDS[transient_failures - 1]
                    control = await self._controlled_sleep(retry_delay)
                    if await self._handle_control(control, job_id, account_id):
                        return None, True
                    continue
                # The locked policy includes a final 4-second transient cooldown before
                # the item is declared failed; no fourth invite RPC is sent.
                control = await self._controlled_sleep(TRANSIENT_RETRY_DELAYS_SECONDS[2])
                if await self._handle_control(control, job_id, account_id):
                    return None, True
                return ItemUpdate(
                    candidate.ordinal,
                    MigrationItemState.FAILED,
                    attempts,
                    str(error.code),
                    str(error),
                ), False

            return ItemUpdate(
                candidate.ordinal,
                classified.state,
                attempts,
                str(error.code),
                str(error),
            ), False

    async def run(self, job_id: int, account_id: int, target) -> None:
        if self._running_job_id is not None:
            raise RuntimeError("This executor already has a running migration job")
        self._running_job_id = job_id
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._result_buffer = []
        self._last_flush = monotonic()
        self.governor.enable_performance_mode()
        await self._set_job_state(job_id, JobState.RUNNING)
        await self._set_account_state(account_id, AccountState.BUSY)
        await self._await_write(
            self.jobs.submit_event(
                job_id,
                "INFO",
                "MIGRATION_STARTED",
                f"Invite interval: {self.scheduler.interval:g}s",
                critical=True,
            )
        )
        buffer = CandidateBuffer(
            self.jobs,
            self.workers,
            job_id,
            account_id,
        )
        await buffer.prime()
        self.events.publish(
            DomainEvent(
                "MigrationStarted",
                {"job_id": job_id, "account_id": account_id},
            )
        )

        interrupted = False
        try:
            async with self.governor.mutation_lock(account_id):
                while True:
                    control = self._control_state()
                    if await self._handle_control(control, job_id, account_id):
                        interrupted = True
                        break
                    candidate = await buffer.pop()
                    if candidate is None:
                        break
                    update, did_interrupt = await self._attempt_candidate(
                        job_id,
                        account_id,
                        target,
                        candidate,
                    )
                    if did_interrupt:
                        interrupted = True
                        break
                    if update is None:
                        continue
                    self._result_buffer.append(update)
                    await self._flush_results(job_id)
                    if self._result_buffer:
                        self._schedule_result_flush(job_id)
                    self.events.publish(
                        DomainEvent(
                            "MigrationItemCompleted",
                            {
                                "job_id": job_id,
                                "ordinal": update.ordinal,
                                "state": str(update.state),
                                "candidate_cache_depth": buffer.depth,
                            },
                        )
                    )

            if not interrupted:
                await self._flush_results(job_id, force=True)
                summary = self.jobs.summary(job_id)
                final_state = (
                    JobState.COMPLETED_WITH_ERRORS
                    if summary["failed"] > 0
                    else JobState.COMPLETED
                )
                await self._set_job_state(job_id, final_state, clear_waiting=True)
                await self._set_account_state(account_id, AccountState.READY)
                await self._await_write(
                    self.jobs.submit_event(
                        job_id,
                        "INFO",
                        "MIGRATION_COMPLETED",
                        f"success={summary['success']} skipped={summary['skipped']} failed={summary['failed']}",
                        critical=True,
                    )
                )
                self.events.publish(
                    DomainEvent(
                        "MigrationCompleted",
                        {"job_id": job_id, **summary, "state": str(final_state)},
                    )
                )
        except Exception as exc:
            await self._flush_results(job_id, force=True)
            await self._set_job_state(job_id, JobState.FAILED, clear_waiting=True)
            await self._set_account_state(account_id, AccountState.ERROR, str(exc))
            await self._await_write(
                self.jobs.submit_event(
                    job_id,
                    "ERROR",
                    "MIGRATION_FAILED",
                    str(exc),
                    critical=True,
                )
            )
            self.events.publish(
                DomainEvent("JobFailed", {"job_id": job_id, "error": str(exc)})
            )
            raise
        finally:
            flush_task = self._flush_task
            self._flush_task = None
            if flush_task is not None and not flush_task.done():
                flush_task.cancel()
                await asyncio.gather(flush_task, return_exceptions=True)
            self.governor.disable_performance_mode()
            self._running_job_id = None
            self._stop_event = None
            self._pause_event = None
