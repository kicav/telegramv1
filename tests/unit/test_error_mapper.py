from tms.telegram.error_mapper import ErrorMapper
from tms.core.enums import InviteResultCode
class FloodWaitError(Exception):seconds=42
class UserPrivacyRestrictedError(Exception):pass
class UserAlreadyParticipantError(Exception):pass
class PeerFloodError(Exception):pass

def test_error_mapping():
    m=ErrorMapper();x=m.map(FloodWaitError('wait'));assert x.code==InviteResultCode.RATE_LIMIT and x.wait_seconds==42
    assert m.map(UserPrivacyRestrictedError()).code==InviteResultCode.PRIVACY
    assert m.map(UserAlreadyParticipantError()).code==InviteResultCode.ALREADY_MEMBER
def test_rate_limit_without_server_duration_is_indefinite():
    mapped=ErrorMapper().map(PeerFloodError('restricted'));assert mapped.code==InviteResultCode.RATE_LIMIT_INDEFINITE;assert mapped.wait_seconds is None
