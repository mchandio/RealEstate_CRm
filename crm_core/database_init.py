"""Database initialization for safe SQLite multi-user access."""

from __future__ import annotations

import os
import sqlite3
import sys


def initialize_database(db_path: str) -> bool:
    """Initialize SQLite pragmas used by both Desktop and Web CRM."""
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        return False

    print(f"Initializing database: {db_path}")
    try:
        with sqlite3.connect(db_path, timeout=30) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            print(f"   Current journal mode: {cursor.fetchone()[0]}")
            cursor.execute("PRAGMA journal_mode=WAL")
            print(f"   Set journal mode: {cursor.fetchone()[0]}")
            cursor.execute("PRAGMA wal_autocheckpoint=1000")
            cursor.execute("PRAGMA synchronous=FULL")
            cursor.execute("PRAGMA cache_size=5000")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        print("Database initialized successfully.")
        return True
    except Exception as exc:
        print(f"Initialization failed: {exc}")
        return False


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    database_path = os.path.join(project_root, "real_estate_crm.db")
    ok = initialize_database(database_path)
    sys.exit(0 if ok else 1)
