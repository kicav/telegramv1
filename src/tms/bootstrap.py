from dataclasses import dataclass
from .config import AppPaths, Settings
from .storage.database import Database
from .runtime.application_runtime import ApplicationRuntime
from .runtime.network_runtime import NetworkRuntime
from .runtime.resource_governor import ResourceGovernor
from .runtime.event_bus import EventBus
from .runtime.event_aggregator import EventAggregator
from .runtime.worker_pool import WorkerPool
from .runtime.db_writer import DBWriter
from .accounts.repository import AccountRepository
from .accounts.service import AccountService
from .groups.repository import GroupRepository
from .members.repository import MemberRepository
from .datasets.repository import DatasetRepository
from .jobs.repository import JobRepository
from .telegram.peer_cache import PeerCache


@dataclass(slots=True)
class AppContext:
    paths: AppPaths
    settings: Settings
    database: Database
    runtime: ApplicationRuntime
    accounts: AccountRepository
    account_service: AccountService
    groups: GroupRepository
    members: MemberRepository
    datasets: DatasetRepository
    jobs: JobRepository
    peers: PeerCache


def bootstrap() -> AppContext:
    paths=AppPaths.discover(); settings=Settings.from_environment(); db=Database(paths.data/'app.db'); db.initialize()
    network=NetworkRuntime(); events=EventBus(); aggregator=EventAggregator(); events.subscribe('*',aggregator.push)
    runtime=ApplicationRuntime(network,ResourceGovernor(),events,aggregator,WorkerPool(2),DBWriter(db))
    accounts=AccountRepository(db)
    return AppContext(paths,settings,db,runtime,accounts,AccountService(accounts,paths.sessions),GroupRepository(db),MemberRepository(db),DatasetRepository(db),JobRepository(db),PeerCache(db))
