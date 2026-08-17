from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class AccountTableModel(QAbstractTableModel):
    headers = ["Phone", "Username", "Display name", "Status", "Enabled"]

    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.rows = []
        self.refresh()

    def refresh(self) -> None:
        self.beginResetModel()
        self.rows = self.repo.list_all()
        self.endResetModel()

    def account_id_at(self, row: int) -> int | None:
        if row < 0 or row >= len(self.rows):
            return None
        return self.rows[row].id

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        account = self.rows[index.row()]
        values = [
            account.phone,
            account.username,
            account.display_name,
            str(account.status),
            "Yes" if account.enabled else "No",
        ]
        value = values[index.column()]
        return "" if value is None else str(value)
