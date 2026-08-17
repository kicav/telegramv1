from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DashboardPage(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        layout = QVBoxLayout(self)
        title = QLabel("Telegram Migration Studio")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(
            QLabel(
                "Core V1 workflow: Account → Source → Dataset → Filter → "
                "Target pre-check → Migration → Result"
            )
        )
        self.status = QLabel("Ready")
        self.metrics = QLabel("")
        layout.addWidget(self.status)
        layout.addWidget(self.metrics)
        layout.addStretch()

    def handle_event(self, event) -> None:
        if event.name == "JobStateChanged":
            self.status.setText(
                f"Job #{event.payload.get('job_id')}: {event.payload.get('state')}"
            )
        elif event.name == "CommandFailed":
            self.status.setText(f"Error: {event.payload.get('error')}")
        snapshot = self.ctx.metrics.snapshot()
        if snapshot:
            local_ms = snapshot.get("local_prepare_ms_avg", 0.0)
            rpc_ms = snapshot.get("rpc_latency_ms_avg", 0.0)
            self.metrics.setText(
                f"Diagnostics: local prepare avg {local_ms:.2f} ms | RPC avg {rpc_ms:.2f} ms"
            )
