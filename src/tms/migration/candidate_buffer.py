from collections import deque
from ..core.constants import CANDIDATE_PREFETCH_MIN, CANDIDATE_PREFETCH_MAX
from ..jobs.repository import JobRepository
from ..members.models import Member


class CandidateBuffer:
    def __init__(self, jobs: JobRepository, job_id: int, chunk_size: int = CANDIDATE_PREFETCH_MIN) -> None:
        self.jobs=jobs; self.job_id=job_id; self.chunk_size=max(CANDIDATE_PREFETCH_MIN,min(CANDIDATE_PREFETCH_MAX,chunk_size)); self.queue=deque(); self.last_loaded=-1

    def _fill(self) -> None:
        if self.queue: return
        rows=self.jobs.pending_chunk(self.job_id,self.last_loaded,self.chunk_size)
        for r in rows:
            self.queue.append((int(r['ordinal']),Member(r['telegram_user_id'],r['username'],r['first_name'],r['last_name'],r['phone'],bool(r['bot']),bool(r['deleted']),r['activity_status'],r['last_seen'])))
        if rows: self.last_loaded=int(rows[-1]['ordinal'])

    def pop(self):
        self._fill(); return self.queue.popleft() if self.queue else None
