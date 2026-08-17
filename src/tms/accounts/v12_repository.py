from __future__ import annotations
from ..core.enums import AccountState,ConnectionState,OperationState
from .repository import AccountRepository

class V12AccountRepository(AccountRepository):
    @staticmethod
    def _split(state:AccountState):
        if state==AccountState.CONNECTING:return ConnectionState.CONNECTING,OperationState.IDLE
        if state==AccountState.AUTH_REQUIRED:return ConnectionState.AUTH_REQUIRED,OperationState.IDLE
        if state==AccountState.DISABLED:return ConnectionState.DISABLED,OperationState.IDLE
        if state==AccountState.DISCONNECTED:return ConnectionState.DISCONNECTED,OperationState.IDLE
        if state==AccountState.BUSY:return ConnectionState.READY,OperationState.RUNNING
        if state==AccountState.WAITING_SERVER:return ConnectionState.READY,OperationState.WAITING_SERVER
        if state==AccountState.ERROR:return ConnectionState.ERROR,OperationState.PAUSED
        return ConnectionState.READY,OperationState.IDLE
    def submit_set_state(self,account_id:int,state:AccountState,error:str|None=None):
        connection,operation=self._split(state);return self.writer.execute('UPDATE accounts SET status=?,connection_state=?,operation_state=?,last_error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(str(state),str(connection),str(operation),error,account_id),critical=True)
    def submit_restriction(self,account_id:int,action_type:str,restriction_type:str,rpc_code:int|None=None,exception_name:str|None=None,request_type:str|None=None):
        def op(conn):
            row=conn.execute('SELECT id FROM account_restrictions WHERE account_id=? AND action_type=? AND restriction_type=? AND cleared_at IS NULL ORDER BY id DESC LIMIT 1',(account_id,action_type,restriction_type)).fetchone()
            if row:conn.execute('UPDATE account_restrictions SET last_seen_at=CURRENT_TIMESTAMP,rpc_code=?,exception_name=?,request_type=? WHERE id=?',(rpc_code,exception_name,request_type,int(row[0])))
            else:conn.execute('INSERT INTO account_restrictions(account_id,action_type,restriction_type,rpc_code,exception_name,request_type) VALUES(?,?,?,?,?,?)',(account_id,action_type,restriction_type,rpc_code,exception_name,request_type))
        return self.writer.submit(op,critical=True)
    def active_restrictions(self,account_id:int):
        with self.db.reader() as conn:rows=conn.execute('SELECT * FROM account_restrictions WHERE account_id=? AND cleared_at IS NULL ORDER BY id DESC',(account_id,)).fetchall()
        return [dict(r) for r in rows]
