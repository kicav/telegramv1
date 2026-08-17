from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QWidget

from ...members.filter_spec import FilterSpec


def _csv_set(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


class FilterPanel(QWidget):
    """Local-only migration filters.

    Activity/source values are optional comma-separated exact labels. Duplicates,
    members already known in the target and members processed by previous jobs for the
    same target are handled automatically by the planner.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self.exclude_bot = QCheckBox("Exclude Bot")
        self.exclude_bot.setChecked(True)
        self.exclude_deleted = QCheckBox("Exclude Deleted")
        self.exclude_deleted.setChecked(True)
        self.username_required = QCheckBox("Username required")
        self.activity = QLineEdit()
        self.activity.setPlaceholderText("online, recently, last_week (optional)")
        self.source = QLineEdit()
        self.source.setPlaceholderText("source labels, comma-separated (optional)")
        layout.addRow(self.exclude_bot)
        layout.addRow(self.exclude_deleted)
        layout.addRow(self.username_required)
        layout.addRow("Activity", self.activity)
        layout.addRow("Source", self.source)

    def spec(self) -> FilterSpec:
        return FilterSpec(
            exclude_bot=self.exclude_bot.isChecked(),
            exclude_deleted=self.exclude_deleted.isChecked(),
            username_required=self.username_required.isChecked(),
            activity=_csv_set(self.activity.text()),
            source=_csv_set(self.source.text()),
        )
