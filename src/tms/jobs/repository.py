import json
from ..storage.database import Database
from ..core.enums import JobState, JobType, MigrationItemState
from .models import Job


class JobRepository:
    def __init__(self, db: Database) -> None: self.db=db

    def create(self, job: Job) -> int:
        with self.db.connect() as conn:
            cur=conn.execute("INSERT INTO jobs(job_type,state,account_id,source_dataset_id,target_group_id,total) VALUES(?,?,?,?,?,?)",
                (job.job_type,job.state,job.account_id,job.source_dataset_id,job.target_group_id,job.total)); conn.commit(); return int(cur.lastrowid)

    def set_state(self, job_id: int, state: JobState, waiting_until: str | None=None) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE jobs SET state=?,waiting_until=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(state,waiting_until,job_id)); conn.commit()

    def checkpoint(self, job_id: int, data: dict) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE jobs SET checkpoint_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(data),job_id)); conn.commit()

    def get_checkpoint(self, job_id: int) -> dict:
        with self.db.reader() as conn: row=conn.execute("SELECT checkpoint_json FROM jobs WHERE id=?",(job_id,)).fetchone()
        return json.loads(row[0]) if row and row[0] else {}

    def add_items(self, job_id: int, member_ids: list[int]) -> None:
        with self.db.connect() as conn:
            conn.executemany("INSERT INTO migration_items(job_id,ordinal,member_id,state) VALUES(?,?,?,?)",
                             [(job_id,i,m,MigrationItemState.READY) for i,m in enumerate(member_ids)])
            conn.execute("UPDATE jobs SET total=? WHERE id=?",(len(member_ids),job_id)); conn.commit()

    def pending_chunk(self, job_id: int, after_ordinal: int, limit: int) -> list[dict]:
        with self.db.reader() as conn:
            rows=conn.execute("""SELECT mi.ordinal,mi.member_id,m.* FROM migration_items mi JOIN members m ON m.id=mi.member_id
              WHERE mi.job_id=? AND mi.ordinal>? AND mi.state IN ('READY','RETRY') ORDER BY mi.ordinal LIMIT ?""",(job_id,after_ordinal,limit)).fetchall()
        return [dict(r) for r in rows]

    def update_item(self, job_id: int, ordinal: int, state: MigrationItemState, attempts: int, code: str | None, text: str | None) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE migration_items SET state=?,attempt_count=?,last_error_code=?,last_error_text=?,processed_at=CURRENT_TIMESTAMP WHERE job_id=? AND ordinal=?",
                         (state,attempts,code,text,job_id,ordinal))
            conn.execute("""UPDATE jobs SET processed=(SELECT COUNT(*) FROM migration_items WHERE job_id=? AND state IN ('SUCCESS','SKIPPED','FAILED')),
            success=(SELECT COUNT(*) FROM migration_items WHERE job_id=? AND state='SUCCESS'),
            skipped=(SELECT COUNT(*) FROM migration_items WHERE job_id=? AND state='SKIPPED'),
            failed=(SELECT COUNT(*) FROM migration_items WHERE job_id=? AND state='FAILED'),updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                         (job_id,job_id,job_id,job_id,job_id)); conn.commit()

    def recoverable(self) -> list[int]:
        with self.db.reader() as conn:
            rows=conn.execute("SELECT id FROM jobs WHERE state IN ('RUNNING','WAITING_SERVER','PAUSED') ORDER BY id").fetchall()
        return [int(r[0]) for r in rows]
