from ..storage.database import Database
from .models import Dataset


class DatasetRepository:
    def __init__(self, db: Database) -> None:
        self.db=db

    def create(self, dataset: Dataset) -> int:
        with self.db.connect() as conn:
            cur=conn.execute("INSERT INTO datasets(name,source_type,source_reference,status) VALUES(?,?,?,?)",
                             (dataset.name,dataset.source_type,dataset.source_reference,dataset.status))
            conn.commit(); return int(cur.lastrowid)

    def add_member_ids(self, dataset_id: int, member_ids: list[int], source_group_id: int | None=None) -> None:
        if not member_ids: return
        with self.db.connect() as conn:
            conn.executemany("INSERT OR IGNORE INTO dataset_members(dataset_id,member_id,source_group_id) VALUES(?,?,?)",
                             [(dataset_id,m,source_group_id) for m in member_ids])
            conn.execute("UPDATE datasets SET member_count=(SELECT COUNT(*) FROM dataset_members WHERE dataset_id=?), updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (dataset_id,dataset_id))
            conn.commit()

    def telegram_ids(self, dataset_id: int) -> set[int]:
        with self.db.reader() as conn:
            rows=conn.execute("SELECT m.telegram_user_id FROM dataset_members dm JOIN members m ON m.id=dm.member_id WHERE dm.dataset_id=? AND m.telegram_user_id IS NOT NULL",(dataset_id,)).fetchall()
        return {int(r[0]) for r in rows}

    def member_rows(self, dataset_id: int) -> list[dict]:
        with self.db.reader() as conn:
            rows=conn.execute("SELECT m.* FROM dataset_members dm JOIN members m ON m.id=dm.member_id WHERE dm.dataset_id=? ORDER BY dm.member_id",(dataset_id,)).fetchall()
        return [dict(r) for r in rows]
