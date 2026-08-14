import asyncio
from pathlib import Path
from tms.storage.database import Database
from tms.accounts.repository import AccountRepository
from tms.accounts.models import Account
from tms.members.repository import MemberRepository
from tms.members.models import Member
from tms.datasets.repository import DatasetRepository
from tms.datasets.models import Dataset
from tms.groups.repository import GroupRepository
from tms.groups.models import GroupContext
from tms.jobs.repository import JobRepository
from tms.migration.planner import MigrationPlanner
from tms.migration.models import PrecheckResult
from tms.migration.executor import MigrationExecutor
from tms.migration.scheduler import InviteScheduler
from tms.runtime.resource_governor import ResourceGovernor
from tms.runtime.event_bus import EventBus
from tms.telegram.fake_gateway import FakeTelegramGateway
from tms.core.clock import FakeClock
from tms.core.enums import TargetCoverage

def test_executor_one_candidate_per_invite_and_no_target_reresolve(tmp_path:Path):
    async def run():
        db=Database(tmp_path/'m.db');db.initialize();accounts=AccountRepository(db);aid=accounts.create(Account(None,'+1',str(tmp_path/'a.session')))
        mrepo=MemberRepository(db);mapping=mrepo.upsert_many([Member(1,'a'),Member(2,'b')]);drepo=DatasetRepository(db);did=drepo.create(Dataset(None,'s','FILE'));drepo.add_member_ids(did,list(mapping.values()))
        group=GroupContext(99,9,'target','target','Channel',True,True,True,True,True);gid=GroupRepository(db).upsert(group);group.local_group_id=gid
        jobs=JobRepository(db);jid,_=MigrationPlanner(db,jobs).create_plan(aid,did,gid,PrecheckResult(set(),TargetCoverage.COMPLETE));fake=FakeTelegramGateway();clock=FakeClock();ex=MigrationExecutor(fake,jobs,accounts,ResourceGovernor(),EventBus(),InviteScheduler(5,clock));await ex.run(jid,aid,group)
        assert fake.invites==[1,2];assert fake.resolve_calls==0;assert clock.now==5
    asyncio.run(run())
