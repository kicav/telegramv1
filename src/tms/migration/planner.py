from ..core.enums import JobState, JobType
from ..jobs.models import Job
from ..jobs.repository import JobRepository
from ..storage.database import Database
from .models import MigrationPlanSummary, PrecheckResult


class MigrationPlanner:
    def __init__(self, db: Database, jobs: JobRepository) -> None:
        self.db=db; self.jobs=jobs

    def create_plan(self, account_id: int, source_dataset_id: int, target_group_id: int, precheck: PrecheckResult) -> tuple[int,MigrationPlanSummary]:
        with self.db.reader() as conn:
            rows=conn.execute("""SELECT m.id,m.telegram_user_id,m.bot,m.deleted FROM dataset_members dm
               JOIN members m ON m.id=dm.member_id WHERE dm.dataset_id=? ORDER BY dm.member_id""",(source_dataset_id,)).fetchall()
        total=len(rows); invalid=0; filtered=0; already=0; ready_ids=[]; seen=set()
        for r in rows:
            uid=r['telegram_user_id']
            if uid is None: invalid+=1; continue
            if r['bot'] or r['deleted']: filtered+=1; continue
            if uid in seen: filtered+=1; continue
            seen.add(uid)
            if uid in precheck.target_ids: already+=1; continue
            ready_ids.append(int(r['id']))
        job=Job(None,JobType.MIGRATION,JobState.READY,account_id,source_dataset_id,target_group_id,total=len(ready_ids))
        job_id=self.jobs.create(job); self.jobs.add_items(job_id,ready_ids)
        return job_id,MigrationPlanSummary(total,total-filtered-invalid,already,invalid,len(ready_ids))
