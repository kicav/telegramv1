# Telegram Migration Studio V1.2 — Stable Fast Path (LOCKED)

This file is normative. Do not change the mechanisms below without an explicit new product version.

## Product scope
Desktop Windows application using PySide6 + Telethon + SQLite WAL. Core functions: account/session management, member collection, filtering/merge, INVITE/REMOVE, progress/errors/server waits, pause/resume/recovery, CSV/XLSX import/export.

## Stable Fast Path
Prepare once before START: resolve target, identify type, permission check, target snapshot, filter, validate account-scoped `user_id + access_hash`, remove already-target users, persist plan, fill bounded CandidateBuffer. Hot path is candidate -> cached InputUser/target -> scheduler -> ONE Telegram RPC -> centralized error policy -> RAM result buffer. No entity resolve, source/target scan, spreadsheet work, large SQL, sort/filter or full UI repaint in the hot path.

## Cadence
User target profiles: 3s fast, 5s standard/default, 8s cautious. Recovery begins at 10s and moves 10 -> 8 -> target when stable. Local cadence may become slower. Server restriction always overrides local cadence.

## Rate limits
`FLOOD_WAIT_X`: wait exactly X seconds, persist `waiting_until`, show countdown, retry the same candidate, then enter recovery. Never skip candidate, reset session or retry before the deadline. Rate limit without a duration is `RATE_LIMIT_INDEFINITE`: persist restriction and pause safely; no fixed retry loop.

## Telethon ownership
Connection recovery belongs to Telethon. RPC retries, FloodWait handling and scheduling belong to the application. `TelegramClient` must use `request_retries=0`, `flood_sleep_threshold=0`, `connection_retries=5`, `auto_reconnect=True`, `raise_last_call_error=True`.

## Mutation model
INVITE and REMOVE share one executor. One mutation job per account at a time; local/read tasks remain available. Basic Chat batch Add is blocked by default. Megagroup/Supergroup workflows remain subject to Telegram limits.

## Runtime targets
100k dataset support; filter target <1s; member table 200/page; CandidateBuffer max ~500; scanner queue 4 pages; member DB batch ~250; result batch ~20 or 1s; UI refresh 5–10 Hz; WorkerPool(2); RPC watchdog ~30s; transient retry delays 1/2/4s then fail candidate.

## Persistence/state
SQLite WAL with one DBWriter lane. Connection state and operation state are distinct. Account restrictions persist independently from jobs. Candidate progress/checkpoints are persisted; startup normalizes orphaned jobs. UI commands cannot override a server gate.

## Explicitly out of scope
Proxy rotation, automatic account rotation to evade limits, spam/seeding, Redis, Docker, backend server, microservices, multiprocessing and hidden retry loops.
