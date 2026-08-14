from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel
class DashboardPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);l=QVBoxLayout(self);title=QLabel('Telegram Migration Studio');title.setObjectName('pageTitle');l.addWidget(title);l.addWidget(QLabel('Core V1 • Accounts → Source → Members → Migration'));l.addStretch()
