from __future__ import annotations
from ..core.enums import JobState
_TERMINAL={JobState.COMPLETED,JobState.COMPLETED_WITH_ERRORS,JobState.FAILED,JobState.CANCELLED}
def validate_transition(old:JobState,new:JobState)->None:
    if old in _TERMINAL and new!=old: raise ValueError(f'Invalid terminal transition {old} -> {new}')
