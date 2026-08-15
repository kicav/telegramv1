from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core.constants import (
    DEFAULT_INVITE_INTERVAL_SECONDS,
    MAX_INVITE_INTERVAL_SECONDS,
    MIN_INVITE_INTERVAL_SECONDS,
)
from ..controllers.job_controller import JobController
from ..models.job_table_model import JobTableModel


class JobsPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.controller = JobController(ctx.commands)
        layout = QVBoxLayout(self)
        self.model = JobTableModel(ctx.jobs)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.refresh = QPushButton("Refresh")
        self.export = QPushButton("Export results")
        self.export_log = QPushButton("Export log")
        self.resume = QPushButton("Resume selected job")
        self.interval = QDoubleSpinBox()
        self.interval.setRange(
            MIN_INVITE_INTERVAL_SECONDS, MAX_INVITE_INTERVAL_SECONDS
        )
        self.interval.setValue(DEFAULT_INVITE_INTERVAL_SECONDS)
        row.addWidget(self.refresh)
        row.addWidget(self.export)
        row.addWidget(self.export_log)
        row.addWidget(self.resume)
        row.addWidget(self.interval)
        layout.addLayout(row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Select a job to view persistent job events.")
        self.log.setMaximumBlockCount(1000)
        layout.addWidget(self.log)

        self.refresh.clicked.connect(self._refresh)
        self.export.clicked.connect(self._export)
        self.export_log.clicked.connect(self._export_log)
        self.resume.clicked.connect(self._resume)
        self.table.clicked.connect(self._load_log)

    def _selected_job_id(self) -> int | None:
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        return self.model.job_id_at(index.row())

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.warning(self, "Jobs", str(exc))

    def _refresh(self) -> None:
        self.model.refresh()
        self._load_log()

    def _load_log(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            self.log.clear()
            return
        rows = self.ctx.jobs.event_rows(job_id, limit=1000)
        lines = []
        for row in rows:
            message = row.get("message") or ""
            member = (
                f" member={row['member_id']}" if row.get("member_id") is not None else ""
            )
            lines.append(
                f"{row['timestamp']} [{row['level']}] {row['event_code']}{member} {message}".rstrip()
            )
        self.log.setPlainText("\n".join(lines))

    def _export(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export migration results",
            f"migration_job_{job_id}.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".csv")):
            path += ".csv" if "CSV" in selected_filter else ".xlsx"
        self._safe(lambda: self.controller.export_results(job_id, path))

    def _export_log(self) -> None:
        job_id = self._selected_job_id()
        if job_id is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export job log",
            f"job_{job_id}_log.csv",
            "CSV (*.csv);;Excel (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".csv")):
            path += ".xlsx" if "Excel" in selected_filter else ".csv"
        self._safe(lambda: self.controller.export_log(job_id, path))

    def _resume(self) -> None:
        job_id = self._selected_job_id()
        if job_id is not None:
            self._safe(
                lambda: self.controller.resume_migration(
                    job_id, self.interval.value()
                )
            )

    def handle_event(self, event) -> None:
        if event.name in {
            "JobStateChanged",
            "MigrationItemCompleted",
            "MigrationCompleted",
            "MemberScanStarted",
            "MemberScanCompleted",
            "ImportCompleted",
            "ExportCompleted",
            "JobFailed",
        }:
            self.model.refresh()
            self._load_log()
