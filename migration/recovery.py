from __future__ import annotations

from datetime import datetime, timezone

from ..core.enums import JobState
from ..jobs.repository import JobRepository


class RecoveryService:
    def __init__(self, jobs: JobRepository) -> None:
        self.jobs = jobs

    def recoverable_jobs(self) -> list[int]:
        return self.jobs.recoverable()

    def normalize_after_restart(self) -> list[int]:
        """Make interrupted jobs explicit instead of pretending an executor still exists."""
        recovered: list[int] = []
        now = datetime.now(timezone.utc)
        for job_id in self.jobs.recoverable():
            row = self.jobs.get(job_id)
            if row is None:
                continue
            state = JobState(str(row["state"]))
            if state == JobState.WAITING_SERVER and row.get("waiting_until"):
                try:
                    wait_until = datetime.fromisoformat(str(row["waiting_until"]))
                except ValueError:
                    wait_until = now
                if wait_until.tzinfo is None:
                    wait_until = wait_until.replace(tzinfo=timezone.utc)
                if wait_until > now:
                    # Keep the server wait visible; user may resume after it expires.
                    recovered.append(job_id)
                    continue
            if state in {JobState.RUNNING, JobState.WAITING_SERVER}:
                self.jobs.submit_set_state(
                    job_id,
                    JobState.PAUSED,
                    checkpoint={
                        **self.jobs.get_checkpoint(job_id),
                        "recovered_after_restart": True,
                    },
                ).result(timeout=10.0)
            recovered.append(job_id)
        return recovered
