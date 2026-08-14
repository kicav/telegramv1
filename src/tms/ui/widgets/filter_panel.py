from PySide6.QtWidgets import QWidget,QVBoxLayout,QCheckBox
class FilterPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); lay=QVBoxLayout(self); self.exclude_bot=QCheckBox('Exclude Bot'); self.exclude_bot.setChecked(True); self.exclude_deleted=QCheckBox('Exclude Deleted'); self.exclude_deleted.setChecked(True); self.username_required=QCheckBox('Username required'); [lay.addWidget(x) for x in (self.exclude_bot,self.exclude_deleted,self.username_required)]
