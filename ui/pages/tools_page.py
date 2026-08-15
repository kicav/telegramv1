from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ToolsPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Utilities — Join / Leave only in Core V1"))

        account_row = QHBoxLayout()
        self.account = QComboBox()
        self.refresh = QPushButton("Refresh accounts")
        account_row.addWidget(self.account)
        account_row.addWidget(self.refresh)
        layout.addLayout(account_row)

        row = QHBoxLayout()
        self.group = QLineEdit()
        self.group.setPlaceholderText("Group link")
        self.join = QPushButton("Join Group")
        self.leave = QPushButton("Leave Group")
        row.addWidget(self.group)
        row.addWidget(self.join)
        row.addWidget(self.leave)
        layout.addLayout(row)
        self.status = QLabel("")
        layout.addWidget(self.status)
        layout.addWidget(
            QLabel("Messenger / Archive / Script Runner are intentionally outside Core V1.")
        )
        layout.addStretch()

        self.refresh.clicked.connect(self.refresh_accounts)
        self.join.clicked.connect(self._join)
        self.leave.clicked.connect(self._leave)
        self.refresh_accounts()

    def refresh_accounts(self) -> None:
        selected = self.account.currentData()
        self.account.clear()
        for account in self.ctx.accounts.list_all():
            if account.id is not None and account.enabled:
                self.account.addItem(account.phone, account.id)
        if selected is not None:
            index = self.account.findData(selected)
            if index >= 0:
                self.account.setCurrentIndex(index)

    def _safe(self, command: str) -> None:
        account_id = self.account.currentData()
        reference = self.group.text().strip()
        if account_id is None or not reference:
            return
        try:
            self.ctx.commands.dispatch(
                command, account_id=int(account_id), reference=reference
            )
        except Exception as exc:
            QMessageBox.warning(self, "Tools", str(exc))

    def _join(self) -> None:
        self._safe("utility.join")

    def _leave(self) -> None:
        self._safe("utility.leave")

    def handle_event(self, event) -> None:
        if event.name in {"AccountsChanged", "AccountStateChanged"}:
            self.refresh_accounts()
        elif event.name == "UtilityCompleted":
            group = event.payload.get("group")
            action = event.payload.get("action")
            self.status.setText(f"{action}: {getattr(group, 'title', '')}")
