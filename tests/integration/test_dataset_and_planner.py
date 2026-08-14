from pathlib import Path
from tms.storage.database import Database
from tms.members.repository import MemberRepository
from tms.members.models import Member
from tms.datasets.repository import DatasetRepository
from tms.datasets.models import Dataset
from tms.jobs.repository import JobRepository
from tms.migration.planner import MigrationPlanner
from tms.migration.models import PrecheckResult
from tms.core.enums import TargetCoverage

def test_plan_excludes_target_and_invalid(tmp_path:Path):
    db=Database(tmp_path/'x.db');db.initialize();mrepo=MemberRepository(db);mapping=mrepo.upsert_many([Member(1,'a'),Member(2,'b'),Member(3,'c',bot=True)])
    drepo=DatasetRepository(db);did=drepo.create(Dataset(None,'source','FILE'));drepo.add_member_ids(did,list(mapping.values()))
    with db.connect() as c:
        c.execute("INSERT INTO accounts(phone,session_path) VALUES('+1','a.session')");aid=c.execute('SELECT id FROM accounts').fetchone()[0]
        c.execute("INSERT INTO groups(telegram_peer_id,type,title) VALUES(9,'Channel','T')");gid=c.execute('SELECT id FROM groups').fetchone()[0];c.commit()
    jid,summary=MigrationPlanner(db,JobRepository(db)).create_plan(aid,did,gid,PrecheckResult({2},TargetCoverage.COMPLETE))
    assert summary.ready==1 and summary.already_target==1 and summary.filtered==2 and jid>0
