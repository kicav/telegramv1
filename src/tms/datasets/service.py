from .models import Dataset
from .repository import DatasetRepository
from .merge_engine import union
from .difference_engine import difference
from .intersection_engine import intersection


class DatasetService:
    def __init__(self, repo: DatasetRepository) -> None:
        self.repo=repo

    def combine(self, name: str, a_id: int, b_id: int, op: str) -> int:
        a=self.repo.telegram_ids(a_id); b=self.repo.telegram_ids(b_id)
        result={'UNION':union,'INTERSECTION':intersection,'DIFFERENCE':difference}[op](a,b)
        dataset_id=self.repo.create(Dataset(None,name,op,f"{a_id},{b_id}"))
        # Map IDs back to local members in one query.
        with self.repo.db.reader() as conn:
            if result:
                vals=list(result); marks=','.join('?' for _ in vals)
                rows=conn.execute(f"SELECT id FROM members WHERE telegram_user_id IN ({marks})",vals).fetchall()
                self.repo.add_member_ids(dataset_id,[int(r[0]) for r in rows])
        return dataset_id
