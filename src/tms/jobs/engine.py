from ..core.enums import JobState
from .repository import JobRepository
from .state_machine import validate_transition


class JobEngine:
    def __init__(self, repo: JobRepository) -> None: self.repo=repo
    def transition(self, job_id: int, old: JobState, new: JobState) -> None:
        validate_transition(old,new); self.repo.set_state(job_id,new)
