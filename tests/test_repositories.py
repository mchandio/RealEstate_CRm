"""Unit tests for crm_core/repositories.py - Repository Pattern implementation.

Covers:
- RepositoryFactory creation
- User repository operations
- Deal repository operations
- Audit repository logging
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import sqlite3

# Skip entire module if crm_core.repositories is not available
pytest.importorskip("crm_core.repositories", reason="crm_core.repositories not available")


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create required tables
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
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rent_availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT,
            contact TEXT,
            location TEXT,
            monthly_rent REAL,
            status TEXT,
            workflow_stage TEXT DEFAULT 'Lead',
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id INTEGER,
            action TEXT,
            username TEXT,
            summary TEXT,
            details TEXT,
            created_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    Path(db_path).unlink(missing_ok=True)


class TestRepositoryFactory:
    def test_factory_creates_repositories(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        assert factory is not None

    def test_factory_clients_property(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        assert factory.clients is not None

    def test_factory_properties_property(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        assert factory.properties is not None

    def test_factory_users_property(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        assert factory.users is not None


class TestUserRepository:
    def test_get_by_username(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        
        # Insert a user directly
        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            ("testuser", "hash123", "Test User", "test@example.com", "Staff", 1)
        )
        conn.commit()
        conn.close()
        
        user_repo = factory.users
        user = user_repo.get_by_username("testuser")
        assert user is not None
        assert user["username"] == "testuser"

    def test_get_by_username_not_found(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        user_repo = factory.users
        user = user_repo.get_by_username("nonexistent")
        assert user is None


class TestDealRepository:
    def test_get_active_deals(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        
        # Insert test deal
        conn = sqlite3.connect(tmp_db)
        conn.execute(
            "INSERT INTO rent_availability (owner_name, contact, location, monthly_rent, status, is_deleted) VALUES (?, ?, ?, ?, ?, ?)",
            ("Owner1", "03001234567", "DHA", 50000, "Available", 0)
        )
        conn.commit()
        conn.close()
        
        deal_repo = factory.get_repository("rent_availability")
        deals = deal_repo.get_active_deals()
        assert len(deals) >= 1


class TestAuditRepository:
    def test_log_action(self, tmp_db):
        from crm_core.repositories import RepositoryFactory
        factory = RepositoryFactory(tmp_db)
        
        audit_repo = factory.audit
        result = audit_repo.log_action(
            table_name="test_table",
            record_id=1,
            action="create",
            username="admin",
            summary="Test creation",
            details={"key": "value"}
        )
        assert result is not None
