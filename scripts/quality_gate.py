"""Dependency-free structural quality gate for the locked Core V1 architecture."""
from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "tms"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def parse_all() -> int:
    count = 0
    for path in sorted(SRC.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"syntax error in {path.relative_to(ROOT)}: {exc}")
        count += 1
    return count


def assert_invariants() -> None:
    ui_files = list((SRC / "ui").rglob("*.py"))
    for path in ui_files:
        text = path.read_text(encoding="utf-8")
        for token in ("TelegramClient", ".gateway.", "INSERT INTO", "DELETE FROM"):
            if token in text:
                fail(f"UI architecture violation ({token}) in {path.relative_to(ROOT)}")

    executor = (SRC / "migration" / "executor.py").read_text(encoding="utf-8")
    for token in ("openpyxl", ".xlsx", ".csv", "resolve_group", ".get_entity(", ".get_input_entity("):
        if token in executor:
            fail(f"migration hot-path violation: {token}")

    gateway = (SRC / "telegram" / "telethon_gateway.py").read_text(encoding="utf-8")
    start = gateway.index("    async def invite_user")
    end = gateway.index("    async def join_group", start)
    invite = gateway[start:end]
    for token in (".get_entity(", ".get_input_entity("):
        if token in invite:
            fail(f"invite hot-path resolves entity: {token}")
    if "InviteToChannelRequest(target_input, [input_user])" not in invite:
        fail("invite RPC must contain exactly one candidate")

    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(SRC))
        if "database.connect()" in text and rel != "runtime/db_writer.py":
            offenders.append(rel)
        if ".db.connect()" in text:
            offenders.append(rel)
    if offenders:
        fail(f"direct DB connection outside DBWriter: {sorted(set(offenders))}")

    schema = SRC / "storage" / "schema.sql"
    if not schema.exists() or schema.stat().st_size < 1000:
        fail("SQLite schema is missing or unexpectedly small")


def main() -> int:
    count = parse_all()
    assert_invariants()
    print(f"[OK] parsed {count} Python modules")
    print("[OK] locked Core V1 architecture invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
