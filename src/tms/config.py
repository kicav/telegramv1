from dataclasses import dataclass
import os
from pathlib import Path
from .core.constants import APP_DIR_NAME, DEFAULT_INVITE_INTERVAL_SECONDS


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    data: Path
    sessions: Path
    cache: Path
    temp: Path
    logs: Path
    exports: Path
    backups: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        root = local / APP_DIR_NAME
        paths = cls(
            root=root,
            data=root / "data",
            sessions=root / "sessions",
            cache=root / "cache",
            temp=root / "temp",
            logs=root / "logs",
            exports=root / "exports",
            backups=root / "backups",
        )
        for p in paths.__dict__.values() if hasattr(paths, "__dict__") else (
            paths.root, paths.data, paths.sessions, paths.cache, paths.temp,
            paths.logs, paths.exports, paths.backups
        ):
            Path(p).mkdir(parents=True, exist_ok=True)
        return paths


@dataclass(slots=True)
class Settings:
    api_id: int | None = None
    api_hash: str | None = None
    invite_interval_seconds: float = DEFAULT_INVITE_INTERVAL_SECONDS

    @classmethod
    def from_environment(cls) -> "Settings":
        raw_id = os.getenv("TMS_TELEGRAM_API_ID")
        return cls(
            api_id=int(raw_id) if raw_id else None,
            api_hash=os.getenv("TMS_TELEGRAM_API_HASH"),
        )
