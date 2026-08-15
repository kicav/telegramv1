from __future__ import annotations

from ..core.enums import InviteResultCode
from ..core.errors import DomainError


class ErrorMapper:
    """Maps Telethon/RPC/network exceptions into stable migration policy categories."""

    RATE_LIMIT_NAMES = (
        "floodwait",
        "floodpremiumwait",
        "slowmodewait",
        "peerflood",
    )
    PRIVACY_NAMES = (
        "userprivacyrestricted",
        "privacy",
    )
    ALREADY_NAMES = (
        "useralreadyparticipant",
        "already",
    )
    NOT_ELIGIBLE_NAMES = (
        "usernotmutualcontact",
        "userchannelsmuch",
        "userchannelstoomuch",
        "botgroupsblocked",
        "botsmuch",
        "botstoomuch",
        "userkicked",
    )
    INVALID_NAMES = (
        "useridinvalid",
        "inputuserdeactivated",
        "userdeactivated",
        "peeridinvalid",
        "invalid",
    )
    PERMISSION_NAMES = (
        "chatadminrequired",
        "adminrequired",
        "chatwriteforbidden",
        "userbannedinchannel",
        "forbidden",
    )
    AUTH_NAMES = (
        "authkeyunregistered",
        "authkeyduplicated",
        "sessionrevoked",
        "sessionexpired",
        "unauthorized",
        "sessionpassword",
        "auth",
    )
    SERVER_NAMES = (
        "servererror",
        "rpcmcgetfail",
        "timedout",
    )

    def map(self, exc: Exception) -> DomainError:
        name = type(exc).__name__.lower()
        text = str(exc)
        lower_text = text.lower()
        wait = getattr(exc, "seconds", None)
        if wait is None:
            wait = getattr(exc, "value", None)

        if any(token in name for token in self.RATE_LIMIT_NAMES) or "flood_wait" in lower_text:
            wait_seconds = max(0, int(wait or 0))
            # Some Telegram anti-spam rate errors do not expose a duration. Never enter
            # a zero-delay retry loop; pause conservatively and persist the wait.
            if wait_seconds == 0:
                wait_seconds = 60 if "peerflood" in name else 1
            return DomainError(InviteResultCode.RATE_LIMIT, text, wait_seconds)
        if any(token in name for token in self.PRIVACY_NAMES):
            return DomainError(InviteResultCode.PRIVACY, text)
        if any(token in name for token in self.ALREADY_NAMES):
            return DomainError(InviteResultCode.ALREADY_MEMBER, text)
        if any(token in name for token in self.NOT_ELIGIBLE_NAMES):
            return DomainError(InviteResultCode.NOT_ELIGIBLE, text)
        if any(token in name for token in self.PERMISSION_NAMES):
            return DomainError(InviteResultCode.PERMISSION, text)
        if any(token in name for token in self.AUTH_NAMES):
            return DomainError(InviteResultCode.AUTH, text)
        if any(token in name for token in self.INVALID_NAMES):
            return DomainError(InviteResultCode.INVALID_USER, text)
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            return DomainError(InviteResultCode.NETWORK_TRANSIENT, text)
        if any(token in name for token in self.SERVER_NAMES):
            return DomainError(InviteResultCode.SERVER_TRANSIENT, text)
        return DomainError(InviteResultCode.UNKNOWN, text)
