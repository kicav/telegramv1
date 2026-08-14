from pathlib import Path
from .models import Account
from .repository import AccountRepository
from ..core.enums import AccountState


class AccountService:
    def __init__(self, repo: AccountRepository, sessions_dir: Path) -> None:
        self.repo = repo
        self.sessions_dir = sessions_dir

    def add(self, phone: str) -> Account:
        safe = "".join(c for c in phone if c.isdigit()) or "account"
        session = self.sessions_dir / f"account_{safe}.session"
        account = Account(id=None, phone=phone, session_path=str(session))
        account.id = self.repo.create(account)
        return account

    def enable(self, account_id: int, enabled: bool) -> None:
        self.repo.set_state(account_id, AccountState.DISCONNECTED if enabled else AccountState.DISABLED)
