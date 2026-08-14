from ..storage.database import Database
from .models import GroupContext


class GroupRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, group: GroupContext) -> int:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO groups(telegram_peer_id,type,username,title) VALUES(?,?,?,?)
                ON CONFLICT(telegram_peer_id) DO UPDATE SET type=excluded.type, username=excluded.username,
                title=excluded.title, updated_at=CURRENT_TIMESTAMP""",
                (group.telegram_id, group.type, group.username, group.title),
            )
            row=conn.execute("SELECT id FROM groups WHERE telegram_peer_id=?", (group.telegram_id,)).fetchone()
            conn.commit()
            return int(row[0])
