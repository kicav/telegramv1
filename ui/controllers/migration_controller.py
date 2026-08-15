class MigrationController:
    def __init__(self, command_bus):
        self.commands = command_bus

    def resolve_target(self, account_id: int, reference: str) -> None:
        self.commands.dispatch(
            "target.resolve", account_id=account_id, reference=reference
        )

    def precheck(self, account_id: int) -> None:
        self.commands.dispatch("migration.precheck", account_id=account_id)

    def plan(self, account_id: int, source_dataset_id: int, filter_spec) -> None:
        self.commands.dispatch(
            "migration.plan",
            account_id=account_id,
            source_dataset_id=source_dataset_id,
            filter_spec=filter_spec,
        )

    def start(self, job_id: int, account_id: int, interval_seconds: float) -> None:
        self.commands.dispatch(
            "migration.start",
            job_id=job_id,
            account_id=account_id,
            interval_seconds=interval_seconds,
        )

    def pause(self, job_id: int) -> None:
        self.commands.dispatch("migration.pause", job_id=job_id)

    def stop(self, job_id: int) -> None:
        self.commands.dispatch("migration.stop", job_id=job_id)

    def resume(self, job_id: int, interval_seconds: float) -> None:
        self.commands.dispatch(
            "migration.resume", job_id=job_id, interval_seconds=interval_seconds
        )
