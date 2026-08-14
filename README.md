# Telegram Migration Studio — Core V1

Windows desktop application for managing Telegram accounts/sessions, collecting group members into local datasets, filtering/deduplicating data, running 1-file / 2-file workflows, pre-checking a target group, and executing resumable migration jobs.

This repository implements the locked Core V1 architecture. The application **does not** rotate accounts to bypass Telegram rate limits. `FLOOD_WAIT` always wins over the local scheduler and the same account/job remains waiting until the server wait expires.

## Locked hot path

```text
PREFETCHED CANDIDATE
        ↓
RAM VALIDATION
        ↓
CACHED INPUT USER
        ↓
INVITE RPC
        ↓
RESULT CLASSIFIER
        ↓
MEMORY UPDATE
        ↓
BUFFER RESULT
        ↓
3–8s SCHEDULER
        ↓
NEXT
```

## Architecture invariants

1. UI never calls Telegram directly.
2. UI never writes SQLite directly.
3. `TelegramClient` instances never leave the network runtime thread.
4. Migration never reads Excel/CSV.
5. Target is resolved once per operation, never once per candidate.
6. Filters are local and never call Telegram.
7. SQLite has one writer pipeline.
8. Access hashes are cached by `(account_id, peer_id)`.
9. Job/checkpoint state is persistent.
10. `FLOOD_WAIT` is respected; a waiting account is not replaced to evade it.
11. Large tables are paged Qt Model/View tables.
12. Messenger/archive/script-runner are intentionally outside Core V1.

## Stack

- Python 3.13
- PySide6 / Qt 6
- Telethon 1.44.x
- SQLite WAL
- XLSX/CSV import-export
- Nuitka Windows packaging

## Development

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
python -m tms
```

Telegram API credentials are supplied through environment variables or the first-run settings dialog:

```text
TMS_TELEGRAM_API_ID
TMS_TELEGRAM_API_HASH
```

Application data is stored under `%LOCALAPPDATA%/TelegramMigrationStudio/`.

## Build Windows EXE

```powershell
./scripts/build_windows.ps1
```

GitHub Actions also builds a Windows artifact for every pull request and tagged release.

## Core scope

Included: Account/Session, multi-account management, group resolver/joined-group browser, participant scanner, datasets, filters/deduplication, 1-file/2-file workflows, target pre-check, migration planner/executor, job progress/checkpoint/recovery, logs/results/export, Join/Leave utility.

Intentionally excluded from Core V1: messenger campaigns, message archive, seeding and script runner.
