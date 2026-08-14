from PySide6.QtCore import QAbstractTableModel,QModelIndex,Qt
class JobTableModel(QAbstractTableModel):
    headers=['ID','Type','State','Progress','Success','Skipped','Failed']
    def __init__(self,db,parent=None):super().__init__(parent);self.db=db;self.rows=[];self.refresh()
    def refresh(self):
        with self.db.reader() as c:self.rows=[dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 200')]
        self.layoutChanged.emit()
    def rowCount(self,parent=QModelIndex()):return len(self.rows)
    def columnCount(self,parent=QModelIndex()):return len(self.headers)
    def headerData(self,s,o,r=Qt.DisplayRole):return self.headers[s] if r==Qt.DisplayRole and o==Qt.Horizontal else None
    def data(self,i,r=Qt.DisplayRole):
        if not i.isValid() or r!=Qt.DisplayRole:return None
        x=self.rows[i.row()];vals=[x['id'],x['job_type'],x['state'],f"{x['processed']}/{x['total']}",x['success'],x['skipped'],x['failed']];return str(vals[i.column()])
