from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import (
    DEFAULT_INVITE_INTERVAL_SECONDS,
    MAX_INVITE_INTERVAL_SECONDS,
    MIN_INVITE_INTERVAL_SECONDS,
)
from ..controllers.migration_controller import MigrationController
from ..widgets.filter_panel import FilterPanel


class MigrationPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.controller = MigrationController(ctx.commands)
        self.current_job_id: int | None = None
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.account = QComboBox()
        self.dataset = QComboBox()
        self.target_reference = QLineEdit()
        self.target_reference.setPlaceholderText("Target group link / @username")
        self.interval = QDoubleSpinBox()
        self.interval.setRange(
            MIN_INVITE_INTERVAL_SECONDS, MAX_INVITE_INTERVAL_SECONDS
        )
        self.interval.setValue(
            ctx.settings.invite_interval_seconds or DEFAULT_INVITE_INTERVAL_SECONDS
        )
        self.interval.setSingleStep(0.5)
        form.addRow("Account", self.account)
        form.addRow("Source dataset", self.dataset)
        form.addRow("Target", self.target_reference)
        form.addRow("Invite interval (s)", self.interval)
        layout.addLayout(form)

        self.filters = FilterPanel()
        layout.addWidget(self.filters)

        row = QHBoxLayout()
        self.refresh = QPushButton("Refresh")
        self.resolve_target = QPushButton("Resolve target")
        self.precheck = QPushButton("PRECHECK")
        self.plan = QPushButton("PLAN")
        self.start = QPushButton("START")
        self.pause = QPushButton("Pause")
        self.resume = QPushButton("Resume")
        self.stop = QPushButton("Stop")
        for button in (
            self.refresh,
            self.resolve_target,
            self.precheck,
            self.plan,
            self.start,
            self.pause,
            self.resume,
            self.stop,
        ):
            row.addWidget(button)
        layout.addLayout(row)

        self.target_info = QLabel("Resolve target, then run target pre-check.")
        self.summary = QLabel("No migration plan yet.")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.counters = QLabel("Success 0   Skip 0   Failed 0   Processed 0")
        layout.addWidget(self.target_info)
        layout.addWidget(self.summary)
        layout.addWidget(self.progress)
        layout.addWidget(self.counters)
        layout.addStretch()

        self.refresh.clicked.connect(self.refresh_sources)
        self.resolve_target.clicked.connect(self._resolve_target)
        self.precheck.clicked.connect(self._precheck)
        self.plan.clicked.connect(self._plan)
        self.start.clicked.connect(self._start)
        self.pause.clicked.connect(self._pause)
        self.resume.clicked.connect(self._resume)
        self.stop.clicked.connect(self._stop)
        self.refresh_sources()

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.warning(self, "Migration", str(exc))

    def refresh_sources(self) -> None:
        selected_account = self.account.currentData()
        selected_dataset = self.dataset.currentData()
        self.account.clear()
        for account in self.ctx.accounts.list_all():
            if account.id is not None and account.enabled:
                self.account.addItem(f"{account.phone} — {account.status}", account.id)
        self.dataset.clear()
        for dataset in self.ctx.datasets.list_all():
            if dataset.id is not None:
                self.dataset.addItem(
                    f"{dataset.name} ({dataset.member_count})", dataset.id
                )
        if selected_account is not None:
            index = self.account.findData(selected_account)
            if index >= 0:
                self.account.setCurrentIndex(index)
        if selected_dataset is not None:
            index = self.dataset.findData(selected_dataset)
            if index >= 0:
                self.dataset.setCurrentIndex(index)

    def _account_id(self) -> int | None:
        value = self.account.currentData()
        return int(value) if value is not None else None

    def _dataset_id(self) -> int | None:
        value = self.dataset.currentData()
        return int(value) if value is not None else None

    def _resolve_target(self) -> None:
        account_id = self._account_id()
        reference = self.target_reference.text().strip()
        if account_id is None or not reference:
            return
        self._safe(lambda: self.controller.resolve_target(account_id, reference))

    def _precheck(self) -> None:
        account_id = self._account_id()
        if account_id is not None:
            self._safe(lambda: self.controller.precheck(account_id))

    def _plan(self) -> None:
        account_id = self._account_id()
        dataset_id = self._dataset_id()
        if account_id is None or dataset_id is None:
            return
        self._safe(
            lambda: self.controller.plan(account_id, dataset_id, self.filters.spec())
        )

    def _start(self) -> None:
        account_id = self._account_id()
        if self.current_job_id is None or account_id is None:
            QMessageBox.information(self, "Migration", "Create a migration plan first.")
            return
        self._safe(
            lambda: self.controller.start(
                self.current_job_id, account_id, self.interval.value()
            )
        )

    def _pause(self) -> None:
        if self.current_job_id is not None:
            self._safe(lambda: self.controller.pause(self.current_job_id))

    def _resume(self) -> None:
        if self.current_job_id is not None:
            self._safe(
                lambda: self.controller.resume(
                    self.current_job_id, self.interval.value()
                )
            )

    def _stop(self) -> None:
        if self.current_job_id is not None:
            self._safe(lambda: self.controller.stop(self.current_job_id))

    def _refresh_counters(self, job_id: int) -> None:
        summary = self.ctx.jobs.summary(job_id)
        total = max(1, summary["total"])
        percent = int(summary["processed"] * 100 / total)
        self.progress.setValue(percent)
        self.counters.setText(
            f"Success {summary['success']}   Skip {summary['skipped']}   "
            f"Failed {summary['failed']}   Processed {summary['processed']}/{summary['total']}"
        )

    def handle_event(self, event) -> None:
        if event.name in {
            "AccountsChanged",
            "AccountStateChanged",
            "DatasetCreated",
            "ImportCompleted",
            "MemberScanCompleted",
        }:
            self.refresh_sources()
        elif event.name == "TargetGroupResolved":
            group = event.payload["group"]
            self.target_info.setText(
                f"Target: {group.title} | member={group.is_member} | "
                f"admin={group.is_admin} | invite={group.can_invite}"
            )
        elif event.name == "TargetPrecheckCompleted":
            self.target_info.setText(
                f"Target pre-check: {event.payload.get('coverage')} | "
                f"known IDs: {event.payload.get('target_count', 0)}"
            )
        elif event.name == "MigrationPlanReady":
            self.current_job_id = int(event.payload["job_id"])
            summary = event.payload["summary"]
            self.summary.setText(
                f"Source {summary.total_source} | Filtered {summary.filtered} | "
                f"Already target {summary.already_target} | Invalid {summary.invalid} | "
                f"Ready {summary.ready} | Job #{self.current_job_id}"
            )
            self._refresh_counters(self.current_job_id)
        elif event.name in {
            "MigrationItemCompleted",
            "MigrationCompleted",
            "JobStateChanged",
        }:
            job_id = event.payload.get("job_id")
            if job_id is not None and (
                self.current_job_id is None or int(job_id) == self.current_job_id
            ):
                self.current_job_id = int(job_id)
                self._refresh_counters(self.current_job_id)
