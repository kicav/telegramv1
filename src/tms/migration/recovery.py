from ..jobs.repository import JobRepository


class RecoveryService:
    def __init__(self,jobs:JobRepository) -> None: self.jobs=jobs
    def recoverable_jobs(self) -> list[int]: return self.jobs.recoverable()
