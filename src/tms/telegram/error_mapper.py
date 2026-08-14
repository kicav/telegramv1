from ..core.errors import DomainError
from ..core.enums import InviteResultCode


class ErrorMapper:
    def map(self, exc: Exception) -> DomainError:
        name=type(exc).__name__.lower()
        text=str(exc)
        wait=getattr(exc, "seconds", None) or getattr(exc, "value", None)
        if "floodwait" in name or "flood_wait" in text.lower():
            return DomainError(InviteResultCode.RATE_LIMIT, text, int(wait or 0))
        if "privacy" in name:
            return DomainError(InviteResultCode.PRIVACY, text)
        if "already" in name or "useralreadyparticipant" in name:
            return DomainError(InviteResultCode.ALREADY_MEMBER, text)
        if "adminrequired" in name or "chatadminrequired" in name or "forbidden" in name:
            return DomainError(InviteResultCode.PERMISSION, text)
        if "auth" in name or "sessionpassword" in name or "unauthorized" in name:
            return DomainError(InviteResultCode.AUTH, text)
        if "invalid" in name or "deactivated" in name:
            return DomainError(InviteResultCode.INVALID_USER, text)
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return DomainError(InviteResultCode.NETWORK_TRANSIENT, text)
        if "server" in name or "rpcmcgetfail" in name:
            return DomainError(InviteResultCode.SERVER_TRANSIENT, text)
        return DomainError(InviteResultCode.UNKNOWN, text)
