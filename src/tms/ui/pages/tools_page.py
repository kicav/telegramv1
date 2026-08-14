from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QLineEdit,QPushButton,QHBoxLayout
class ToolsPage(QWidget):
    def __init__(self,ctx,parent=None):
        super().__init__(parent);l=QVBoxLayout(self);l.addWidget(QLabel('Utilities'));row=QHBoxLayout();self.group=QLineEdit();self.group.setPlaceholderText('Group link');self.join=QPushButton('Join Group');self.leave=QPushButton('Leave Group');row.addWidget(self.group);row.addWidget(self.join);row.addWidget(self.leave);l.addLayout(row);l.addWidget(QLabel('Messenger / Archive / Script Runner are intentionally outside Core V1.'));l.addStretch()
