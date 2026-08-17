from __future__ import annotations
from dataclasses import dataclass
import json,sqlite3
from concurrent.futures import Future
from ..core.enums import JobState,MigrationItemState
from ..runtime.db_writer import DBWriter
from ..storage.database import Database
from .models import Job

@dataclass(slots=True)
class ItemUpdate:
    ordinal:int; state:MigrationItemState; attempts:int; error_code:str|None=None; error_text:str|None=None
class JobRepository:
    def __init__(self,db:Database,writer:DBWriter)->None:self.db=db;self.writer=writer
    def create(self,j:Job)->int:
        def op(conn:sqlite3.Connection)->int:
            c=conn.execute('INSERT INTO jobs(job_type,state,account_id,source_dataset_id,target_group_id,total) VALUES(?,?,?,?,?,?)',(str(j.job_type),str(j.state),j.account_id,j.source_dataset_id,j.target_group_id,j.total));return int(c.lastrowid)
        return self.writer.submit(op,critical=True).result(timeout=10)
    def get(self,job_id:int):
        with self.db.reader() as conn:r=conn.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        return dict(r) if r else None
    def list_recent(self,limit:int=200):
        with self.db.reader() as conn:rows=conn.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT ?',(max(1,min(1000,limit)),)).fetchall()
        return [dict(r) for r in rows]
    def has_nonterminal_jobs(self,account_id:int)->bool:
        with self.db.reader() as conn:r=conn.execute("SELECT 1 FROM jobs WHERE account_id=? AND state NOT IN ('COMPLETED','COMPLETED_WITH_ERRORS','FAILED','CANCELLED') LIMIT 1",(account_id,)).fetchone()
        return bool(r)
    def account_waiting_until(self,account_id:int)->str|None:
        with self.db.reader() as conn:r=conn.execute("SELECT waiting_until FROM jobs WHERE account_id=? AND state='WAITING_SERVER' AND waiting_until IS NOT NULL ORDER BY waiting_until DESC LIMIT 1",(account_id,)).fetchone()
        return str(r[0]) if r and r[0] else None
    def submit_set_state(self,job_id:int,state:JobState,waiting_until:str|None=None,checkpoint:dict|None=None,*,clear_waiting:bool=False)->Future:
        def op(conn):
            sets=['state=?','updated_at=CURRENT_TIMESTAMP'];params=[str(state)]
            if waiting_until is not None or clear_waiting:sets.append('waiting_until=?');params.append(waiting_until)
            if checkpoint is not None:sets.append('checkpoint_json=?');params.append(json.dumps(checkpoint))
            if state==JobState.RUNNING:sets.append('started_at=COALESCE(started_at,CURRENT_TIMESTAMP)')
            if state in {JobState.COMPLETED,JobState.COMPLETED_WITH_ERRORS,JobState.FAILED,JobState.CANCELLED}:sets.append('finished_at=CURRENT_TIMESTAMP')
            params.append(job_id);conn.execute(f"UPDATE jobs SET {','.join(sets)} WHERE id=?",tuple(params))
        return self.writer.submit(op,critical=True)
    def submit_checkpoint(self,job_id:int,checkpoint:dict)->Future:
        return self.writer.execute('UPDATE jobs SET checkpoint_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(json.dumps(checkpoint),job_id),critical=True)
    def submit_add_items(self,job_id:int,items:list[tuple[int,str]])->Future:
        def op(conn):
            conn.executemany('INSERT OR IGNORE INTO migration_items(job_id,ordinal,member_id,target_state) VALUES(?,?,?,?)',[(job_id,i,m,s) for i,(m,s) in enumerate(items)]);conn.execute('UPDATE jobs SET total=? WHERE id=?',(len(items),job_id))
        return self.writer.submit(op,critical=True)
    def pending_chunk(self,job_id:int,account_id:int,last_ordinal:int,limit:int):
        with self.db.reader() as conn:rows=conn.execute('''SELECT mi.*,m.telegram_user_id,m.username,m.first_name,m.last_name,m.phone,m.bot,m.deleted,m.activity_status,m.last_seen,pc.access_hash account_access_hash FROM migration_items mi JOIN members m ON m.id=mi.member_id LEFT JOIN peer_cache pc ON pc.account_id=? AND pc.peer_id=m.telegram_user_id WHERE mi.job_id=? AND mi.ordinal>? AND mi.state IN ('READY','RETRY') ORDER BY mi.ordinal LIMIT ?''',(account_id,job_id,last_ordinal,limit)).fetchall()
        return [dict(r) for r in rows]
    def submit_update_items_batch(self,job_id:int,updates:list[ItemUpdate],checkpoint:dict|None=None)->Future:
        def op(conn):
            for u in updates:conn.execute('UPDATE migration_items SET state=?,attempt_count=?,last_error_code=?,last_error_text=?,processed_at=CURRENT_TIMESTAMP WHERE job_id=? AND ordinal=?',(str(u.state),u.attempts,u.error_code,u.error_text,job_id,u.ordinal))
            counts=conn.execute("SELECT SUM(state='SUCCESS') success,SUM(state='SKIPPED') skipped,SUM(state='FAILED') failed FROM migration_items WHERE job_id=?",(job_id,)).fetchone();success=int(counts['success'] or 0);skipped=int(counts['skipped'] or 0);failed=int(counts['failed'] or 0);processed=success+skipped+failed
            conn.execute('UPDATE jobs SET processed=?,success=?,skipped=?,failed=?,checkpoint_json=COALESCE(?,checkpoint_json),updated_at=CURRENT_TIMESTAMP WHERE id=?',(processed,success,skipped,failed,json.dumps(checkpoint) if checkpoint else None,job_id))
        return self.writer.submit(op)
    def submit_mark_retry(self,job_id:int,ordinal:int,attempts:int,error_code:str|None,error_text:str|None,next_retry_at:str|None=None)->Future:
        return self.writer.execute("UPDATE migration_items SET state='RETRY',attempt_count=?,last_error_code=?,last_error_text=?,next_retry_at=? WHERE job_id=? AND ordinal=?",(attempts,error_code,error_text,next_retry_at,job_id,ordinal),critical=True)
    def submit_event(self,job_id:int,level:str,event_code:str,message:str|None=None,member_id:int|None=None,critical:bool=False)->Future:
        return self.writer.execute('INSERT INTO job_events(job_id,level,event_code,member_id,message) VALUES(?,?,?,?,?)',(job_id,level,event_code,member_id,message),critical=critical)
    def summary(self,job_id:int)->dict:
        row=self.get(job_id) or {};return {k:int(row.get(k,0) or 0) for k in ('total','processed','success','skipped','failed')}
    def get_checkpoint(self,job_id:int)->dict:
        row=self.get(job_id);raw=row.get('checkpoint_json') if row else None
        try:return json.loads(raw) if raw else {}
        except Exception:return {}
    def recoverable(self)->list[int]:
        with self.db.reader() as conn:rows=conn.execute("SELECT id FROM jobs WHERE state IN ('RUNNING','WAITING_SERVER','PAUSED','RATE_LIMITED') ORDER BY id").fetchall()
        return [int(r[0]) for r in rows]
    def processed_user_ids_for_target(self,target_group_id:int)->set[int]:
        with self.db.reader() as conn:rows=conn.execute("SELECT DISTINCT m.telegram_user_id FROM jobs j JOIN migration_items mi ON mi.job_id=j.id JOIN members m ON m.id=mi.member_id WHERE j.target_group_id=? AND mi.state='SUCCESS' AND m.telegram_user_id IS NOT NULL",(target_group_id,)).fetchall()
        return {int(r[0]) for r in rows}
