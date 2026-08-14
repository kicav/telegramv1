from pathlib import Path
from tms.storage.database import Database
from tms.accounts.repository import AccountRepository
from tms.accounts.models import Account

def test_schema_and_account(tmp_path:Path):
    db=Database(tmp_path/'app.db');db.initialize();repo=AccountRepository(db);i=repo.create(Account(None,'+84123',str(tmp_path/'a.session')));assert i>0;assert repo.list_all()[0].phone=='+84123'
    with db.reader() as c: assert c.execute('PRAGMA journal_mode').fetchone()[0].lower()=='wal'
