from __future__ import annotations

import sqlite3

from ..runtime.db_writer import DBWriter
from ..storage.database import Database
from .models import Dataset


class DatasetRepository:
    def __init__(self, db: Database, writer: DBWriter) -> None:
        self.db = db
        self.writer = writer

    def create(self, dataset: Dataset) -> int:
        def operation(conn: sqlite3.Connection) -> int:
            cursor = conn.execute(
                "INSERT INTO datasets(name,source_type,source_reference,status,member_count) VALUES(?,?,?,?,?)",
                (
                    dataset.name,
                    dataset.source_type,
                    dataset.source_reference,
                    dataset.status,
                    dataset.member_count,
                ),
            )
            return int(cursor.lastrowid)

        return self.writer.submit(operation, critical=True).result(timeout=10)

    def get(self, dataset_id: int) -> Dataset | None:
        with self.db.reader() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        if not row:
            return None
        return Dataset(
            int(row["id"]),
            row["name"],
            row["source_type"],
            row["source_reference"],
            row["status"],
            int(row["member_count"]),
        )

    def list_all(self) -> list[Dataset]:
        with self.db.reader() as conn:
            rows = conn.execute("SELECT * FROM datasets ORDER BY id DESC").fetchall()
        return [
            Dataset(
                int(row["id"]),
                row["name"],
                row["source_type"],
                row["source_reference"],
                row["status"],
                int(row["member_count"]),
            )
            for row in rows
        ]

    def member_rows(self, dataset_id: int) -> list[dict]:
        """Return dataset members for local inspection/tests without mutating state."""
        with self.db.reader() as conn:
            rows = conn.execute(
                """SELECT m.*
                   FROM dataset_members dm
                   JOIN members m ON m.id=dm.member_id
                   WHERE dm.dataset_id=?
                   ORDER BY dm.member_id""",
                (dataset_id,),
            ).fetchall()
        return [dict(row) for row in rows]
