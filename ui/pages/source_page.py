from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..controllers.source_controller import SourceController


class SourcePage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.controller = SourceController(ctx.commands)
        self.current_scan_job_id: int | None = None
        self.joined_groups = []
        self.joined_account_id: int | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Source: Telegram group, joined group, CSV or XLSX"))

        account_row = QHBoxLayout()
        self.account = QComboBox()
        self.refresh_accounts_button = QPushButton("Refresh accounts")
        account_row.addWidget(QLabel("Account"))
        account_row.addWidget(self.account)
        account_row.addWidget(self.refresh_accounts_button)
        layout.addLayout(account_row)

        resolve_row = QHBoxLayout()
        self.reference = QLineEdit()
        self.reference.setPlaceholderText("https://t.me/group, @username, invite link")
        self.resolve = QPushButton("Resolve")
        self.load_joined = QPushButton("Joined groups")
        resolve_row.addWidget(self.reference)
        resolve_row.addWidget(self.resolve)
        resolve_row.addWidget(self.load_joined)
        layout.addLayout(resolve_row)

        joined_row = QHBoxLayout()
        self.joined = QComboBox()
        self.select_joined = QPushButton("Use selected joined group")
        joined_row.addWidget(self.joined)
        joined_row.addWidget(self.select_joined)
        layout.addLayout(joined_row)

        scan_row = QHBoxLayout()
        self.dataset_name = QLineEdit()
        self.dataset_name.setPlaceholderText("Dataset name")
        self.scan = QPushButton("Get Members")
        self.cancel = QPushButton("Cancel scan")
        self.import_file = QPushButton("Import CSV/XLSX")
        scan_row.addWidget(self.dataset_name)
        scan_row.addWidget(self.scan)
        scan_row.addWidget(self.cancel)
        scan_row.addWidget(self.import_file)
        layout.addLayout(scan_row)

        self.info = QLabel("Select an account and resolve a source group.")
        self.progress = QLabel("")
        layout.addWidget(self.info)
        layout.addWidget(self.progress)
        layout.addStretch()

        self.refresh_accounts_button.clicked.connect(self.refresh_accounts)
        self.resolve.clicked.connect(self._resolve)
        self.load_joined.clicked.connect(self._load_joined)
        self.select_joined.clicked.connect(self._select_joined)
        self.scan.clicked.connect(self._scan)
        self.cancel.clicked.connect(self._cancel)
        self.import_file.clicked.connect(self._import)
        self.refresh_accounts()

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.warning(self, "Source", str(exc))

    def refresh_accounts(self) -> None:
        selected = self.account.currentData()
        self.account.clear()
        for account in self.ctx.accounts.list_all():
            if account.id is not None and account.enabled:
                self.account.addItem(f"{account.phone} — {account.status}", account.id)
        if selected is not None:
            index = self.account.findData(selected)
            if index >= 0:
                self.account.setCurrentIndex(index)

    def _account_id(self) -> int | None:
        value = self.account.currentData()
        return int(value) if value is not None else None

    def _resolve(self) -> None:
        account_id = self._account_id()
        reference = self.reference.text().strip()
        if account_id is None or not reference:
            return
        self._safe(lambda: self.controller.resolve(account_id, reference))

    def _load_joined(self) -> None:
        account_id = self._account_id()
        if account_id is not None:
            self._safe(lambda: self.controller.joined_groups(account_id))

    def _select_joined(self) -> None:
        index = self.joined.currentIndex()
        account_id = self._account_id()
        if account_id is None or not (0 <= index < len(self.joined_groups)):
            return
        if self.joined_account_id != account_id:
            QMessageBox.information(
                self,
                "Source",
                "The joined-group list belongs to another account. Reload joined groups first.",
            )
            return
        self._safe(
            lambda: self.controller.select_group(account_id, self.joined_groups[index])
        )

    def _scan(self) -> None:
        account_id = self._account_id()
        if account_id is None:
            return
        self._safe(
            lambda: self.controller.scan(account_id, self.dataset_name.text().strip())
        )

    def _cancel(self) -> None:
        if self.current_scan_job_id is not None:
            self._safe(lambda: self.controller.cancel_scan(self.current_scan_job_id))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import members",
            "",
            "Member files (*.csv *.xlsx *.xlsm)",
        )
        if not path:
            return
        account_id = self._account_id()
        name = self.dataset_name.text().strip() or Path(path).stem
        self._safe(lambda: self.controller.import_file(path, name, account_id))

    def handle_event(self, event) -> None:
        if event.name in {"AccountsChanged", "AccountStateChanged"}:
            self.refresh_accounts()
        elif event.name == "SourceGroupResolved":
            group = event.payload["group"]
            self.info.setText(
                f"Source: {group.title} | {group.type} | member={group.is_member} | read={group.can_read}"
            )
            if not self.dataset_name.text().strip():
                self.dataset_name.setText(group.title)
        elif event.name == "JoinedGroupsLoaded":
            self.joined_groups = list(event.payload.get("groups", []))
            self.joined_account_id = int(event.payload["account_id"])
            self.joined.clear()
            for group in self.joined_groups:
                self.joined.addItem(group.title)
        elif event.name == "MemberScanStarted":
            self.current_scan_job_id = int(event.payload["job_id"])
            self.progress.setText("Scanning members...")
        elif event.name == "MemberScanProgress":
            self.progress.setText(
                f"Scanned offset {event.payload.get('offset', 0)} | "
                f"accepted {event.payload.get('accepted', 0)} | "
                f"queue {event.payload.get('queue_depth', 0)}"
            )
        elif event.name == "MemberScanCompleted":
            self.progress.setText(
                f"Completed: {event.payload.get('accepted', 0)} accepted, "
                f"{event.payload.get('invalid', 0)} invalid"
            )
            self.current_scan_job_id = None
        elif event.name == "ImportCompleted":
            self.progress.setText(
                f"Import complete: {event.payload.get('accepted', 0)} accepted"
            )
