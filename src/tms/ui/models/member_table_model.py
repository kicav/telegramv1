from PySide6.QtCore import QAbstractTableModel,QModelIndex,Qt
class MemberTableModel(QAbstractTableModel):
    headers=['User ID','Username','First name','Last name','Status']
    def __init__(self,repo,dataset_id=None,page_size=200,parent=None):
        super().__init__(parent); self.repo=repo;self.dataset_id=dataset_id;self.page_size=page_size;self.rows=[];self.total=0;self.offset=0;self.load_page(0)
    def load_page(self,offset:int):
        self.beginResetModel();self.rows,self.total=self.repo.page(offset,self.page_size,self.dataset_id);self.offset=offset;self.endResetModel()
    def rowCount(self,parent=QModelIndex()): return len(self.rows)
    def columnCount(self,parent=QModelIndex()): return len(self.headers)
    def headerData(self,section,orientation,role=Qt.DisplayRole): return self.headers[section] if role==Qt.DisplayRole and orientation==Qt.Horizontal else None
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid() or role!=Qt.DisplayRole:return None
        m=self.rows[index.row()]; vals=[m.telegram_user_id,m.username,m.first_name,m.last_name,m.activity_status]; return '' if vals[index.column()] is None else str(vals[index.column()])
