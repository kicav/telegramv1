from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QProgressBar
class ProgressCard(QWidget):
    def __init__(self,title:str,parent=None):
        super().__init__(parent); lay=QVBoxLayout(self); self.title=QLabel(title); self.bar=QProgressBar(); self.detail=QLabel(''); lay.addWidget(self.title);lay.addWidget(self.bar);lay.addWidget(self.detail)
