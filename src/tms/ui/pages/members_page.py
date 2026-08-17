from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..controllers.member_controller import MemberController
from ..models.member_table_model import MemberTableModel


class MembersPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.controller = MemberController(ctx.commands)
        layout = QVBoxLayout(self)

        select_row = QHBoxLayout()
        self.dataset = QComboBox()
        self.refresh_button = QPushButton("Refresh datasets")
        select_row.addWidget(QLabel("Dataset"))
        select_row.addWidget(self.dataset)
        select_row.addWidget(self.refresh_button)
        layout.addLayout(select_row)

        self.model = MemberTableModel(ctx.members)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(False)
        layout.addWidget(self.table)

        page_row = QHBoxLayout()
        self.previous = QPushButton("Previous")
        self.next = QPushButton("Next")
        self.page_label = QLabel("")
        page_row.addWidget(self.previous)
        page_row.addWidget(self.next)
        page_row.addWidget(self.page_label)
        page_row.addStretch()
        layout.addLayout(page_row)

        combine_row = QHBoxLayout()
        self.dataset_a = QComboBox()
        self.operation = QComboBox()
        self.operation.addItems(["UNION", "INTERSECTION", "DIFFERENCE"])
        self.dataset_b = QComboBox()
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("Result dataset name")
        self.combine = QPushButton("Run 2-file workflow")
        for widget in (
            self.dataset_a,
            self.operation,
            self.dataset_b,
            self.output_name,
            self.combine,
        ):
            combine_row.addWidget(widget)
        layout.addLayout(combine_row)

        export_row = QHBoxLayout()
        self.export = QPushButton("Export selected dataset")
        export_row.addWidget(self.export)
        export_row.addStretch()
        layout.addLayout(export_row)

        self.dataset.currentIndexChanged.connect(self._dataset_changed)
        self.refresh_button.clicked.connect(self.refresh_datasets)
        self.previous.clicked.connect(self._previous)
        self.next.clicked.connect(self._next)
        self.combine.clicked.connect(self._combine)
        self.export.clicked.connect(self._export)
        self.refresh_datasets()
        self._update_page_label()

    def _safe(self, action) -> None:
        try:
            action()
        except Exception as exc:
            QMessageBox.warning(self, "Members", str(exc))

    def refresh_datasets(self) -> None:
        selected = self.dataset.currentData()
        datasets = self.ctx.datasets.list_all()
        for combo in (self.dataset, self.dataset_a, self.dataset_b):
            combo.blockSignals(True)
            combo.clear()
            for dataset in datasets:
                if dataset.id is not None:
                    combo.addItem(f"{dataset.name} ({dataset.member_count})", dataset.id)
            combo.blockSignals(False)
        if selected is not None:
            index = self.dataset.findData(selected)
            if index >= 0:
                self.dataset.setCurrentIndex(index)
        self._dataset_changed()

    def _dataset_changed(self) -> None:
        value = self.dataset.currentData()
        dataset_id = int(value) if value is not None else None
        self.model.set_dataset(dataset_id)
        if dataset_id is not None:
            self._safe(lambda: self.controller.select_dataset(dataset_id))
        self._update_page_label()

    def _update_page_label(self) -> None:
        if self.model.total == 0:
            self.page_label.setText("0 rows")
            return
        start = self.model.offset + 1
        end = min(self.model.offset + len(self.model.rows), self.model.total)
        self.page_label.setText(f"{start}–{end} / {self.model.total}")

    def _previous(self) -> None:
        self.model.previous_page()
        self._update_page_label()

    def _next(self) -> None:
        self.model.next_page()
        self._update_page_label()

    def _combine(self) -> None:
        a = self.dataset_a.currentData()
        b = self.dataset_b.currentData()
        if a is None or b is None:
            return
        name = self.output_name.text().strip() or f"{self.operation.currentText()} result"
        self._safe(
            lambda: self.controller.combine(
                name, int(a), int(b), self.operation.currentText()
            )
        )

    def _export(self) -> None:
        dataset_id = self.dataset.currentData()
        if dataset_id is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export dataset",
            "members.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith((".xlsx", ".csv")):
            path += ".csv" if "CSV" in selected_filter else ".xlsx"
        account_id = self.ctx.state.snapshot().active_account_id
        self._safe(
            lambda: self.controller.export(int(dataset_id), path, account_id)
        )

    def handle_event(self, event) -> None:
        if event.name in {
            "DatasetCreated",
            "ImportCompleted",
            "MemberScanCompleted",
            "ExportCompleted",
        }:
            self.refresh_datasets()
