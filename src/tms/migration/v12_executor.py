from __future__ import annotations
from ..core.enums import JobState
from .executor import MigrationExecutor

class V12MigrationExecutor(MigrationExecutor):
    async def _attempt(self,job_id,account_id,target,candidate):
        result=await super()._attempt(job_id,account_id,target,candidate)
        row=self.jobs.get(job_id)
        if row and str(row.get('state'))==str(JobState.RATE_LIMITED) and hasattr(self.accounts,'submit_restriction'):
            await self._await_write(self.accounts.submit_restriction(account_id,self.action,'RATE_LIMIT_INDEFINITE',420,'RateLimit','InviteToChannelRequest' if self.action=='INVITE' else 'EditBannedRequest'))
        return result
