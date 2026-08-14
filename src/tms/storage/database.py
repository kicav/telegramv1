from contextlib import contextmanager
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from .pragmas import PRAGMAS


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._schema = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        for pragma in PRAGMAS:
            conn.execute(pragma)
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(self._schema)
            conn.commit()

    @contextmanager
    def reader(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()
