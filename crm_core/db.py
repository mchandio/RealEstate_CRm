"""Small SQLite data-access helpers shared by desktop and reporting code."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence


class SQLiteRepository:
    """Thin wrapper around sqlite3 that returns rows as dictionaries."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA wal_autocheckpoint=1000")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA cache_size=5000")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        return conn

    def fetch_all(self, query: str, params: Sequence[object] | None = None) -> list[dict]:
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, query: str, params: Sequence[object] | None = None) -> dict | None:
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            row = cur.fetchone()
            return dict(row) if row else None

    def execute(self, query: str, params: Sequence[object] | None = None) -> int:
        with self.connect() as conn:
            cur = conn.execute(query, params or ())
            conn.commit()
            return cur.rowcount

    def table_columns(self, table: str) -> set[str]:
        rows = self.fetch_all(f"PRAGMA table_info({table})")
        return {row["name"] for row in rows}

    def table_count(self, table: str) -> int:
        row = self.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
        return int(row["count"]) if row else 0

    def table_counts(self, tables: Iterable[str]) -> dict[str, int]:
        return {table: self.table_count(table) for table in tables}
