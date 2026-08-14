# Locked Core V1 specification

This file is a code-review guardrail. A change that violates any invariant below is an architecture bug and must not be merged.

- UI thread performs only rendering/input/progress/commands.
- Telegram network I/O runs on one dedicated asyncio loop thread.
- A Telegram client is reused per active account and is disconnected after idle timeout; startup does not connect every account.
- Participant scans use pagination, normalization, deduplication, bounded queues, checkpoints, progress/cancel and batched persistence.
- Working member data is internal; Excel/CSV are import/export only.
- Dedup identity is Telegram user ID; username is fallback only for imported rows that lack an ID.
- Filter operations are local.
- 2-file operations are UNION / INTERSECTION / DIFFERENCE.
- Target pre-check builds a RAM set of target IDs and records coverage as COMPLETE/PARTIAL/UNAVAILABLE.
- Migration uses one candidate per invite RPC.
- Configurable normal invite interval is 3–8 seconds, default 5 seconds. This is an attempt interval, not a guaranteed-success interval.
- Server wait overrides local scheduling.
- Transient network/server errors retry at 1s, 2s, 4s only; privacy/invalid/already-member are terminal; permission/auth pause the job.
- No account switching to bypass server wait.
- Migration hot path has no XLSX access, large SQL query, sorting, source scan, target resolve, heavy filter or UI rendering.
- SQLite uses WAL and one DBWriter.
- Routine writes are buffered; critical state transitions are flushed immediately.
- Migration has priority over export/statistics and enables Performance Mode.
- UI events are aggregated to roughly 5–10 refreshes/second.
