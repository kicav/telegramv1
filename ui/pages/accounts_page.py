from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..controllers.account_controller import AccountController
from ..models.account_table_model import AccountTableModel


class AccountsPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.controller = AccountController(ctx.commands)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+84...")
        form.addRow("Phone", self.phone)
        layout.addLayout(form)

        row = QHBoxLayout()
        self.add_button = QPushButton("Add account")
        self.api_button = QPushButton("Telegram API Settings")
        self.connect_button = QPushButton("Connect")
        self.otp_button = QPushButton("Send OTP")
        self.signin_button = QPushButton("Sign in")
        self.toggle_button = QPushButton("Enable/Disable")
        self.delete_button = QPushButton("Delete")
        for button in (
            self.add_button,
            self.api_button,
            self.connect_button,
            self.otp_button,
            self.signin_button,
            self.toggle_button,
            self.delete_button,
        ):
            row.addWidget(button)
        layout.addLayout(row)

        self.model = AccountTableModel(ctx.accounts)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        layout.addWidget(self.table)

        self.add_button.clicked.connect(self._add)
        self.api_button.clicked.connect(self._api_settings)
        self.connect_button.clicked.connect(self._connect)
        self.otp_button.clicked.connect(self._send_otp)
        self.signin_button.clicked.connect(self._sign_in)
        self.toggle_button.clicked.connect(self._toggle)
        self.delete_button.clicked.connect(self._delete)
        self.table.clicked.connect(self._select)

    def _selected_account(self):
        index = self.table.currentIndex()
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self.model.rows):
            return None
        return self.model.rows[row]

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.warning(self, "Accounts", str(exc))

    def _add(self) -> None:
        phone = self.phone.text().strip()
        if not phone:
            return
        self._safe(lambda: self.controller.add(phone))

    def _api_settings(self) -> None:
        api_id, ok = QInputDialog.getInt(
            self,
            "Telegram API",
            "API ID",
            int(self.ctx.settings.api_id or 0),
            1,
            2_147_483_647,
        )
        if not ok:
            return
        api_hash, ok = QInputDialog.getText(
            self,
            "Telegram API",
            "API Hash",
            QLineEdit.Normal,
            self.ctx.settings.api_hash or "",
        )
        if ok:
            self._safe(lambda: self.controller.update_settings(api_id, api_hash))

    def _select(self) -> None:
        account = self._selected_account()
        if account and account.id is not None:
            self._safe(lambda: self.controller.select(account.id))

    def _connect(self) -> None:
        account = self._selected_account()
        if account and account.id is not None:
            self._safe(lambda: self.controller.connect(account.id))

    def _send_otp(self) -> None:
        account = self._selected_account()
        if account and account.id is not None:
            self._safe(lambda: self.controller.send_code(account.id))

    def _sign_in(self) -> None:
        account = self._selected_account()
        if account is None or account.id is None:
            return
        code, ok = QInputDialog.getText(self, "Telegram OTP", "OTP code")
        if not ok or not code.strip():
            return
        password, _ = QInputDialog.getText(
            self,
            "Telegram 2FA",
            "2FA password (leave empty if disabled)",
            QLineEdit.Password,
        )
        self._safe(
            lambda: self.controller.sign_in(
                account.id, code.strip(), password or None
            )
        )

    def _toggle(self) -> None:
        account = self._selected_account()
        if account and account.id is not None:
            self._safe(lambda: self.controller.enable(account.id, not account.enabled))

    def _delete(self) -> None:
        account = self._selected_account()
        if account is None or account.id is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete account",
            f"Delete {account.phone} and its local session?",
        )
        if answer == QMessageBox.Yes:
            self._safe(lambda: self.controller.delete(account.id))

    def handle_event(self, event) -> None:
        if event.name in {
            "AccountsChanged",
            "AccountConnected",
            "AccountAuthenticated",
            "AccountStateChanged",
        }:
            self.model.refresh()
            self.phone.clear()
