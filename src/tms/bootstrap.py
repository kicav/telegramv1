from __future__ import annotations
from dataclasses import dataclass
from types import MethodType
from .accounts.v12_repository import V12AccountRepository
from .accounts.service import AccountService
from .config import AppPaths,Settings
from .datasets.repository import DatasetRepository
from .datasets.service import DatasetService
from .groups.repository import GroupRepository
from .groups.service import GroupService
from .import_export.service import ImportExportService
from .jobs.v12_repository import V12JobRepository
from .members.repository import MemberRepository
from .migration.v12_executor import V12MigrationExecutor
from .migration.planner import MigrationPlanner
from .migration.precheck import TargetPrecheck
from .migration.recovery import RecoveryService
from .migration.scheduler import InviteScheduler
from .runtime.application_runtime import ApplicationRuntime
from .runtime.command_bus import CommandBus
from .runtime.command_handlers import CommandHandlers
from .runtime.db_writer import DBWriter
from .runtime.event_aggregator import EventAggregator
from .runtime.event_bus import EventBus
from .runtime.network_runtime import NetworkRuntime
from .runtime.performance_monitor import PerformanceMonitor
from .runtime.resource_governor import ResourceGovernor
from .runtime.state_store import StateStore
from .runtime.worker_pool import WorkerPool
from .storage.database import Database
from .telegram.auth_service import AuthService
from .telegram.client_manager import ClientManager
from .telegram.member_action_gateway import MemberActionGateway
from .telegram.participant_scanner import ParticipantScanner
from .telegram.peer_cache import PeerCache
from .utilities.group_membership import GroupMembershipUtility
from .core.events import DomainEvent

@dataclass(slots=True)
class AppContext:
    paths:AppPaths;settings:Settings;database:Database;runtime:ApplicationRuntime;commands:CommandBus;state:StateStore;metrics:PerformanceMonitor;accounts:V12AccountRepository;account_service:AccountService;groups:GroupRepository;group_service:GroupService;members:MemberRepository;datasets:DatasetRepository;dataset_service:DatasetService;jobs:V12JobRepository;peers:PeerCache;clients:ClientManager;auth:AuthService;gateway:MemberActionGateway;scanner:ParticipantScanner;precheck:TargetPrecheck;planner:MigrationPlanner;recovery:RecoveryService;import_export:ImportExportService;membership:GroupMembershipUtility;command_handlers:CommandHandlers|None=None

def bootstrap()->AppContext:
    paths=AppPaths.discover();settings=Settings.load(paths);database=Database(paths.data/'app.db');database.initialize();network=NetworkRuntime();events=EventBus();aggregator=EventAggregator();events.subscribe('*',aggregator.push);writer=DBWriter(database);governor=ResourceGovernor();runtime=ApplicationRuntime(network,governor,events,aggregator,WorkerPool(2),writer);commands=CommandBus();state=StateStore();metrics=PerformanceMonitor();accounts=V12AccountRepository(database,writer);groups=GroupRepository(database,writer);members=MemberRepository(database,writer);datasets=DatasetRepository(database,writer);jobs=V12JobRepository(database,writer);peers=PeerCache(database,writer);account_service=AccountService(accounts,paths.sessions);dataset_service=DatasetService(datasets);clients=ClientManager(network,settings.api_id,settings.api_hash)
    def session_lookup(account_id:int)->str:
        account=accounts.get(account_id)
        if account is None:raise KeyError(f'Unknown account id: {account_id}')
        return account.session_path
    auth=AuthService(clients,accounts,session_lookup);gateway=MemberActionGateway(clients,accounts,peers);group_service=GroupService(gateway);scanner=ParticipantScanner(gateway,members,datasets,peers,jobs,events,governor);precheck=TargetPrecheck(governor);planner=MigrationPlanner(database,jobs);recovery=RecoveryService(jobs);import_export=ImportExportService(datasets,members,jobs,events);membership=GroupMembershipUtility(gateway,governor)
    context=AppContext(paths,settings,database,runtime,commands,state,metrics,accounts,account_service,groups,group_service,members,datasets,dataset_service,jobs,peers,clients,auth,gateway,scanner,precheck,planner,recovery,import_export,membership)
    handlers=CommandHandlers(context);handlers.register_all();context.command_handlers=handlers
    def new_executor(self,job_id:int,interval:float):
        action=str(context.jobs.get_checkpoint(job_id).get('action','INVITE')).upper();executor=V12MigrationExecutor(context.gateway,context.jobs,context.accounts,context.runtime.governor,context.runtime.events,InviteScheduler(interval),context.runtime.workers,context.metrics,action=action);self._executors[job_id]=executor;return executor
    handlers._new_executor=MethodType(new_executor,handlers)
    def plan_action(account_id:int,source_dataset_id:int,filter_spec=None,action:str='INVITE')->None:
        snapshot=context.state.snapshot();target=snapshot.target_group;pre=snapshot.precheck
        if target is None or target.local_group_id is None or pre is None:raise ValueError('Hãy kiểm tra group đích trước khi tạo kế hoạch.')
        if snapshot.target_account_id!=account_id:raise ValueError('Group đích được kiểm tra bằng tài khoản khác.')
        action=action.upper()
        if action=='INVITE' and target.type.lower()=='chat':raise RuntimeError('Basic Chat bị chặn batch Add theo chính sách V1.2. Hãy dùng Megagroup/Supergroup.')
        def work():return context.planner.create_remove_plan(account_id,source_dataset_id,target.local_group_id,pre,filter_spec) if action=='REMOVE' else context.planner.create_plan(account_id,source_dataset_id,target.local_group_id,pre,filter_spec)
        def done(result):
            job_id,summary=result;context.state.update(migration_job_id=job_id,plan_summary=summary);context.runtime.events.publish(DomainEvent('MigrationPlanReady',{'job_id':job_id,'summary':summary,'action':action}))
        handlers._submit_worker('migration.plan',work,done)
    commands.register('migration.plan',plan_action)
    runtime.add_network_shutdown_hook(handlers.prepare_shutdown);runtime.add_network_shutdown_hook(clients.close_all);return context
