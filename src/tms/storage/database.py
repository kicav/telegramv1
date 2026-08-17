from __future__ import annotations
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from .pragmas import PRAGMAS

class Database:
    def __init__(self,path:Path)->None:
        self.path=path;self.path.parent.mkdir(parents=True,exist_ok=True);self._schema=Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    def connect(self)->sqlite3.Connection:
        conn=sqlite3.connect(self.path,timeout=10.0,check_same_thread=False);conn.row_factory=sqlite3.Row
        for p in PRAGMAS:conn.execute(p)
        return conn
    def initialize(self)->None:
        conn=self.connect()
        try:self._schema and conn.executescript(self._schema);self._apply_compatibility_migrations(conn);conn.execute('PRAGMA user_version=3');conn.commit()
        finally:conn.close()
    @staticmethod
    def _add_column(conn,table,name,definition)->None:
        cols={str(r['name']) for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}
        if name not in cols:conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
    @classmethod
    def _apply_compatibility_migrations(cls,conn:sqlite3.Connection)->None:
        cls._add_column(conn,'migration_items','target_state',"TEXT NOT NULL DEFAULT 'KNOWN_ABSENT'")
        cls._add_column(conn,'accounts','connection_state',"TEXT NOT NULL DEFAULT 'DISCONNECTED'")
        cls._add_column(conn,'accounts','operation_state',"TEXT NOT NULL DEFAULT 'IDLE'")
        conn.execute('''CREATE TABLE IF NOT EXISTS account_restrictions(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL,action_type TEXT NOT NULL,restriction_type TEXT NOT NULL,rpc_code INTEGER,exception_name TEXT,request_type TEXT,first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,cleared_at TEXT,FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE)''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_account_restrictions_active ON account_restrictions(account_id,action_type,cleared_at)')
        conn.execute('DELETE FROM migration_items WHERE rowid NOT IN (SELECT MIN(rowid) FROM migration_items GROUP BY job_id,member_id)')
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_migration_items_job_member_unique ON migration_items(job_id,member_id)')
        conn.execute('''DELETE FROM dataset_provenance WHERE rowid NOT IN (SELECT MIN(rowid) FROM dataset_provenance GROUP BY dataset_id,member_id,COALESCE(source_dataset_id,-1),COALESCE(source_group_id,-1),COALESCE(source_label,''))''')
        conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_dataset_provenance_nullsafe_unique ON dataset_provenance(dataset_id,member_id,COALESCE(source_dataset_id,-1),COALESCE(source_group_id,-1),COALESCE(source_label,''))""")
    @contextmanager
    def reader(self)->Iterator[sqlite3.Connection]:
        conn=self.connect()
        try:yield conn
        finally:conn.close()
