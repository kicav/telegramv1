from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout,QListWidget,QMainWindow,QMessageBox,QStackedWidget,QWidget
from .pages.accounts_page import AccountsPage
from .pages.dashboard_page import DashboardPage
from .pages.jobs_page import JobsPage
from .pages.members_page import MembersPage
from .pages.migration_page import MigrationPage
from .pages.source_page import SourcePage
from .pages.tools_page import ToolsPage
class MainWindow(QMainWindow):
    def __init__(self,ctx):
        super().__init__();self.ctx=ctx;self.setWindowTitle('Telegram Migration Studio V1.2 — Stable Fast Path');self.resize(1280,800);root=QWidget();layout=QHBoxLayout(root);self.nav=QListWidget();self.nav.setMaximumWidth(190);self.stack=QStackedWidget();layout.addWidget(self.nav,1);layout.addWidget(self.stack,6);self.setCentralWidget(root);self.pages=[('Tổng quan',DashboardPage(ctx)),('Tài khoản',AccountsPage(ctx)),('Nguồn member',SourcePage(ctx)),('Member',MembersPage(ctx)),('Thao tác',MigrationPage(ctx)),('Công việc',JobsPage(ctx)),('Công cụ',ToolsPage(ctx))]
        for name,page in self.pages:self.nav.addItem(name);self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex);self.nav.setCurrentRow(0);self.statusBar().showMessage('Sẵn sàng');self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self._drain_events);self.timer.start()
    def _drain_events(self):
        for event in self.ctx.runtime.ui_events.drain():
            if event.name=='CommandFailed':self.statusBar().showMessage(str(event.payload.get('error','Thao tác thất bại')));QMessageBox.warning(self,'Thao tác thất bại',str(event.payload.get('error','Lỗi không xác định')))
            elif event.name=='BackgroundTaskDeferred':self.statusBar().showMessage(str(event.payload.get('reason','Tác vụ đang được hoãn')))
            for _name,page in self.pages:
                handler=getattr(page,'handle_event',None)
                if handler is not None:handler(event)
