# Telegram Migration Studio — Core V1

Windows desktop application for Telegram account/session management, group-member collection, local datasets, filter/dedup workflows, target pre-check, resumable migration jobs, persistent logs and CSV/XLSX import/export.

The implementation follows the locked Core V1 design. It does **not** rotate accounts to bypass Telegram rate limits. A Telegram server wait overrides the local 3–8 second scheduler and remains tied to the same account/job/candidate.

## Core workflow

```text
Account / Session
      ↓
Resolve source / joined group / import file
      ↓
Get Members → Dataset → Filter / Dedup / 2-file workflow
      ↓
Resolve target → Target pre-check
      ↓
Migration plan
      ↓
Prefetch → Cached InputUser → one-user Invite RPC
      ↓
Classifier → buffered persistence → scheduler → next
      ↓
Persistent results / logs / export / recovery
```

## Architecture guarantees

- Qt thread is for UI/rendering/commands; Telegram RPCs never run there.
- All Telethon clients live on one dedicated asyncio runtime thread.
- SQLite uses WAL and one DBWriter pipeline; critical state is flushed immediately.
- Member scans use pagination, a bounded 4-page queue, backpressure, dedup and checkpoints.
- Access hashes are account-scoped `(account_id, peer_id)`.
- CSV/XLSX is import/export only and never enters the migration hot path.
- Target pre-check distinguishes `COMPLETE`, `PARTIAL` and `UNAVAILABLE` coverage.
- Missing IDs under incomplete coverage become `UNKNOWN_TARGET_STATE`.
- Migration prefetch is bounded; target/member entity resolution is not performed per candidate.
- One candidate is sent per invite RPC.
- `FLOOD_WAIT`/server wait is persisted and wins over local cadence; no wait-evasion account rotation.
- Transient retry policy is 1s → 2s → 4s.
- UI progress is aggregated at roughly 150 ms and member tables are paged Qt Model/View.
- Join/Leave is utility-only; Messenger/Archive/Seeding/Script Runner are outside Core V1.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the detailed design and [`LOCKED_SPEC.md`](LOCKED_SPEC.md) for review guardrails.

## Requirements

- Windows 10/11
- Python 3.13
- PySide6 / Qt 6
- Telethon **1.44.0**
- SQLite
- openpyxl
- Nuitka for standalone Windows packaging

## Development

Fast Windows setup + validation:

```powershell
./scripts/setup_windows.ps1
.\.venv\Scripts\python.exe -m tms
```

Equivalent manual setup:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python scripts/quality_gate.py
python -m ruff check src tests scripts
pytest -q
python -m tms
```

Telegram API credentials can be entered in **Accounts → Telegram API Settings** or supplied through:

```text
TMS_TELEGRAM_API_ID
TMS_TELEGRAM_API_HASH
```

Application state is stored under `%LOCALAPPDATA%\TelegramMigrationStudio\`.

## Build Windows EXE

```powershell
./scripts/build_windows.ps1
```

The build script runs tests + the architecture gate before Nuitka. GitHub Actions includes a Windows CI job and a Windows standalone build job for pull requests, manual runs and `v*` tags.

## Scope

Included: account/session + OTP/2FA, multi-account management, group resolver/joined groups, member scanner, CSV/XLSX import, datasets and 1/2-file workflows, local filters/dedup, target pre-check, migration planner/executor, pause/resume/recovery, persistent logs/results/export, Join/Leave utility.

Excluded by design: messenger campaigns, message archive, seeding, proxy/account rotation intended to evade server limits, and script runner.

For usage steps, see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md). Validation details are in [`docs/VALIDATION.md`](docs/VALIDATION.md).
