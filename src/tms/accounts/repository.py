from __future__ import annotations
import sqlite3
from concurrent.futures import Future
from ..core.enums import AccountState, JobState
from ..runtime.db_writer import DBWriter
from ..storage.database import Database
from .models import Account

_TERMINAL={str(JobState.COMPLETED),str(JobState.COMPLETED_WITH_ERRORS),str(JobState.FAILED),str(JobState.CANCELLED)}
class AccountRepository:
    def __init__(self, db: Database, writer: DBWriter) -> None: self.db=db; self.writer=writer
    @staticmethod
    def _row(row) -> Account:
        return Account(int(row['id']),row['phone'],row['session_path'],row['telegram_user_id'],row['username'],row['display_name'],AccountState(row['status']),bool(row['enabled']),row['last_error'])
    def create(self, account: Account) -> int:
        def op(conn: sqlite3.Connection) -> int:
            cur=conn.execute('INSERT INTO accounts(phone,session_path,status,enabled) VALUES(?,?,?,?)',(account.phone,account.session_path,str(account.status),int(account.enabled))); return int(cur.lastrowid)
        return self.writer.submit(op,critical=True).result(timeout=10)
    def get(self, account_id: int) -> Account | None:
        with self.db.reader() as conn: row=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
        return self._row(row) if row else None
    def list_all(self) -> list[Account]:
        with self.db.reader() as conn: rows=conn.execute('SELECT * FROM accounts ORDER BY id').fetchall()
        return [self._row(r) for r in rows]
    def submit_set_state(self, account_id:int,state:AccountState,error:str|None=None)->Future:
        return self.writer.execute('UPDATE accounts SET status=?,last_error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(str(state),error,account_id),critical=True)
    def submit_update_identity(self,account_id:int,user_id:int|None,username:str|None,display_name:str|None)->Future:
        return self.writer.execute('UPDATE accounts SET telegram_user_id=?,username=?,display_name=?,status=?,last_error=NULL,last_connected_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?',(user_id,username,display_name,str(AccountState.READY),account_id),critical=True)
    def submit_enable(self,account_id:int,enabled:bool)->Future:
        state=AccountState.DISCONNECTED if enabled else AccountState.DISABLED
        return self.writer.execute('UPDATE accounts SET enabled=?,status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(int(enabled),str(state),account_id),critical=True)
    def submit_delete(self,account_id:int)->Future:
        def op(conn:sqlite3.Connection)->None:
            rows=conn.execute('SELECT state FROM jobs WHERE account_id=?',(account_id,)).fetchall()
            if any(str(r['state']) not in _TERMINAL for r in rows): raise RuntimeError('Account has non-terminal jobs')
            conn.execute('UPDATE jobs SET account_id=NULL WHERE account_id=?',(account_id,)); conn.execute('DELETE FROM accounts WHERE id=?',(account_id,))
        return self.writer.submit(op,critical=True)
