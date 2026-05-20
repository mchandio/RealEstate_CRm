"""Shared filesystem paths used by the CRM apps."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
else:
    APP_ROOT = Path(__file__).resolve().parents[1]
    RESOURCE_ROOT = APP_ROOT

DB_PATH = APP_ROOT / "real_estate_crm.db"
OUTPUT_DIR = APP_ROOT / "outputs"

if getattr(sys, "frozen", False) and not DB_PATH.exists():
    bundled_db = RESOURCE_ROOT / "real_estate_crm.db"
    if bundled_db.exists():
        shutil.copy2(bundled_db, DB_PATH)


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR
