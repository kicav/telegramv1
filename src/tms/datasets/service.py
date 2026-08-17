from __future__ import annotations
from .models import Dataset
from .repository import DatasetRepository

class DatasetService:
    def __init__(self,repo:DatasetRepository)->None:self.repo=repo
    def combine(self,name:str,a_id:int,b_id:int,operation:str)->int:
        op=operation.upper();
        if op not in {'UNION','INTERSECTION','DIFFERENCE'}:raise ValueError('Operation must be UNION, INTERSECTION or DIFFERENCE')
        db=self.repo.db; writer=self.repo.writer
        def tx(conn):
            cur=conn.execute('INSERT INTO datasets(name,source_type,source_reference,status) VALUES(?,?,?,?)',(name or f'{op} {a_id}/{b_id}','MERGED',f'{a_id}:{b_id}:{op}','READY'));new_id=int(cur.lastrowid)
            if op=='UNION': sql='SELECT member_id FROM dataset_members WHERE dataset_id IN (?,?) GROUP BY member_id'; params=(a_id,b_id)
            elif op=='INTERSECTION': sql='SELECT member_id FROM dataset_members WHERE dataset_id IN (?,?) GROUP BY member_id HAVING COUNT(DISTINCT dataset_id)=2'; params=(a_id,b_id)
            else: sql='SELECT member_id FROM dataset_members WHERE dataset_id=? AND member_id NOT IN (SELECT member_id FROM dataset_members WHERE dataset_id=?)'; params=(a_id,b_id)
            ids=[int(r[0]) for r in conn.execute(sql,params).fetchall()]
            conn.executemany('INSERT OR IGNORE INTO dataset_members(dataset_id,member_id) VALUES(?,?)',[(new_id,m) for m in ids])
            for source_id,label in ((a_id,'A'),(b_id,'B')):
                conn.execute('INSERT OR IGNORE INTO dataset_provenance(dataset_id,member_id,source_dataset_id,source_label) SELECT ?,member_id,?,? FROM dataset_members WHERE dataset_id=?',(new_id,source_id,label,source_id))
            conn.execute('UPDATE datasets SET member_count=? WHERE id=?',(len(ids),new_id));return new_id
        return writer.submit(tx,critical=True).result(timeout=30)
