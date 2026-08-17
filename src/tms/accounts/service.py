from __future__ import annotations
from pathlib import Path
import re
from .models import Account
from .repository import AccountRepository

class AccountService:
    def __init__(self, repo:AccountRepository,sessions_dir:Path)->None: self.repo=repo; self.sessions_dir=sessions_dir
    def add(self,phone:str)->Account:
        clean=phone.strip();
        if not re.fullmatch(r'\+?\d{7,16}',clean): raise ValueError('Invalid phone number')
        safe=re.sub(r'\D','',clean); account=Account(None,clean,str(self.sessions_dir/f'{safe}.session')); account.id=self.repo.create(account); return account
    def enable(self,account_id:int,enabled:bool)->None: self.repo.submit_enable(account_id,enabled).result(timeout=10)
    def delete(self,account_id:int)->None:
        account=self.repo.get(account_id)
        self.repo.submit_delete(account_id).result(timeout=10)
        if account:
            p=Path(account.session_path)
            for candidate in (p,Path(str(p)+'-journal'),Path(str(p)+'-wal'),Path(str(p)+'-shm')):
                try: candidate.unlink(missing_ok=True)
                except OSError: pass
