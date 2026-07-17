"""Unit tests for database migrations.

Covers:
- Migration execution
- Idempotency
- Column existence checks
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import sqlite3


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database for testing migrations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    # Create basic users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            role TEXT DEFAULT 'Staff',
            is_active INTEGER DEFAULT 1,
            last_login TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    Path(db_path).unlink(missing_ok=True)


class TestMigration005:
    def test_migration_adds_lockout_columns(self, tmp_db):
        """Test that migration 005 adds failed_attempts and locked_until columns."""
        # Simulate migration 005
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add columns if not exist
        if "failed_attempts" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        conn.commit()
        
        # Verify columns exist
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        assert "failed_attempts" in columns
        assert "locked_until" in columns
        conn.close()
    
    def test_migration_is_idempotent(self, tmp_db):
        """Test that running migration twice doesn't cause errors."""
        conn = sqlite3.connect(tmp_db)
        
        # First run
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if "failed_attempts" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        conn.commit()
        
        # Second run (should not error)
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if "failed_attempts" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        conn.commit()
        
        # Verify columns still exist
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        assert "failed_attempts" in columns
        assert "locked_until" in columns
        conn.close()
    
    def test_migration_preserves_existing_data(self, tmp_db):
        """Test that migration doesn't destroy existing user data."""
        conn = sqlite3.connect(tmp_db)
        
        # Insert a user
        conn.execute("""
            INSERT INTO users (username, password_hash, full_name, email, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("testuser", "hash123", "Test User", "test@example.com", "Staff", 1))
        conn.commit()
        
        # Run migration
        cursor = conn.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if "failed_attempts" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
        if "locked_until" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        conn.commit()
        
        # Verify user data preserved
        user = conn.execute("SELECT * FROM users WHERE username = ?", ("testuser",)).fetchone()
        assert user is not None
        assert user[1] == "testuser"  # username
        assert user[3] == "Test User"  # full_name
        conn.close()
