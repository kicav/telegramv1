from __future__ import annotations

from ..groups.models import GroupContext


def can_scan(group: GroupContext) -> bool:
    return group.is_member and group.can_read


def can_migrate(group: GroupContext) -> bool:
    return group.is_member and group.can_invite
