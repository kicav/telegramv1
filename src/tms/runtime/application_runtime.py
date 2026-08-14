from dataclasses import dataclass
from .network_runtime import NetworkRuntime
from .resource_governor import ResourceGovernor
from .event_bus import EventBus
from .event_aggregator import EventAggregator
from .worker_pool import WorkerPool
from .db_writer import DBWriter


@dataclass(slots=True)
class ApplicationRuntime:
    network: NetworkRuntime
    governor: ResourceGovernor
    events: EventBus
    ui_events: EventAggregator
    workers: WorkerPool
    db_writer: DBWriter

    def start(self) -> None:
        self.db_writer.start(); self.network.start()

    def stop(self) -> None:
        self.network.stop(); self.db_writer.stop(); self.workers.shutdown()
