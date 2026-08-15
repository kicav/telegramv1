from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from .pages.accounts_page import AccountsPage
from .pages.dashboard_page import DashboardPage
from .pages.jobs_page import JobsPage
from .pages.members_page import MembersPage
from .pages.migration_page import MigrationPage
from .pages.source_page import SourcePage
from .pages.tools_page import ToolsPage


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle("Telegram Migration Studio")
        self.resize(1280, 800)

        root = QWidget()
        layout = QHBoxLayout(root)
        self.nav = QListWidget()
        self.nav.setMaximumWidth(180)
        self.stack = QStackedWidget()
        layout.addWidget(self.nav, 1)
        layout.addWidget(self.stack, 6)
        self.setCentralWidget(root)

        self.pages = [
            ("Dashboard", DashboardPage(ctx)),
            ("Accounts", AccountsPage(ctx)),
            ("Source", SourcePage(ctx)),
            ("Members", MembersPage(ctx)),
            ("Migration", MigrationPage(ctx)),
            ("Jobs", JobsPage(ctx)),
            ("Tools", ToolsPage(ctx)),
        ]
        for name, page in self.pages:
            self.nav.addItem(name)
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.statusBar().showMessage("Ready")

        self.timer = QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._drain_events)
        self.timer.start()

    def _drain_events(self) -> None:
        events = self.ctx.runtime.ui_events.drain()
        for event in events:
            if event.name == "CommandFailed":
                self.statusBar().showMessage(str(event.payload.get("error", "Command failed")))
                QMessageBox.warning(
                    self,
                    "Operation failed",
                    str(event.payload.get("error", "Unknown error")),
                )
            elif event.name == "BackgroundTaskDeferred":
                self.statusBar().showMessage(str(event.payload.get("reason", "Task deferred")))
            for _name, page in self.pages:
                handler = getattr(page, "handle_event", None)
                if handler is not None:
                    handler(event)
