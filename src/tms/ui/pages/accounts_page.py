from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QTableView,QMessageBox
from ..models.account_table_model import AccountTableModel
class AccountsPage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);self.ctx=ctx;l=QVBoxLayout(self);bar=QHBoxLayout();self.phone=QLineEdit();self.phone.setPlaceholderText('+84...');add=QPushButton('Add account');bar.addWidget(self.phone);bar.addWidget(add);l.addLayout(bar);self.model=AccountTableModel(ctx.accounts);table=QTableView();table.setModel(self.model);l.addWidget(table);add.clicked.connect(self._add)
    def _add(self):
        p=self.phone.text().strip()
        if not p:return
        try:self.ctx.account_service.add(p);self.phone.clear();self.model.refresh()
        except Exception as e:QMessageBox.critical(self,'Account',str(e))
