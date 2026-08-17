# Telegram Migration Studio V1.2 — Stable Fast Path

Ứng dụng desktop Windows để quản lý tài khoản Telegram, thu thập/quản lý member, lọc/gộp dữ liệu, thêm hoặc xóa member, theo dõi tiến độ/lỗi/server wait, pause/resume/recovery và import/export CSV/XLSX.

## Kiến trúc
- PySide6 UI tiếng Việt.
- Dedicated asyncio Telegram runtime + Telethon 1.44.
- WorkerPool(2) cho file/DB read/filter.
- SQLite WAL + một DBWriter cho toàn bộ write.
- Prepare/Plan tách khỏi hot path; CandidateBuffer bounded ~500.
- INVITE/REMOVE dùng chung `V12MigrationExecutor`.
- Scheduler 3/5/8s, recovery 10s; server wait luôn ưu tiên.
- RPC watchdog 30s; network retry có giới hạn 1/2/4s.
- Không có proxy/account rotation để né limit, không Redis/Docker/backend.

## Cài đặt phát triển
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python -m pytest -q
python scripts/quality_gate.py
python -m tms
```

API ID/API Hash được cấu hình trong trang **Tài khoản** hoặc qua `TMS_TELEGRAM_API_ID` / `TMS_TELEGRAM_API_HASH`.

## Build Windows
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```
Nuitka tạo standalone build trong `dist/`.

## Luồng sử dụng
1. Tài khoản: thêm số điện thoại, nhập API ID/API Hash, OTP/2FA, kết nối session.
2. Nguồn member: nhập link/@username hoặc chọn group đã tham gia; quét member hoặc import CSV/XLSX.
3. Member: xem/lọc dữ liệu theo trang.
4. Thao tác: chọn tài khoản + dataset + group đích + INVITE/REMOVE + tốc độ; bấm **KIỂM TRA**, xem kế hoạch rồi **BẮT ĐẦU**.
5. Khi Telegram trả `FLOOD_WAIT_X`, ứng dụng chờ đúng X giây và tự recovery 10 -> 8 -> target. Nếu không có duration, job dừng an toàn ở `RATE_LIMITED`.

## Quality gate
`python scripts/quality_gate.py` khóa các invariant: UI không gọi Telegram/SQL write trực tiếp, hot path không resolve/file scan, invite RPC chỉ một candidate, và write DB đi qua DBWriter.

> Sử dụng công cụ theo quyền quản trị và chính sách của Telegram. V1.2 không cố né giới hạn phía server.
