from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QListWidget,QStackedWidget
from .pages.dashboard_page import DashboardPage
from .pages.accounts_page import AccountsPage
from .pages.source_page import SourcePage
from .pages.members_page import MembersPage
from .pages.migration_page import MigrationPage
from .pages.jobs_page import JobsPage
from .pages.tools_page import ToolsPage


class MainWindow(QMainWindow):
    def __init__(self,ctx):
        super().__init__();self.ctx=ctx;self.setWindowTitle('Telegram Migration Studio');self.resize(1180,760)
        root=QWidget();lay=QHBoxLayout(root);self.nav=QListWidget();self.stack=QStackedWidget();lay.addWidget(self.nav,1);lay.addWidget(self.stack,5);self.setCentralWidget(root)
        pages=[('Dashboard',DashboardPage(ctx)),('Accounts',AccountsPage(ctx)),('Source',SourcePage(ctx)),('Members',MembersPage(ctx)),('Migration',MigrationPage(ctx)),('Jobs',JobsPage(ctx)),('Tools',ToolsPage(ctx))]
        for name,page in pages:self.nav.addItem(name);self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex);self.nav.setCurrentRow(0)
        self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self._drain_events);self.timer.start()
    def _drain_events(self):
        # UI consumes aggregated events only; it never talks to Telegram or SQLite writers.
        self.ctx.runtime.ui_events.drain()
