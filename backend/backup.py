"""Small scheduled backup helper for the LAN CRM server."""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import date, datetime
from pathlib import Path

from backend.config import CRM_DB_PATH, DATABASE_URL
from backend.database import SessionLocal
from backend.models import AppSetting
from crm_core.ecosystem import RECOMMENDED_MAX_BACKUPS
from crm_core.paths import OUTPUT_DIR


BACKUP_SETTING_KEY = "last_auto_backup_date"
BACKUP_DIR = OUTPUT_DIR / "backups"
_scheduler_started = False
_scheduler_lock = threading.Lock()


def _settings_get(db, key: str, default: str = "") -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value) if row else default


def _settings_set(db, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


def run_database_backup(reason: str = "manual") -> Path:
    if not DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("Automatic file backup is only available for SQLite deployments")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = BACKUP_DIR / f"{reason}_backup_{stamp}.db"
    source = Path(CRM_DB_PATH)
    with sqlite3.connect(source, timeout=30) as src, sqlite3.connect(destination) as dest:
        src.execute("PRAGMA busy_timeout=30000")
        src.backup(dest, pages=100, sleep=0.001)
    trim_backup_folder()
    return destination


def trim_backup_folder(max_backups: int = RECOMMENDED_MAX_BACKUPS) -> None:
    backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    for old_backup in backups[max_backups:]:
        try:
            old_backup.unlink()
        except OSError:
            pass


def daily_backup_if_due() -> Path | None:
    today = date.today().isoformat()
    db = SessionLocal()
    try:
        last = _settings_get(db, BACKUP_SETTING_KEY)
        if last == today:
            return None
        path = run_database_backup("auto")
        _settings_set(db, BACKUP_SETTING_KEY, today)
        _settings_set(db, "last_auto_backup_path", str(path))
        db.commit()
        return path
    finally:
        db.close()


def backup_status() -> dict[str, str]:
    db = SessionLocal()
    try:
        return {
            "last_auto_backup_date": _settings_get(db, BACKUP_SETTING_KEY),
            "last_auto_backup_path": _settings_get(db, "last_auto_backup_path"),
            "backup_dir": str(BACKUP_DIR),
        }
    finally:
        db.close()


def start_daily_backup_scheduler(interval_seconds: int = 3600) -> None:
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    def worker() -> None:
        while True:
            try:
                daily_backup_if_due()
            except Exception as exc:
                print(f"Daily backup skipped: {exc}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=worker, name="CRM-Daily-Backup", daemon=True)
    thread.start()
