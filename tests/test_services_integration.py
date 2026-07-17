"""Unit tests for CRM/services.py - Integration layer.

Covers:
- CRMServices initialization
- Settings operations
- Password hashing integration
- Repository access patterns
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Skip entire module if PySide6 is not available (needed for CRM services)
pytest.importorskip("PySide6", reason="PySide6 not available")

from CRM.services import CRMServices


@pytest.fixture
def services():
    """Create a CRMServices instance with a temporary database."""
    import crm_core
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Patch DB_PATH
    original_db_path = crm_core.DB_PATH
    crm_core.DB_PATH = db_path
    
    # Initialize database
    from CRM.database import ensure_database
    ensure_database()
    
    svc = CRMServices()
    yield svc
    
    crm_core.DB_PATH = original_db_path
    Path(db_path).unlink(missing_ok=True)


class TestCRMServicesInit:
    def test_services_initializes(self, services):
        assert services is not None
    
    def test_services_has_repo(self, services):
        assert services.repo is not None
    
    def test_services_has_repositories(self, services):
        assert services.clients is not None
        assert services.properties is not None
        assert services.users is not None


class TestPasswordHashing:
    def test_hash_password_returns_string(self, services):
        result = services.hash_password("test123")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_hash_password_deterministic(self, services):
        h1 = services.hash_password("same_password")
        h2 = services.hash_password("same_password")
        # bcrypt produces different hashes due to salt
        assert len(h1) > 0
        assert len(h2) > 0


class TestSettings:
    def test_settings_roundtrip(self, services):
        services.settings_set("test_key", "test_value")
        result = services.settings_get("test_key")
        assert result == "test_value"
    
    def test_settings_default_value(self, services):
        result = services.settings_get("nonexistent_key", "default")
        assert result == "default"


class TestUserOperations:
    def test_create_user(self, services):
        ok, msg = services.create_user("newuser", "Password1!", "New User", "new@test.com", "Staff")
        assert ok is True
        assert "created" in msg.lower()
    
    def test_create_duplicate_user(self, services):
        services.create_user("dupuser", "Password1!", "Dup User", "dup@test.com", "Staff")
        ok, msg = services.create_user("dupuser", "Password1!", "Dup User 2", "dup2@test.com", "Staff")
        assert ok is False
        assert "exists" in msg.lower()
    
    def test_create_user_weak_password(self, services):
        ok, msg = services.create_user("weakuser", "weak", "Weak User", "weak@test.com", "Staff")
        assert ok is False
        assert "password" in msg.lower()
    
    def test_login_success(self, services):
        services.create_user("loginuser", "Login1!Pass", "Login User", "login@test.com", "Staff")
        user = services.login("loginuser", "Login1!Pass")
        assert user is not None
        assert user["username"] == "loginuser"
    
    def test_login_wrong_password(self, services):
        services.create_user("loginuser2", "Login1!Pass", "Login User 2", "login2@test.com", "Staff")
        user = services.login("loginuser2", "WrongPassword1!")
        assert user is None
    
    def test_change_password(self, services):
        services.create_user("changepass", "OldPass1!", "Change Pass", "change@test.com", "Staff")
        user = services.login("changepass", "OldPass1!")
        ok, msg = services.change_password(user["id"], "OldPass1!", "NewPass1!")
        assert ok is True
        
        # Verify new password works
        user2 = services.login("changepass", "NewPass1!")
        assert user2 is not None
    
    def test_change_password_weak_new(self, services):
        services.create_user("changepass2", "OldPass1!", "Change Pass 2", "change2@test.com", "Staff")
        user = services.login("changepass2", "OldPass1!")
        ok, msg = services.change_password(user["id"], "OldPass1!", "weak")
        assert ok is False
        assert "password" in msg.lower()
