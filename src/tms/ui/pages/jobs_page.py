from PySide6.QtWidgets import QWidget,QVBoxLayout,QTableView,QPushButton
from ..models.job_table_model import JobTableModel
class JobsPage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);l=QVBoxLayout(self);self.model=JobTableModel(ctx.database);t=QTableView();t.setModel(self.model);l.addWidget(t);r=QPushButton('Refresh');r.clicked.connect(self.model.refresh);l.addWidget(r)
