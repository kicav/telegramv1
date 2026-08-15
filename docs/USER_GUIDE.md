# User Guide

## 1. Install on Windows

Install Python 3.13, then from PowerShell in the repository root:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python -m tms
```

Application data is stored in `%LOCALAPPDATA%\TelegramMigrationStudio\` with separate `data`, `sessions`, `exports`, `logs`, `cache`, `temp` and `backups` directories.

## 2. Configure Telegram API credentials

Open **Accounts → Telegram API Settings**, enter your Telegram API ID and API Hash, then add an account phone number. Credentials can alternatively be provided by `TMS_TELEGRAM_API_ID` and `TMS_TELEGRAM_API_HASH` environment variables.

Select the account, request OTP, then sign in. If Telegram requires 2FA, enter the account password in the sign-in dialog. Session files remain local under the application `sessions` directory.

## 3. Build a source dataset

Open **Source** and choose the same account used for the source group.

- Resolve a public link / `@username`, or load the account's joined groups.
- Enter a dataset name and choose **Get Members**.
- The scan can be cancelled and is checkpointed for recovery.
- Or import a `.csv`, `.xlsx` or `.xlsm` file. Recognized fields include `user_id`, `telegram_user_id`, `access_hash`, `username`, names, phone, bot/deleted flags, activity status and last seen.

For migration with an imported file, rows need a Telegram user ID and an **access hash valid for the selected account**. Username-only rows remain useful for local dataset management but cannot be invited without an ID/access hash.

## 4. Work with datasets

Open **Members** to view data through a paged table. The 2-file workflow supports UNION, INTERSECTION and DIFFERENCE. Results preserve provenance and can be exported to CSV/XLSX.

## 5. Pre-check and plan migration

Open **Migration**:

1. Choose the account and source dataset.
2. Resolve the target group with that account.
3. Run **PRECHECK**.
4. Set optional local filters. Activity and source accept comma-separated exact labels.
5. Press **PLAN** and review Source / Filtered / Already target / Invalid / Ready counts.

If target coverage is partial/unavailable, unknown target membership is kept explicitly as `UNKNOWN_TARGET_STATE`.

## 6. Run migration

Choose an interval from 3 to 8 seconds and press **START**. Each Telegram invite RPC contains one candidate. Pause/stop state is persisted. If Telegram returns a server wait, the job/account waits and retries the same candidate after the wait; it does not rotate accounts to bypass the limit.

The **Jobs** page shows persisted counters/events. Paused migration/scan jobs can be resumed. Migration results and job logs can be exported to CSV/XLSX.

## 7. Utilities

**Tools** contains Join/Leave only. Messenger campaigns, message archive, seeding and script execution are intentionally outside Core V1.

## 8. Build the Windows EXE

```powershell
./scripts/build_windows.ps1
```

The script runs the test suite and architecture quality gate before invoking Nuitka. The standalone output is written under `dist/`.
