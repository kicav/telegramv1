from __future__ import annotations
from ..core.enums import InviteResultCode
from ..core.errors import DomainError

class ErrorMapper:
    RATE_LIMIT_NAMES=('floodwait','floodpremiumwait','slowmodewait','peerflood','flood')
    PRIVACY_NAMES=('userprivacyrestricted','privacy');ALREADY_NAMES=('useralreadyparticipant','already');NOT_ELIGIBLE_NAMES=('usernotmutualcontact','userchannelsmuch','userchannelstoomuch','botgroupsblocked','botsmuch','botstoomuch','userkicked');INVALID_NAMES=('useridinvalid','inputuserdeactivated','userdeactivated','peeridinvalid','invalid');PERMISSION_NAMES=('chatadminrequired','adminrequired','chatwriteforbidden','userbannedinchannel','forbidden');AUTH_NAMES=('authkeyunregistered','authkeyduplicated','sessionrevoked','sessionexpired','unauthorized','sessionpassword','auth');SERVER_NAMES=('servererror','rpcmcgetfail','timedout')
    def map(self,exc:Exception)->DomainError:
        name=type(exc).__name__.lower();text=str(exc);lower=text.lower();wait=getattr(exc,'seconds',None)
        if wait is None:wait=getattr(exc,'value',None)
        if any(t in name for t in self.RATE_LIMIT_NAMES) or 'flood_wait' in lower or 'too many requests' in lower:
            if wait is None or int(wait or 0)<=0:return DomainError(InviteResultCode.RATE_LIMIT_INDEFINITE,text,None)
            return DomainError(InviteResultCode.RATE_LIMIT,text,max(0,int(wait)))
        if any(t in name for t in self.PRIVACY_NAMES):return DomainError(InviteResultCode.PRIVACY,text)
        if any(t in name for t in self.ALREADY_NAMES):return DomainError(InviteResultCode.ALREADY_MEMBER,text)
        if any(t in name for t in self.NOT_ELIGIBLE_NAMES):return DomainError(InviteResultCode.NOT_ELIGIBLE,text)
        if any(t in name for t in self.PERMISSION_NAMES):return DomainError(InviteResultCode.PERMISSION,text)
        if any(t in name for t in self.AUTH_NAMES):return DomainError(InviteResultCode.AUTH,text)
        if any(t in name for t in self.INVALID_NAMES):return DomainError(InviteResultCode.INVALID_USER,text)
        if isinstance(exc,(ConnectionError,TimeoutError,OSError)):return DomainError(InviteResultCode.NETWORK_TRANSIENT,text)
        if any(t in name for t in self.SERVER_NAMES):return DomainError(InviteResultCode.SERVER_TRANSIENT,text)
        return DomainError(InviteResultCode.UNKNOWN,text)
