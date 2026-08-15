from __future__ import annotations

from ..core.enums import JobState, JobType, TargetCoverage, TargetMemberState
from ..jobs.models import Job
from ..jobs.repository import JobRepository
from ..members.filter_spec import FilterSpec
from ..storage.database import Database
from .models import MigrationPlanSummary, PrecheckResult


class MigrationPlanner:
    def __init__(self, db: Database, jobs: JobRepository) -> None:
        self.db = db
        self.jobs = jobs

    def create_plan(
        self,
        account_id: int,
        source_dataset_id: int,
        target_group_id: int,
        precheck: PrecheckResult,
        filter_spec: FilterSpec | None = None,
    ) -> tuple[int, MigrationPlanSummary]:
        spec = filter_spec or FilterSpec()
        processed_ids = self.jobs.processed_user_ids_for_target(target_group_id)
        source_filter = {value.casefold() for value in spec.source if value.strip()}
        source_map: dict[int, set[str]] = {}
        with self.db.reader() as conn:
            rows = conn.execute(
                """SELECT
                       m.id,m.telegram_user_id,m.username,m.bot,m.deleted,
                       m.activity_status,pc.access_hash
                   FROM dataset_members dm
                   JOIN members m ON m.id=dm.member_id
                   LEFT JOIN peer_cache pc
                     ON pc.account_id=? AND pc.peer_id=m.telegram_user_id
                   WHERE dm.dataset_id=?
                   ORDER BY dm.member_id""",
                (account_id, source_dataset_id),
            ).fetchall()
            if source_filter:
                provenance_rows = conn.execute(
                    """SELECT member_id,source_label
                       FROM dataset_provenance
                       WHERE dataset_id=? AND source_label IS NOT NULL""",
                    (source_dataset_id,),
                ).fetchall()
                for provenance in provenance_rows:
                    source_map.setdefault(int(provenance["member_id"]), set()).add(
                        str(provenance["source_label"]).casefold()
                    )

        total = len(rows)
        invalid = 0
        filtered = 0
        already = 0
        ready_items: list[tuple[int, str]] = []
        seen: set[int] = set()

        for row in rows:
            uid = row["telegram_user_id"]
            if uid is None:
                invalid += 1
                continue
            uid = int(uid)
            # The hot path never resolves candidates. A selected account must already
            # have an account-scoped access hash from scan/import preparation.
            if row["access_hash"] is None:
                invalid += 1
                continue
            if uid in seen:
                filtered += 1
                continue
            seen.add(uid)
            if spec.exclude_bot and bool(row["bot"]):
                filtered += 1
                continue
            if spec.exclude_deleted and bool(row["deleted"]):
                filtered += 1
                continue
            if spec.username_required and not row["username"]:
                filtered += 1
                continue
            if spec.activity and str(row["activity_status"] or "") not in spec.activity:
                filtered += 1
                continue
            if source_filter and not (source_map.get(int(row["id"]), set()) & source_filter):
                filtered += 1
                continue
            if uid in processed_ids or uid in spec.exclude_processed:
                filtered += 1
                continue
            if uid in spec.exclude_target:
                filtered += 1
                continue
            if uid in precheck.target_ids:
                already += 1
                continue

            target_state = (
                TargetMemberState.KNOWN_ABSENT
                if precheck.coverage == TargetCoverage.COMPLETE
                else TargetMemberState.UNKNOWN_TARGET_STATE
            )
            ready_items.append((int(row["id"]), str(target_state)))

        job = Job(
            id=None,
            job_type=JobType.MIGRATION,
            state=JobState.READY,
            account_id=account_id,
            source_dataset_id=source_dataset_id,
            target_group_id=target_group_id,
            total=len(ready_items),
        )
        job_id = self.jobs.create(job)
        self.jobs.submit_add_items(job_id, ready_items).result(timeout=30.0)
        summary = MigrationPlanSummary(
            total_source=total,
            filtered=filtered,
            already_target=already,
            invalid=invalid,
            ready=len(ready_items),
        )
        return job_id, summary
