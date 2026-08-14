from pathlib import Path
from tms.storage.database import Database
from tms.jobs.repository import JobRepository
from tms.jobs.models import Job
from tms.core.enums import JobType,JobState

def test_recovery_is_persistent(tmp_path:Path):
    db=Database(tmp_path/'r.db');db.initialize();repo=JobRepository(db);jid=repo.create(Job(None,JobType.MIGRATION,JobState.RUNNING));repo.checkpoint(jid,{'last_ordinal':1519});assert jid in repo.recoverable();assert repo.get_checkpoint(jid)['last_ordinal']==1519
