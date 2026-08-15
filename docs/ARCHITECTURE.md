# Architecture — Telegram Migration Studio Core V1

## Execution domains

The application is a modular monolith with four deliberately separated execution domains:

- **Qt/UI thread** — rendering, user input, paged table models and command dispatch only.
- **Telegram runtime** — one dedicated thread with one `asyncio` loop. Every `TelegramClient` and Telegram RPC stays on this runtime.
- **DBWriter** — one SQLite writer thread. Routine writes are coalesced; critical job/account state writes flush immediately.
- **Worker pool** — bounded threads for CSV/XLSX I/O and larger local transformations/reads that must not block the Telegram loop.

SQLite uses WAL. Repositories may open short-lived read connections, but runtime writes are submitted to `DBWriter`.

## Member collection

`ParticipantScanner` uses a bounded `asyncio.Queue` (4 pages), paginated Telegram reads, local deduplication and batched member persistence. The queue creates backpressure when persistence is slower than Telegram reads. Checkpoints contain the last persisted offset plus accepted/invalid counters, so a paused/recovered scan can safely replay a small suffix without duplicating dataset membership/provenance.

Member identity is Telegram user ID when present. Username is a normalized fallback only for imported rows without an ID. Access hashes are never global: they are cached using `(account_id, peer_id)`.

## Dataset model

Datasets can originate from Telegram groups, CSV/XLSX imports or the three local set operations:

- UNION / MERGE
- INTERSECTION
- DIFFERENCE

`dataset_provenance` records source labels/datasets/groups. A NULL-safe unique index prevents provenance duplication during replay/recovery.

## Target pre-check and planning

Target pre-check reads the target participant IDs once and records one of:

- `COMPLETE`
- `PARTIAL`
- `UNAVAILABLE`

Only IDs known to be in the target are excluded. If coverage is not complete, all other candidates are tagged `UNKNOWN_TARGET_STATE` rather than treated as definitely absent.

The planner performs local-only filtering and persists an ordered migration queue. It automatically excludes duplicates and members already processed by previous jobs for the same target. Source/activity/bot/deleted/username filters do not call Telegram.

## Migration hot path

```text
Prefetched candidate
  -> RAM validation
  -> cached InputUser
  -> exactly one invite RPC
  -> result classification
  -> memory/event update
  -> buffered SQLite persistence
  -> monotonic scheduler
  -> next candidate
```

The hot path never opens Excel/CSV, scans the target, resolves the target, performs a large SQL query, sorts a large dataset or runs a heavy filter.

The normal attempt interval is constrained to 3–8 seconds (default 5). A persisted server wait overrides this cadence. `FLOOD_WAIT` stays on the same account/job/candidate; the runtime does not rotate accounts to evade it. Account-wide persisted wait state is applied to another migration job before it can use the same account.

Transient network/server failures use the locked 1s, 2s, 4s policy. Privacy/invalid/not-eligible are terminal skips, already-member is success-like, permission/auth pause, and unknown errors fail the current item.

## Recovery

Jobs and migration items are persisted. On restart, interrupted work is normalized into resumable states while future server waits remain visible. Migration resumes from persisted item state/checkpoint, not from an in-memory queue.

## UI refresh

Backend code publishes domain events. `EventAggregator` coalesces noisy progress messages and the Qt timer drains events every 150 ms. Large member lists use a paged `QAbstractTableModel`; the UI does not create one widget per member.
