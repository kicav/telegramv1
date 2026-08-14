from PySide6.QtCore import QAbstractTableModel,QModelIndex,Qt
class AccountTableModel(QAbstractTableModel):
    headers=['Phone','Username','Display name','Status','Enabled']
    def __init__(self,repo,parent=None): super().__init__(parent); self.repo=repo;self.rows=[];self.refresh()
    def refresh(self): self.beginResetModel();self.rows=self.repo.list_all();self.endResetModel()
    def rowCount(self,parent=QModelIndex()):return len(self.rows)
    def columnCount(self,parent=QModelIndex()):return len(self.headers)
    def headerData(self,s,o,r=Qt.DisplayRole):return self.headers[s] if r==Qt.DisplayRole and o==Qt.Horizontal else None
    def data(self,i,r=Qt.DisplayRole):
        if not i.isValid() or r!=Qt.DisplayRole:return None
        a=self.rows[i.row()];vals=[a.phone,a.username,a.display_name,a.status,'Yes' if a.enabled else 'No'];return '' if vals[i.column()] is None else str(vals[i.column()])
