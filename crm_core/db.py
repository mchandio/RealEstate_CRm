"""Small SQLite data-access helpers shared by desktop and reporting code.

All write operations (execute, insert) now use proper transaction handling
with automatic rollback on error, as recommended in Section 22 of the
engineering audit (Missing Transactions).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


class SQLiteRepository:
    """Thin wrapper around sqlite3 that returns rows as dictionaries.
    
    All write operations use proper transaction handling with automatic
    rollback on error to prevent data corruption.
    """

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

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for transactions with automatic commit/rollback.
        
        Usage:
            with repo.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
                # Auto-commits on success, auto-rollbacks on exception
        """
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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
        """Execute a write query with automatic commit/rollback.
        
        On success, commits the transaction.
        On error, rolls back and re-raises the exception.
        """
        with self.connect() as conn:
            try:
                cur = conn.execute(query, params or ())
                conn.commit()
                return cur.rowcount
            except Exception:
                conn.rollback()
                raise

    def insert(self, query: str, params: Sequence[object] | None = None) -> int:
        """Execute an INSERT query and return the lastrowid.
        
        On success, commits the transaction.
        On error, rolls back and re-raises the exception.
        """
        with self.connect() as conn:
            try:
                cur = conn.execute(query, params or ())
                conn.commit()
                return cur.lastrowid
            except Exception:
                conn.rollback()
                raise

    def table_columns(self, table: str) -> set[str]:
        rows = self.fetch_all(f"PRAGMA table_info({table})")
        return {row["name"] for row in rows}

    def table_count(self, table: str) -> int:
        row = self.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
        return int(row["count"]) if row else 0

    def table_counts(self, tables: Iterable[str]) -> dict[str, int]:
        return {table: self.table_count(table) for table in tables}
