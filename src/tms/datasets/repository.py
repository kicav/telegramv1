from __future__ import annotations
import sqlite3
from ..runtime.db_writer import DBWriter
from ..storage.database import Database
from .models import Dataset

class DatasetRepository:
    def __init__(self,db:Database,writer:DBWriter)->None:self.db=db;self.writer=writer
    def create(self,d:Dataset)->int:
        def op(conn:sqlite3.Connection)->int:
            c=conn.execute('INSERT INTO datasets(name,source_type,source_reference,status,member_count) VALUES(?,?,?,?,?)',(d.name,d.source_type,d.source_reference,d.status,d.member_count));return int(c.lastrowid)
        return self.writer.submit(op,critical=True).result(timeout=10)
    def get(self,dataset_id:int)->Dataset|None:
        with self.db.reader() as conn:r=conn.execute('SELECT * FROM datasets WHERE id=?',(dataset_id,)).fetchone()
        return Dataset(int(r['id']),r['name'],r['source_type'],r['source_reference'],r['status'],int(r['member_count'])) if r else None
    def list_all(self)->list[Dataset]:
        with self.db.reader() as conn:rows=conn.execute('SELECT * FROM datasets ORDER BY id DESC').fetchall()
        return [Dataset(int(r['id']),r['name'],r['source_type'],r['source_reference'],r['status'],int(r['member_count'])) for r in rows]
