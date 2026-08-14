from ..storage.database import Database
from .models import Account
from ..core.enums import AccountState


class AccountRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, account: Account) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO accounts(phone,session_path,status,enabled) VALUES(?,?,?,?)",
                (account.phone, account.session_path, account.status, int(account.enabled)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_all(self) -> list[Account]:
        with self.db.reader() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        return [Account(
            id=row["id"], phone=row["phone"], session_path=row["session_path"],
            telegram_user_id=row["telegram_user_id"], username=row["username"],
            display_name=row["display_name"], status=AccountState(row["status"]),
            enabled=bool(row["enabled"])
        ) for row in rows]

    def set_state(self, account_id: int, state: AccountState, error: str | None = None) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE accounts SET status=?, last_error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (state, error, account_id),
            )
            conn.commit()

    def delete(self, account_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
            conn.commit()
