from .repository import JobRepository


class CheckpointService:
    def __init__(self, repo: JobRepository) -> None: self.repo=repo
    def save(self, job_id: int, **values) -> None: self.repo.checkpoint(job_id,values)
    def load(self, job_id: int) -> dict: return self.repo.get_checkpoint(job_id)
