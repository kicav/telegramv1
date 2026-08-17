from __future__ import annotations
from .repository import JobRepository

class V12JobRepository(JobRepository):
    def account_waiting_until(self,account_id:int)->str|None:
        with self.db.reader() as conn:
            row=conn.execute("SELECT waiting_until FROM jobs WHERE account_id=? AND state='WAITING_SERVER' AND waiting_until IS NOT NULL ORDER BY waiting_until DESC LIMIT 1",(account_id,)).fetchone()
        return str(row[0]) if row and row[0] else None
