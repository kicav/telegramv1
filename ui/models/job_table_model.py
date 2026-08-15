from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class JobTableModel(QAbstractTableModel):
    headers = ["ID", "Type", "State", "Progress", "Success", "Skipped", "Failed"]

    def __init__(self, jobs, parent=None):
        super().__init__(parent)
        self.jobs = jobs
        self.rows = []
        self.refresh()

    def refresh(self) -> None:
        self.beginResetModel()
        self.rows = self.jobs.list_recent(200)
        self.endResetModel()

    def job_id_at(self, row: int) -> int | None:
        if row < 0 or row >= len(self.rows):
            return None
        return int(self.rows[row]["id"])

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
        row = self.rows[index.row()]
        values = [
            row["id"],
            row["job_type"],
            row["state"],
            f"{row['processed']}/{row['total']}",
            row["success"],
            row["skipped"],
            row["failed"],
        ]
        return str(values[index.column()])
