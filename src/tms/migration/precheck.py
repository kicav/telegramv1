from ..core.enums import TargetCoverage
from .models import PrecheckResult


class TargetPrecheck:
    async def run(self, gateway, account_id: int, group, page_limit: int = 200) -> PrecheckResult:
        ids:set[int]=set(); coverage=TargetCoverage.COMPLETE
        try:
            async for page in gateway.iter_participant_pages(account_id,group,0,page_limit):
                ids.update(m.telegram_user_id for m in page if m.telegram_user_id is not None)
        except Exception:
            coverage=TargetCoverage.PARTIAL if ids else TargetCoverage.UNAVAILABLE
        return PrecheckResult(ids,coverage)
