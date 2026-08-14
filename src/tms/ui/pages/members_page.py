from PySide6.QtWidgets import QWidget,QVBoxLayout,QTableView,QLabel
from ..models.member_table_model import MemberTableModel
from ..widgets.filter_panel import FilterPanel
class MembersPage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);l=QVBoxLayout(self);l.addWidget(QLabel('Members / Dataset'));l.addWidget(FilterPanel());self.model=MemberTableModel(ctx.members);t=QTableView();t.setModel(self.model);t.setSortingEnabled(False);l.addWidget(t)
