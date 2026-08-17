from __future__ import annotations
from dataclasses import dataclass
from ..core.enums import JobState,JobType

@dataclass(slots=True)
class Job:
    id:int|None
    job_type:JobType
    state:JobState
    account_id:int|None=None
    source_dataset_id:int|None=None
    target_group_id:int|None=None
    total:int=0
