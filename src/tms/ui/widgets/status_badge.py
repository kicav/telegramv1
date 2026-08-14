from PySide6.QtWidgets import QLabel

class StatusBadge(QLabel):
    def set_status(self,text:str)->None:
        self.setText(text); self.setProperty('status',text); self.style().unpolish(self); self.style().polish(self)
