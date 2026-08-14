from ..groups.models import GroupContext

def can_migrate(group: GroupContext) -> bool:
    return group.can_invite
