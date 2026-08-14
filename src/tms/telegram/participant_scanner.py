from dataclasses import dataclass
from ..core.constants import SCAN_PAGE_LIMIT
from ..core.events import DomainEvent
from ..members.repository import MemberRepository
from ..datasets.repository import DatasetRepository
from ..telegram.peer_cache import PeerCache, CachedPeer


@dataclass(slots=True)
class ScanCheckpoint:
    offset: int = 0
    cancelled: bool = False


class ParticipantScanner:
    def __init__(self, gateway, members: MemberRepository, datasets: DatasetRepository, peers: PeerCache, event_bus) -> None:
        self.gateway=gateway
        self.members=members
        self.datasets=datasets
        self.peers=peers
        self.events=event_bus

    async def scan(self, job_id: int, account_id: int, group, dataset_id: int, checkpoint: ScanCheckpoint | None=None) -> ScanCheckpoint:
        cp=checkpoint or ScanCheckpoint()
        seen: set[int] = set()
        async for page in self.gateway.iter_participant_pages(account_id,group,cp.offset,SCAN_PAGE_LIMIT):
            if cp.cancelled:
                break
            normalized=[m for m in page if m.telegram_user_id is not None and m.telegram_user_id not in seen]
            for member in normalized:
                seen.add(member.telegram_user_id)
                if member.access_hash is not None:
                    self.peers.put(CachedPeer(account_id,member.telegram_user_id,'User',member.access_hash,member.username,None))
            mapping=self.members.upsert_many(normalized)
            self.datasets.add_member_ids(dataset_id,list(mapping.values()),group.local_group_id)
            cp.offset += len(page)
            self.events.publish(DomainEvent('MemberScanProgress',{'job_id':job_id,'offset':cp.offset}))
        return cp
