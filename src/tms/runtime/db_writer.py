from dataclasses import dataclass
from queue import Queue, Empty
import sqlite3
import threading
from typing import Any
from ..storage.database import Database


@dataclass(slots=True)
class DBOperation:
    sql: str
    params: tuple[Any, ...] | list[tuple[Any, ...]]
    many: bool = False
    critical: bool = False


class DBWriter:
    """The only component allowed to commit routine writes."""
    def __init__(self, database: Database, batch_limit: int = 250) -> None:
        self.database = database
        self.batch_limit = batch_limit
        self.queue: Queue[DBOperation | None] = Queue(maxsize=5000)
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="TMS-DBWriter", daemon=True)
        self._thread.start()
        self._started.wait(timeout=5)

    def submit(self, op: DBOperation) -> None:
        self.queue.put(op)

    def stop(self) -> None:
        self.queue.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def _apply(self, conn: sqlite3.Connection, op: DBOperation) -> None:
        if op.many:
            conn.executemany(op.sql, op.params)  # type: ignore[arg-type]
        else:
            conn.execute(op.sql, op.params)  # type: ignore[arg-type]

    def _run(self) -> None:
        conn = self.database.connect()
        self._started.set()
        pending: list[DBOperation] = []
        try:
            while True:
                try:
                    item = self.queue.get(timeout=0.25)
                except Empty:
                    item = "FLUSH"  # type: ignore[assignment]
                if item is None:
                    break
                if item == "FLUSH":
                    if pending:
                        with conn:
                            for op in pending:
                                self._apply(conn, op)
                        pending.clear()
                    continue
                pending.append(item)
                if item.critical or len(pending) >= self.batch_limit:
                    with conn:
                        for op in pending:
                            self._apply(conn, op)
                    pending.clear()
            if pending:
                with conn:
                    for op in pending:
                        self._apply(conn, op)
        finally:
            conn.close()
