"""Migration 005: Add Account Lockout Columns

This migration adds failed_attempts and locked_until columns to the users table
to support account lockout after failed login attempts (Section 8 - Engineering Audit).

The account lockout feature:
- Tracks consecutive failed login attempts per user
- Locks accounts after MAX_FAILED_ATTEMPTS (5) failures
- Locks for LOCKOUT_DURATION_MINUTES (30) minutes
- Resets on successful login
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Get the database path."""
    try:
        from crm_core import DB_PATH
        return str(DB_PATH)
    except ImportError:
        return "real_estate_crm.db"


def add_lockout_columns(conn: sqlite3.Connection) -> dict[str, int]:
    """Add failed_attempts and locked_until columns to users table."""
    counts = {
        "columns_added": 0,
        "columns_skipped": 0,
    }
    
    cursor = conn.cursor()
    
    # Get existing columns in users table
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # Add failed_attempts column (tracks consecutive failed login attempts)
    if "failed_attempts" not in existing_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
            counts["columns_added"] += 1
            print("  \u2713 Added 'failed_attempts' column to users table")
        except sqlite3.Error as e:
            print(f"  \u2717 Error adding 'failed_attempts': {e}")
    else:
        counts["columns_skipped"] += 1
        print("  - 'failed_attempts' column already exists")
    
    # Add locked_until column (timestamp when lockout expires)
    if "locked_until" not in existing_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
            counts["columns_added"] += 1
            print("  \u2713 Added 'locked_until' column to users table")
        except sqlite3.Error as e:
            print(f"  \u2717 Error adding 'locked_until': {e}")
    else:
        counts["columns_skipped"] += 1
        print("  - 'locked_until' column already exists")
    
    conn.commit()
    return counts


def run_migration(db_path: str | None = None) -> dict[str, int]:
    """Run the migration. Returns counts of columns added."""
    if db_path is None:
        db_path = get_db_path()
    
    print(f"Running migration 005: Add Account Lockout Columns")
    print(f"Database: {db_path}")
    print("-" * 60)
    
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        
        counts = add_lockout_columns(conn)
        conn.close()
        
        print("-" * 60)
        print(f"Migration complete!")
        print(f"  - Columns added: {counts['columns_added']}")
        print(f"  - Columns skipped (already exist): {counts['columns_skipped']}")
        
        return counts
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_migration()
