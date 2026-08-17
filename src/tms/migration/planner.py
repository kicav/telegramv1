from __future__ import annotations
from ..core.enums import JobState,JobType,TargetCoverage,TargetMemberState
from ..jobs.models import Job
from ..members.filter_spec import FilterSpec
from .models import MigrationPlanSummary,PrecheckResult

class MigrationPlanner:
    def __init__(self,db,jobs)->None:self.db=db;self.jobs=jobs
    def _rows(self,account_id:int,dataset_id:int):
        with self.db.reader() as conn:return conn.execute('''SELECT m.id,m.telegram_user_id,m.username,m.bot,m.deleted,m.activity_status,pc.access_hash FROM dataset_members dm JOIN members m ON m.id=dm.member_id LEFT JOIN peer_cache pc ON pc.account_id=? AND pc.peer_id=m.telegram_user_id WHERE dm.dataset_id=? ORDER BY dm.member_id''',(account_id,dataset_id)).fetchall()
    @staticmethod
    def _valid(row,spec:FilterSpec)->bool:
        if row['telegram_user_id'] is None or row['access_hash'] is None:return False
        if spec.exclude_bot and bool(row['bot']):return False
        if spec.exclude_deleted and bool(row['deleted']):return False
        if spec.username_required and not row['username']:return False
        if spec.activity and str(row['activity_status'] or '') not in spec.activity:return False
        return True
    def _persist(self,account_id,source_dataset_id,target_group_id,ready_items,summary,action):
        job=Job(None,JobType.MIGRATION,JobState.READY,account_id=account_id,source_dataset_id=source_dataset_id,target_group_id=target_group_id,total=len(ready_items));job_id=self.jobs.create(job);self.jobs.submit_add_items(job_id,ready_items).result(timeout=30);self.jobs.submit_checkpoint(job_id,{'action':action}).result(timeout=10);return job_id,summary
    def create_plan(self,account_id:int,source_dataset_id:int,target_group_id:int,precheck:PrecheckResult,filter_spec:FilterSpec|None=None):
        spec=filter_spec or FilterSpec();rows=self._rows(account_id,source_dataset_id);processed=self.jobs.processed_user_ids_for_target(target_group_id);seen=set();invalid=filtered=already=0;items=[]
        for row in rows:
            uid=row['telegram_user_id']
            if uid is None or row['access_hash'] is None:invalid+=1;continue
            uid=int(uid)
            if uid in seen or not self._valid(row,spec) or uid in processed or uid in spec.exclude_processed or uid in spec.exclude_target:filtered+=1;continue
            seen.add(uid)
            if uid in precheck.target_ids:already+=1;continue
            state=TargetMemberState.KNOWN_ABSENT if precheck.coverage==TargetCoverage.COMPLETE else TargetMemberState.UNKNOWN_TARGET_STATE;items.append((int(row['id']),str(state)))
        summary=MigrationPlanSummary(len(rows),filtered,already,invalid,len(items));return self._persist(account_id,source_dataset_id,target_group_id,items,summary,'INVITE')
    def create_remove_plan(self,account_id:int,source_dataset_id:int,target_group_id:int,precheck:PrecheckResult,filter_spec:FilterSpec|None=None):
        if precheck.coverage==TargetCoverage.UNAVAILABLE:raise RuntimeError('Không thể xác minh thành viên group đích để tạo kế hoạch xóa an toàn.')
        spec=filter_spec or FilterSpec();rows=self._rows(account_id,source_dataset_id);seen=set();invalid=filtered=not_in_target=0;items=[]
        for row in rows:
            uid=row['telegram_user_id']
            if uid is None or row['access_hash'] is None:invalid+=1;continue
            uid=int(uid)
            if uid in seen or not self._valid(row,spec):filtered+=1;continue
            seen.add(uid)
            if uid not in precheck.target_ids:not_in_target+=1;continue
            items.append((int(row['id']),str(TargetMemberState.KNOWN_ABSENT)))
        summary=MigrationPlanSummary(len(rows),filtered,not_in_target,invalid,len(items));return self._persist(account_id,source_dataset_id,target_group_id,items,summary,'REMOVE')
