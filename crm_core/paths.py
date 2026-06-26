"""Shared filesystem paths used by the CRM apps."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
else:
    APP_ROOT = Path(__file__).resolve().parents[1]
    RESOURCE_ROOT = APP_ROOT

def _configured_database_path() -> Path:
    env_path = os.getenv("CRM_DB_PATH", "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        return path if path.is_absolute() else APP_ROOT / path

    pointer = APP_ROOT / "database_path.txt"
    if pointer.exists():
        text = pointer.read_text(encoding="utf-8").splitlines()
        for line in text:
            value = line.strip().strip('"')
            if value and not value.startswith("#"):
                path = Path(os.path.expandvars(value)).expanduser()
                return path if path.is_absolute() else APP_ROOT / path

    return APP_ROOT / "real_estate_crm.db"


DB_PATH = _configured_database_path()
OUTPUT_DIR = APP_ROOT / "outputs"

if getattr(sys, "frozen", False) and not DB_PATH.exists():
    bundled_db = RESOURCE_ROOT / "real_estate_crm.db"
    if bundled_db.exists():
        shutil.copy2(bundled_db, DB_PATH)


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
