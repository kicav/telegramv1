from ..storage.database import Database
from .models import Member


class MemberRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_many(self, members: list[Member]) -> dict[int, int]:
        """Returns telegram_user_id -> local member id. Intended for batch/data-worker use."""
        if not members:
            return {}
        with self.db.connect() as conn:
            conn.executemany(
                """INSERT INTO members(telegram_user_id,username,first_name,last_name,phone,bot,deleted,activity_status,last_seen)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                  username=excluded.username, first_name=excluded.first_name, last_name=excluded.last_name,
                  phone=excluded.phone, bot=excluded.bot, deleted=excluded.deleted,
                  activity_status=excluded.activity_status, last_seen=excluded.last_seen,
                  updated_at=CURRENT_TIMESTAMP""",
                [(m.telegram_user_id,m.username,m.first_name,m.last_name,m.phone,int(m.bot),int(m.deleted),m.activity_status,m.last_seen)
                 for m in members if m.telegram_user_id is not None],
            )
            ids = [m.telegram_user_id for m in members if m.telegram_user_id is not None]
            mapping: dict[int,int] = {}
            if ids:
                chunk=500
                for i in range(0,len(ids),chunk):
                    part=ids[i:i+chunk]
                    marks=','.join('?' for _ in part)
                    for row in conn.execute(f"SELECT id,telegram_user_id FROM members WHERE telegram_user_id IN ({marks})", part):
                        mapping[int(row['telegram_user_id'])]=int(row['id'])
            conn.commit()
            return mapping

    def page(self, offset: int, limit: int, dataset_id: int | None = None) -> tuple[list[Member], int]:
        with self.db.reader() as conn:
            if dataset_id is None:
                total = int(conn.execute("SELECT COUNT(*) FROM members").fetchone()[0])
                rows = conn.execute("SELECT * FROM members ORDER BY id LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            else:
                total = int(conn.execute("SELECT COUNT(*) FROM dataset_members WHERE dataset_id=?", (dataset_id,)).fetchone()[0])
                rows = conn.execute(
                    "SELECT m.* FROM dataset_members dm JOIN members m ON m.id=dm.member_id WHERE dm.dataset_id=? ORDER BY dm.member_id LIMIT ? OFFSET ?",
                    (dataset_id, limit, offset),
                ).fetchall()
        return ([Member(row['telegram_user_id'],row['username'],row['first_name'],row['last_name'],row['phone'],bool(row['bot']),bool(row['deleted']),row['activity_status'],row['last_seen']) for row in rows], total)
