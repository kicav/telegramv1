from __future__ import annotations
import sqlite3
from ..runtime.db_writer import DBWriter
from ..storage.database import Database
from .models import GroupContext

class GroupRepository:
    def __init__(self,db:Database,writer:DBWriter)->None:self.db=db;self.writer=writer
    def submit_upsert(self,g:GroupContext):
        def op(conn:sqlite3.Connection)->int:
            conn.execute('INSERT INTO groups(telegram_peer_id,type,username,title) VALUES(?,?,?,?) ON CONFLICT(telegram_peer_id) DO UPDATE SET type=excluded.type,username=excluded.username,title=excluded.title,updated_at=CURRENT_TIMESTAMP',(g.telegram_id,g.type,g.username,g.title))
            return int(conn.execute('SELECT id FROM groups WHERE telegram_peer_id=?',(g.telegram_id,)).fetchone()[0])
        return self.writer.submit(op)
    def upsert(self,g:GroupContext)->int:return self.submit_upsert(g).result(timeout=10)
    def get(self,local_id:int,account_id:int|None=None)->GroupContext|None:
        with self.db.reader() as conn:
            if account_id is None:r=conn.execute('SELECT g.*,NULL access_hash FROM groups g WHERE g.id=?',(local_id,)).fetchone()
            else:r=conn.execute('SELECT g.*,pc.access_hash FROM groups g LEFT JOIN peer_cache pc ON pc.account_id=? AND pc.peer_id=g.telegram_peer_id WHERE g.id=?',(account_id,local_id)).fetchone()
        if not r:return None
        return GroupContext(int(r['telegram_peer_id']),int(r['access_hash']) if r['access_hash'] is not None else None,r['title'],r['username'],r['type'],local_group_id=int(r['id']))
