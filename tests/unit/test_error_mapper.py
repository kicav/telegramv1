from tms.telegram.error_mapper import ErrorMapper
from tms.core.enums import InviteResultCode
class FloodWaitError(Exception):
    seconds=42
class UserPrivacyRestrictedError(Exception): pass
class UserAlreadyParticipantError(Exception): pass

def test_error_mapping():
    m=ErrorMapper();assert m.map(FloodWaitError('wait')).code==InviteResultCode.RATE_LIMIT;assert m.map(FloodWaitError('wait')).wait_seconds==42
    assert m.map(UserPrivacyRestrictedError()).code==InviteResultCode.PRIVACY
    assert m.map(UserAlreadyParticipantError()).code==InviteResultCode.ALREADY_MEMBER


class PeerFloodError(Exception):
    pass


def test_rate_limit_without_server_duration_never_busy_loops():
    mapped = ErrorMapper().map(PeerFloodError("restricted"))
    assert mapped.code == InviteResultCode.RATE_LIMIT
    assert mapped.wait_seconds >= 1
