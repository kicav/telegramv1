from dataclasses import dataclass
from ..core.enums import TargetCoverage


@dataclass(slots=True)
class PrecheckResult:
    target_ids: set[int]
    coverage: TargetCoverage


@dataclass(slots=True)
class MigrationPlanSummary:
    total_source: int
    filtered: int
    already_target: int
    invalid: int
    ready: int
