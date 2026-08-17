from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..core.enums import JobState, JobType
from ..core.events import DomainEvent
from ..datasets.models import Dataset
from ..jobs.models import Job
from ..members.filter_spec import FilterSpec
from ..migration.executor import MigrationExecutor
from ..migration.scheduler import InviteScheduler


class CommandHandlers:
    """Registers UI commands and keeps blocking/network work off the Qt thread."""

    def __init__(self, context) -> None:
        self.ctx = context
        self._executors: dict[int, MigrationExecutor] = {}

    async def prepare_shutdown(self, timeout: float = 3.0) -> None:
        """Request a resumable pause before Telegram clients are disconnected."""
        executors = list(self._executors.values())
        for executor in executors:
            await executor.request_pause()
        if not executors:
            return
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(0.0, timeout)
        while loop.time() < deadline:
            if all(executor._running_job_id is None for executor in executors):
                return
            await asyncio.sleep(0.05)

    def register_all(self) -> None:
        c = self.ctx.commands
        c.register("settings.update", self.update_settings)
        c.register("account.add", self.add_account)
        c.register("account.enable", self.enable_account)
        c.register("account.delete", self.delete_account)
        c.register("account.select", self.select_account)
        c.register("account.connect", self.connect_account)
        c.register("auth.send_code", self.send_code)
        c.register("auth.sign_in", self.sign_in)
        c.register("source.resolve", self.resolve_source)
        c.register("source.joined_groups", self.joined_groups)
        c.register("source.select_group", self.select_source_group)
        c.register("source.scan", self.scan_source)
        c.register("source.cancel_scan", self.cancel_scan)
        c.register("source.resume_scan", self.resume_scan)
        c.register("dataset.import", self.import_dataset)
        c.register("dataset.combine", self.combine_dataset)
        c.register("dataset.select", self.select_dataset)
        c.register("dataset.export", self.export_dataset)
        c.register("target.resolve", self.resolve_target)
        c.register("migration.precheck", self.precheck_target)
        c.register("migration.plan", self.plan_migration)
        c.register("migration.start", self.start_migration)
        c.register("migration.pause", self.pause_migration)
        c.register("migration.stop", self.stop_migration)
        c.register("migration.resume", self.resume_migration)
        c.register("job.export_results", self.export_job_results)
        c.register("job.export_log", self.export_job_log)
        c.register("job.resume", self.resume_job)
        c.register("utility.join", self.join_group)
        c.register("utility.leave", self.leave_group)

    def _publish_failure(self, command: str, exc: BaseException) -> None:
        self.ctx.runtime.events.publish(
            DomainEvent(
                "CommandFailed",
                {"command": command, "error": str(exc), "type": type(exc).__name__},
            )
        )

    def _submit_worker(
        self,
        command: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
    ) -> None:
        future = self.ctx.runtime.workers.submit(func)

        def done(completed) -> None:
            try:
                result = completed.result()
                if on_success is not None:
                    on_success(result)
            except BaseException as exc:
                self._publish_failure(command, exc)

        future.add_done_callback(done)

    def _submit_network(
        self,
        command: str,
        coro,
        on_success: Callable[[Any], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        try:
            future = self.ctx.runtime.network.submit(coro)
        except BaseException as exc:
            close = getattr(coro, "close", None)
            if callable(close):
                close()
            self._publish_failure(command, exc)
            if on_finished is not None:
                on_finished()
            return

        def done(completed) -> None:
            try:
                result = completed.result()
                if on_success is not None:
                    on_success(result)
            except BaseException as exc:
                self._publish_failure(command, exc)
            finally:
                if on_finished is not None:
                    on_finished()

        future.add_done_callback(done)

    def update_settings(self, api_id: int, api_hash: str) -> None:
        if api_id <= 0 or not api_hash.strip():
            raise ValueError("API ID and API Hash are required")

        async def apply_credentials() -> None:
            await self.ctx.clients.close_all()
            self.ctx.clients.update_credentials(api_id, api_hash.strip())

        def save_settings() -> None:
            self.ctx.settings.api_id = api_id
            self.ctx.settings.api_hash = api_hash.strip()
            self.ctx.settings.save(self.ctx.paths)

        def credentials_applied(_result: Any) -> None:
            self._submit_worker(
                "settings.update",
                save_settings,
                lambda _saved: self.ctx.runtime.events.publish(
                    DomainEvent("SettingsChanged", {})
                ),
            )

        self._submit_network(
            "settings.update",
            apply_credentials(),
            credentials_applied,
        )

    def _require_enabled_account(self, account_id: int):
        account = self.ctx.accounts.get(account_id)
        if account is None:
            raise ValueError("Account not found")
        if not account.enabled:
            raise RuntimeError("Selected account is disabled")
        return account

    def add_account(self, phone: str) -> None:
        def done(account) -> None:
            self.ctx.runtime.events.publish(
                DomainEvent("AccountsChanged", {"account_id": account.id})
            )

        self._submit_worker("account.add", lambda: self.ctx.account_service.add(phone), done)

    def enable_account(self, account_id: int, enabled: bool) -> None:
        if not enabled:
            account = self.ctx.accounts.get(account_id)
            if account is None:
                raise ValueError("Account not found")
            if str(account.status) in {"BUSY", "WAITING_SERVER", "CONNECTING"} or (
                self.ctx.jobs.has_nonterminal_jobs(account_id)
            ):
                raise RuntimeError("Stop/pause active Telegram work before disabling this account")

        def operation() -> None:
            self.ctx.account_service.enable(account_id, enabled)

        self._submit_worker(
            "account.enable",
            operation,
            lambda _result: self.ctx.runtime.events.publish(
                DomainEvent("AccountsChanged", {"account_id": account_id})
            ),
        )

    def delete_account(self, account_id: int) -> None:
        if self.ctx.accounts.get(account_id) is None:
            raise ValueError("Account not found")
        if self.ctx.jobs.has_nonterminal_jobs(account_id):
            raise RuntimeError(
                "Account has non-terminal jobs. Complete/cancel those jobs before deletion."
            )

        async def disconnect_then_delete() -> None:
            await self.ctx.clients.disconnect(account_id)

        def after_disconnect(_result: Any) -> None:
            self._submit_worker(
                "account.delete",
                lambda: self.ctx.account_service.delete(account_id),
                lambda _x: self.ctx.runtime.events.publish(
                    DomainEvent("AccountsChanged", {"account_id": account_id})
                ),
            )

        self._submit_network("account.delete", disconnect_then_delete(), after_disconnect)

    def select_account(self, account_id: int) -> None:
        self.ctx.state.update(active_account_id=account_id)
        self.ctx.runtime.events.publish(
            DomainEvent("ActiveAccountChanged", {"account_id": account_id})
        )

    def connect_account(self, account_id: int) -> None:
        self._require_enabled_account(account_id)
        self._submit_network(
            "account.connect",
            self.ctx.auth.connect_existing(account_id),
            lambda identity: self.ctx.runtime.events.publish(
                DomainEvent(
                    "AccountConnected",
                    {
                        "account_id": account_id,
                        "authorized": identity is not None,
                        "identity": asdict(identity) if identity else None,
                    },
                )
            ),
        )

    def send_code(self, account_id: int) -> None:
        account = self._require_enabled_account(account_id)

        def done(code_hash: str) -> None:
            if code_hash:
                self.ctx.state.set_phone_code_hash(account_id, code_hash)
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "AuthCodeSent",
                    {"account_id": account_id, "already_authorized": not bool(code_hash)},
                )
            )

        self._submit_network(
            "auth.send_code",
            self.ctx.auth.send_code(account_id, account.phone),
            done,
        )

    def sign_in(self, account_id: int, code: str, password: str | None = None) -> None:
        account = self._require_enabled_account(account_id)
        code_hash = self.ctx.state.snapshot().phone_code_hashes.get(account_id)
        if not code_hash:
            raise ValueError("Request OTP before signing in")

        def done(identity) -> None:
            self.ctx.state.pop_phone_code_hash(account_id)
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "AccountAuthenticated",
                    {"account_id": account_id, "identity": asdict(identity)},
                )
            )

        self._submit_network(
            "auth.sign_in",
            self.ctx.auth.sign_in(account_id, account.phone, code, code_hash, password),
            done,
        )

    async def _resolve_and_persist(self, account_id: int, reference: str):
        group = await self.ctx.group_service.resolve(account_id, reference)
        local_id = await asyncio.wrap_future(self.ctx.groups.submit_upsert(group))
        group.local_group_id = local_id
        return group

    def resolve_source(self, account_id: int, reference: str) -> None:
        self._require_enabled_account(account_id)
        def done(group) -> None:
            self.ctx.state.update(source_group=group, source_account_id=account_id)
            self.ctx.runtime.events.publish(
                DomainEvent("SourceGroupResolved", {"group": group})
            )

        self._submit_network(
            "source.resolve",
            self._resolve_and_persist(account_id, reference),
            done,
        )

    def joined_groups(self, account_id: int) -> None:
        self._require_enabled_account(account_id)
        async def operation():
            groups = await self.ctx.gateway.get_joined_groups(account_id)
            for group in groups:
                group.local_group_id = await asyncio.wrap_future(
                    self.ctx.groups.submit_upsert(group)
                )
            return groups

        self._submit_network(
            "source.joined_groups",
            operation(),
            lambda groups: self.ctx.runtime.events.publish(
                DomainEvent("JoinedGroupsLoaded", {"account_id": account_id, "groups": groups})
            ),
        )

    def select_source_group(self, account_id: int, group) -> None:
        self.ctx.state.update(source_group=group, source_account_id=account_id)
        self.ctx.runtime.events.publish(DomainEvent("SourceGroupResolved", {"group": group}))

    def scan_source(self, account_id: int, dataset_name: str) -> None:
        self._require_enabled_account(account_id)
        snapshot = self.ctx.state.snapshot()
        group = snapshot.source_group
        if group is None or group.local_group_id is None:
            raise ValueError("Resolve/select a source group first")
        if snapshot.source_account_id != account_id:
            raise ValueError("Source group was resolved with a different account; resolve it again")

        def prepare() -> tuple[int, int]:
            dataset_id = self.ctx.datasets.create(
                Dataset(
                    None,
                    dataset_name.strip() or group.title,
                    "TELEGRAM_GROUP",
                    str(group.telegram_id),
                )
            )
            job_id = self.ctx.jobs.create(
                Job(
                    None,
                    JobType.SCAN,
                    JobState.READY,
                    account_id=account_id,
                    source_dataset_id=dataset_id,
                    target_group_id=group.local_group_id,
                )
            )
            return dataset_id, job_id

        def start(prepared: tuple[int, int]) -> None:
            dataset_id, job_id = prepared
            self.ctx.state.update(source_dataset_id=dataset_id)
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "MemberScanStarted",
                    {"job_id": job_id, "dataset_id": dataset_id},
                )
            )
            self._submit_network(
                "source.scan",
                self.ctx.scanner.scan(job_id, account_id, group, dataset_id),
            )

        self._submit_worker("source.scan.prepare", prepare, start)

    def cancel_scan(self, job_id: int) -> None:
        self._submit_network("source.cancel_scan", self.ctx.scanner.cancel(job_id))


    def resume_scan(self, job_id: int) -> None:
        row = self.ctx.jobs.get(job_id)
        if row is None or str(row["job_type"]) != str(JobType.SCAN):
            raise ValueError("Scan job not found")
        if str(row["state"]) != str(JobState.PAUSED):
            raise ValueError("Only paused scan jobs can be resumed")
        if (
            row["account_id"] is None
            or row["source_dataset_id"] is None
            or row["target_group_id"] is None
        ):
            raise ValueError("Scan job is missing account/dataset/group metadata")
        account_id = int(row["account_id"])
        self._require_enabled_account(account_id)
        dataset_id = int(row["source_dataset_id"])
        group = self.ctx.groups.get(int(row["target_group_id"]), account_id)
        if group is None:
            raise ValueError("Source group metadata is unavailable")
        checkpoint_data = self.ctx.jobs.get_checkpoint(job_id)
        from ..telegram.participant_scanner import ScanCheckpoint

        checkpoint = ScanCheckpoint(
            offset=int(checkpoint_data.get("offset", 0) or 0),
            accepted=int(checkpoint_data.get("accepted", 0) or 0),
            invalid=int(checkpoint_data.get("invalid", 0) or 0),
        )
        self._submit_network(
            "source.resume_scan",
            self.ctx.scanner.scan(
                job_id,
                account_id,
                group,
                dataset_id,
                checkpoint,
            ),
        )

    def import_dataset(
        self,
        path: str,
        name: str,
        account_id: int | None = None,
    ) -> None:
        self._submit_worker(
            "dataset.import",
            lambda: self.ctx.import_export.import_dataset(
                Path(path), name, account_id=account_id
            ),
        )

    def combine_dataset(self, name: str, a_id: int, b_id: int, operation: str) -> None:
        def done(dataset_id: int) -> None:
            self.ctx.state.update(source_dataset_id=dataset_id)
            self.ctx.runtime.events.publish(
                DomainEvent("DatasetCreated", {"dataset_id": dataset_id})
            )

        self._submit_worker(
            "dataset.combine",
            lambda: self.ctx.dataset_service.combine(name, a_id, b_id, operation),
            done,
        )

    def select_dataset(self, dataset_id: int) -> None:
        self.ctx.state.update(source_dataset_id=dataset_id)
        self.ctx.runtime.events.publish(
            DomainEvent("ActiveDatasetChanged", {"dataset_id": dataset_id})
        )

    def export_dataset(
        self,
        dataset_id: int,
        path: str,
        account_id: int | None = None,
    ) -> None:
        if self.ctx.runtime.governor.performance_mode:
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "BackgroundTaskDeferred",
                    {"task": "export", "reason": "Migration Performance Mode is active"},
                )
            )
            return
        self._submit_worker(
            "dataset.export",
            lambda: self.ctx.import_export.export_dataset(
                dataset_id, Path(path), account_id=account_id
            ),
        )

    def resolve_target(self, account_id: int, reference: str) -> None:
        self._require_enabled_account(account_id)
        def done(group) -> None:
            self.ctx.state.update(
                target_group=group,
                target_account_id=account_id,
                precheck=None,
                migration_job_id=None,
            )
            self.ctx.runtime.events.publish(
                DomainEvent("TargetGroupResolved", {"group": group})
            )

        self._submit_network(
            "target.resolve",
            self._resolve_and_persist(account_id, reference),
            done,
        )

    def precheck_target(self, account_id: int) -> None:
        self._require_enabled_account(account_id)
        snapshot = self.ctx.state.snapshot()
        target = snapshot.target_group
        if target is None or target.local_group_id is None:
            raise ValueError("Resolve target group first")
        if snapshot.target_account_id != account_id:
            raise ValueError("Target group was resolved with a different account; resolve it again")

        def prepare() -> int:
            return self.ctx.jobs.create(
                Job(
                    None,
                    JobType.TARGET_SCAN,
                    JobState.RUNNING,
                    account_id=account_id,
                    target_group_id=target.local_group_id,
                )
            )

        def start(job_id: int) -> None:
            async def operation():
                await asyncio.wrap_future(
                    self.ctx.jobs.submit_event(
                        job_id,
                        "INFO",
                        "TARGET_PRECHECK_STARTED",
                        f"target={target.telegram_id}",
                        critical=True,
                    )
                )
                try:
                    result = await self.ctx.precheck.run(
                        self.ctx.gateway, account_id, target
                    )
                    await asyncio.wrap_future(
                        self.ctx.jobs.submit_set_state(
                            job_id,
                            JobState.COMPLETED,
                            checkpoint={
                                "coverage": str(result.coverage),
                                "target_count": len(result.target_ids),
                            },
                        )
                    )
                    await asyncio.wrap_future(
                        self.ctx.jobs.submit_event(
                            job_id,
                            "INFO",
                            "TARGET_PRECHECK_COMPLETED",
                            f"coverage={result.coverage} target_count={len(result.target_ids)}",
                            critical=True,
                        )
                    )
                    return result
                except Exception as exc:
                    await asyncio.wrap_future(
                        self.ctx.jobs.submit_set_state(
                            job_id,
                            JobState.FAILED,
                            checkpoint={"error": str(exc)},
                        )
                    )
                    await asyncio.wrap_future(
                        self.ctx.jobs.submit_event(
                            job_id,
                            "ERROR",
                            "TARGET_PRECHECK_FAILED",
                            str(exc),
                            critical=True,
                        )
                    )
                    raise

            def done(result) -> None:
                self.ctx.state.update(precheck=result)
                self.ctx.runtime.events.publish(
                    DomainEvent(
                        "TargetPrecheckCompleted",
                        {
                            "job_id": job_id,
                            "coverage": str(result.coverage),
                            "target_count": len(result.target_ids),
                        },
                    )
                )

            self._submit_network("migration.precheck", operation(), done)

        self._submit_worker("migration.precheck.prepare", prepare, start)

    def plan_migration(
        self,
        account_id: int,
        source_dataset_id: int,
        filter_spec: FilterSpec | None = None,
    ) -> None:
        self._require_enabled_account(account_id)
        snapshot = self.ctx.state.snapshot()
        if snapshot.target_group is None or snapshot.target_group.local_group_id is None:
            raise ValueError("Resolve target group first")
        if snapshot.target_account_id != account_id:
            raise ValueError("Target group/pre-check belongs to a different account")
        if snapshot.precheck is None:
            raise ValueError("Run target pre-check first")
        if not snapshot.target_group.can_invite:
            raise PermissionError("Selected account has no invite permission in target group")

        target_group_id = snapshot.target_group.local_group_id

        def operation():
            return self.ctx.planner.create_plan(
                account_id,
                source_dataset_id,
                target_group_id,
                snapshot.precheck,
                filter_spec,
            )

        def done(result) -> None:
            job_id, summary = result
            self.ctx.state.update(
                source_dataset_id=source_dataset_id,
                migration_job_id=job_id,
                plan_summary=summary,
            )
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "MigrationPlanReady",
                    {"job_id": job_id, "summary": summary},
                )
            )

        self._submit_worker("migration.plan", operation, done)

    @staticmethod
    def _remaining_wait(waiting_until: str | None) -> float:
        if not waiting_until:
            return 0.0
        try:
            wait_dt = datetime.fromisoformat(str(waiting_until))
        except ValueError:
            return 0.0
        if wait_dt.tzinfo is None:
            wait_dt = wait_dt.replace(tzinfo=timezone.utc)
        return max(0.0, (wait_dt - datetime.now(timezone.utc)).total_seconds())

    def _apply_account_server_wait(
        self, executor: MigrationExecutor, account_id: int
    ) -> None:
        remaining = self._remaining_wait(self.ctx.jobs.account_waiting_until(account_id))
        if remaining > 0:
            executor.scheduler.apply_server_wait(remaining)

    def _new_executor(self, job_id: int, interval: float) -> MigrationExecutor:
        scheduler = InviteScheduler(interval)
        executor = MigrationExecutor(
            self.ctx.gateway,
            self.ctx.jobs,
            self.ctx.accounts,
            self.ctx.runtime.governor,
            self.ctx.runtime.events,
            scheduler,
            self.ctx.runtime.workers,
            self.ctx.metrics,
        )
        self._executors[job_id] = executor
        return executor

    def start_migration(
        self,
        job_id: int,
        account_id: int,
        interval_seconds: float,
    ) -> None:
        if job_id in self._executors:
            raise RuntimeError("Migration job is already running")
        self._require_enabled_account(account_id)
        row = self.ctx.jobs.get(job_id)
        if row is None or str(row["job_type"]) != str(JobType.MIGRATION):
            raise ValueError("Migration job not found")
        if str(row["state"]) != str(JobState.READY):
            raise ValueError("Only READY migration jobs can be started")
        if row["account_id"] is None or int(row["account_id"]) != account_id:
            raise ValueError("Selected account does not match the migration plan")
        if row["target_group_id"] is None:
            raise ValueError("Migration job is missing target metadata")
        target = self.ctx.groups.get(int(row["target_group_id"]), account_id)
        if target is None:
            raise ValueError("Target group metadata is unavailable")
        target.can_invite = True  # validated when the persisted plan was created
        executor = self._new_executor(job_id, interval_seconds)
        self._apply_account_server_wait(executor, account_id)

        self._submit_network(
            "migration.start",
            executor.run(job_id, account_id, target),
            on_finished=lambda: self._executors.pop(job_id, None),
        )

    def pause_migration(self, job_id: int) -> None:
        executor = self._executors.get(job_id)
        if executor is None:
            raise ValueError("Migration job is not currently running")
        self._submit_network("migration.pause", executor.request_pause())

    def stop_migration(self, job_id: int) -> None:
        executor = self._executors.get(job_id)
        if executor is None:
            raise ValueError("Migration job is not currently running")
        self._submit_network("migration.stop", executor.request_stop())

    def resume_migration(self, job_id: int, interval_seconds: float) -> None:
        if job_id in self._executors:
            raise RuntimeError("Migration job is already running")
        row = self.ctx.jobs.get(job_id)
        if row is None or str(row["job_type"]) != str(JobType.MIGRATION):
            raise ValueError("Migration job not found")
        if str(row["state"]) not in {str(JobState.PAUSED), str(JobState.WAITING_SERVER)}:
            raise ValueError("Only PAUSED/WAITING_SERVER migration jobs can be resumed")
        if row["account_id"] is None or row["target_group_id"] is None:
            raise ValueError("Migration job is missing account/target metadata")
        account_id = int(row["account_id"])
        self._require_enabled_account(account_id)
        target = self.ctx.groups.get(int(row["target_group_id"]), account_id)
        if target is None:
            raise ValueError("Target group metadata is unavailable")
        # Capabilities are not persisted; the existing plan already validated invite
        # rights. The next RPC remains authoritative if rights changed.
        target.can_invite = True
        executor = self._new_executor(job_id, interval_seconds)
        self._apply_account_server_wait(executor, account_id)

        self._submit_network(
            "migration.resume",
            executor.run(job_id, account_id, target),
            on_finished=lambda: self._executors.pop(job_id, None),
        )


    def resume_job(self, job_id: int, interval_seconds: float) -> None:
        row = self.ctx.jobs.get(job_id)
        if row is None:
            raise ValueError("Job not found")
        job_type = str(row["job_type"])
        if job_type == str(JobType.MIGRATION):
            self.resume_migration(job_id, interval_seconds)
            return
        if job_type == str(JobType.SCAN):
            self.resume_scan(job_id)
            return
        raise ValueError(f"Job type {job_type} is not resumable")

    def export_job_log(self, job_id: int, path: str) -> None:
        if self.ctx.runtime.governor.performance_mode:
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "BackgroundTaskDeferred",
                    {"task": "log_export", "reason": "Migration Performance Mode is active"},
                )
            )
            return
        self._submit_worker(
            "job.export_log",
            lambda: self.ctx.import_export.export_job_log(job_id, Path(path)),
            lambda _x: self.ctx.runtime.events.publish(
                DomainEvent("LogExportCompleted", {"job_id": job_id, "path": path})
            ),
        )

    def export_job_results(self, job_id: int, path: str) -> None:
        if self.ctx.runtime.governor.performance_mode:
            self.ctx.runtime.events.publish(
                DomainEvent(
                    "BackgroundTaskDeferred",
                    {"task": "result_export", "reason": "Migration Performance Mode is active"},
                )
            )
            return
        self._submit_worker(
            "job.export_results",
            lambda: self.ctx.import_export.export_job_results(job_id, Path(path)),
            lambda _x: self.ctx.runtime.events.publish(
                DomainEvent("ResultExportCompleted", {"job_id": job_id, "path": path})
            ),
        )

    def join_group(self, account_id: int, reference: str) -> None:
        self._require_enabled_account(account_id)
        self._submit_network(
            "utility.join",
            self.ctx.membership.join(account_id, reference),
            lambda group: self.ctx.runtime.events.publish(
                DomainEvent("UtilityCompleted", {"action": "join", "group": group})
            ),
        )

    def leave_group(self, account_id: int, reference: str) -> None:
        self._require_enabled_account(account_id)
        async def operation():
            group = await self._resolve_and_persist(account_id, reference)
            await self.ctx.membership.leave(account_id, group)
            return group

        self._submit_network(
            "utility.leave",
            operation(),
            lambda group: self.ctx.runtime.events.publish(
                DomainEvent("UtilityCompleted", {"action": "leave", "group": group})
            ),
        )
