# Validation

The repository uses layered validation rather than relying on a single happy-path test:

- architecture invariant gate (`scripts/quality_gate.py`)
- unit tests for filters, set operations, state machine, scheduler, result/error policies and resource governance
- integration tests for SQLite/WAL, account lifecycle, member identity upgrade, dataset provenance, planner/coverage, import/export, scanner pipeline and migration execution
- recovery tests for interrupted jobs and persisted server waits
- end-to-end fake-gateway flow from scan → target pre-check → plan → migration
- 100k-member local filter performance test
- resource-warning-clean test runs

## Final local validation snapshot

The final source package was validated with Python 3.13.5 in the available build environment:

- `scripts/quality_gate.py`: **111 production Python modules parsed; locked Core V1 invariants passed**
- `pytest`: **42/42 tests passed** with `ResourceWarning` promoted to an error
- SQLite: `PRAGMA integrity_check = ok`; journal mode is `wal`
- 100,000-member local filter benchmark: comfortably below one second in the validation environment
- unfinished-code marker scan: no `TODO`, `FIXME`, `XXX` or `NotImplementedError` remains in source/tests/scripts

`TelethonGateway` and the Qt desktop shell are deliberately separated from fake-gateway tests so the core can be validated without Telegram credentials. The current Linux validation environment does not contain PySide6, Telethon, Ruff or Nuitka and cannot execute a Windows standalone binary. For that reason, real Telegram authentication/RPC behavior and the Windows GUI/packaging step must be verified on Windows after installing the declared dependencies. The repository includes `scripts/setup_windows.ps1`, `scripts/build_windows.ps1` and Windows GitHub Actions workflows for that final platform-specific validation.

Real Telegram behavior also depends on the selected account's permissions, Telegram server responses and current platform rules. The application preserves server waits and does not attempt to bypass Telegram limits.
