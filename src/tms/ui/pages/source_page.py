from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QLineEdit,QPushButton,QComboBox,QHBoxLayout
class SourcePage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);l=QVBoxLayout(self);l.addWidget(QLabel('Source'));row=QHBoxLayout();self.reference=QLineEdit();self.reference.setPlaceholderText('Group link / @username / invite link');self.resolve=QPushButton('Resolve');row.addWidget(self.reference);row.addWidget(self.resolve);l.addLayout(row);self.info=QLabel('Choose an account then resolve source.');l.addWidget(self.info);l.addStretch()
