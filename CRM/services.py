"""CRM Services Layer.

This module provides the service layer for the CRM application, implementing
business logic and coordinating between repositories and UI components.

Follows the Service Layer pattern and Dependency Inversion Principle.
All data access is now performed through the Repository Pattern.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Any
from crm_core import DB_PATH
from crm_core.auth import (
    hash_password, verify_password, needs_rehash, rehash_to_bcrypt,
    validate_password_strength, is_account_locked, record_failed_login, reset_failed_attempts,
)
from crm_core.db import SQLiteRepository
from crm_core.repositories import (
    RepositoryFactory,
    SQLiteBaseRepository,
    DealRepository,
    ClientRepository,
    PropertyRepository,
    UserRepository,
    AuditRepository,
)
from crm_core.constants import EXPENSE_CATEGORIES
from CRM.utils import setting_lines


class CRMServices:
    """Main CRM services providing business logic and data access.
    
    Uses Repository Pattern for data access and follows
    Dependency Inversion Principle by depending on abstractions.
    All data access is now performed through repositories.
    """
    
    def __init__(self):
        # Legacy repo for backward compatibility with setting_lines and other callers
        self.repo = SQLiteRepository(DB_PATH)
        self._repo_factory = RepositoryFactory(DB_PATH)
        self._deal_repos: dict[str, DealRepository] = {}
    
    # =========================================================================
    # Repository Properties (Dependency Inversion)
    # =========================================================================
    
    @property
    def clients(self) -> ClientRepository:
        """Get client repository."""
        return self._repo_factory.clients
    
    @property
    def properties(self) -> PropertyRepository:
        """Get property repository."""
        return self._repo_factory.properties
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        return self._repo_factory.users
    
    @property
    def audit(self) -> AuditRepository:
        """Get audit repository."""
        return self._repo_factory.audit
    
    def get_deal_repository(self, table: str) -> DealRepository:
        """Get repository for a specific deal table."""
        if table not in self._deal_repos:
            self._deal_repos[table] = self._repo_factory.get_repository(table)  # type: ignore
        return self._deal_repos[table]
    
    def get_repository(self, table: str) -> SQLiteBaseRepository:
        """Get repository for any table."""
        return self._repo_factory.get_repository(table)
    
    # =========================================================================
    # Generic Data Access Methods (Delegated to Legacy Repository)
    # =========================================================================
    
    def fetch_all(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict]:
        """Fetch all records matching query. For backward compatibility."""
        return self.repo.fetch_all(query, params)
    
    def fetch_one(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> dict | None:
        """Fetch one record matching query. For backward compatibility."""
        return self.repo.fetch_one(query, params)
    
    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        """Execute a query. For backward compatibility."""
        return self.repo.execute(query, params)
    
    def insert(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        """Insert a record and return lastrowid. For backward compatibility."""
        return self.repo.insert(query, params)
    
    # =========================================================================
    # Settings Operations (Using Repository)
    # =========================================================================
    
    def settings_get(self, key: str, default: str = "") -> str:
        """Get a setting value by key."""
        row = self.repo.fetch_one("SELECT value FROM app_settings WHERE key=?", (key,))
        return str(row["value"]) if row else default
    
    def settings_set(self, key: str, value: str) -> None:
        """Set a setting value."""
        self.repo.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, value))
    
    def expense_categories(self) -> list[str]:
        """Get expense categories from settings."""
        return setting_lines(self, "expense_categories", list(EXPENSE_CATEGORIES))
    
    def table_columns(self, table: str) -> set[str]:
        """Get column names for a table."""
        return self._repo_factory.get_repository(table).get_columns()
    
    # =========================================================================
    # Approval Operations (Using Repository)
    # =========================================================================
    
    def submit_approval(
        self,
        action: str,
        table_name: str,
        record_id: int | None,
        payload: dict[str, Any],
        requested_by: str,
    ) -> int:
        """Submit an approval request."""
        repo = self._repo_factory.get_repository("pending_approvals")
        data = {
            "action": action,
            "table_name": table_name,
            "record_id": record_id,
            "payload": json.dumps(payload, default=str),
            "requested_by": requested_by,
            "requested_at": datetime.now().isoformat(timespec="seconds"),
            "status": "Pending"
        }
        result = repo.create(data)
        return result.get("id", 0)
    
    def pending_approvals(self) -> list[dict]:
        """Get all pending approvals."""
        repo = self._repo_factory.get_repository("pending_approvals")
        return repo.filter_by(status="Pending")
    
    def review_approval(self, approval_id: int, approved: bool, reviewed_by: str, comment: str = "") -> None:
        """Review an approval request."""
        repo = self._repo_factory.get_repository("pending_approvals")
        status = "Approved" if approved else "Rejected"
        repo.update(approval_id, {
            "status": status,
            "reviewed_by": reviewed_by,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "review_comment": comment
        })
    
    # =========================================================================
    # Authentication Operations (Using UserRepository)
    # =========================================================================
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt (with SHA-256 fallback)."""
        return hash_password(password)
    
    def login(self, username: str, password: str) -> dict | None:
        """Authenticate user by username and password.
        
        Supports both bcrypt and legacy SHA-256 hashes.
        On successful login with SHA-256, automatically rehashes to bcrypt
        for improved security (Section 10 engineering audit recommendation).
        
        Account lockout is enforced after MAX_FAILED_ATTEMPTS (Section 8).
        """
        username = str(username or "").strip()
        
        # Check account lockout (Section 8: Account Lockout)
        locked, lock_msg = is_account_locked(self.repo.fetch_one, self.repo.execute, username)
        if locked:
            self._log_login(None, "Locked")
            return None
        
        # Get user repository
        user_repo = self.users
        
        # Find user by username
        row = user_repo.get_by_username(username)
        
        # Verify password (supports both bcrypt and SHA-256)
        if row and verify_password(password, row.get("password_hash", "")):
            # Reset failed attempts on successful login
            reset_failed_attempts(self.repo.execute, username)
            
            # Update last login
            user_repo.update(row["id"], {"last_login": datetime.now().isoformat()})
            
            # Auto-rehash SHA-256 to bcrypt on successful login
            current_hash = row.get("password_hash", "")
            if needs_rehash(current_hash):
                new_hash = rehash_to_bcrypt(password)
                if new_hash:
                    self.repo.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (new_hash, row["id"])
                    )
            
            # Log successful login
            self._log_login(row["id"], "Success")
            
            return row
        
        # Record failed login attempt (Section 8: Account Lockout)
        record_failed_login(self.repo.execute, self.repo.fetch_one, username)
        
        # Log failed login
        self._log_login(None, "Failed")
        return None
    
    def _log_login(self, user_id: int | None, status: str) -> None:
        """Log a login attempt."""
        self.execute(
            "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
            (user_id, datetime.now(), status)
        )
    
    def create_user(self, username: str, password: str, full_name: str, email: str, role: str) -> tuple[bool, str]:
        """Create a new user with password strength validation (Section 8)."""
        username = str(username or "").strip()
        
        if not username:
            return False, "Username is required."
        
        # Validate password strength (Section 8: Password Strength Policy)
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return False, error_msg
        
        # Check if username already exists
        user_repo = self.users
        if user_repo.get_by_username(username):
            return False, "Username already exists."
        
        # Create user
        user_data = {
            "username": username,
            "password_hash": self.hash_password(password),
            "full_name": full_name,
            "email": email,
            "role": role,
            "is_active": 1,
            "failed_attempts": 0,
            "locked_until": None,
            "created_at": datetime.now().isoformat()
        }
        user_repo.create(user_data)
        return True, "User created."
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """Change user password with strength validation (Section 8)."""
        user_repo = self.users
        
        # Get user
        row = user_repo.get_by_id(user_id)
        if not row:
            return False, "User not found."
        
        # Verify old password (supports both bcrypt and SHA-256)
        if not verify_password(old_password, row.get("password_hash", "")):
            return False, "Current password is incorrect."
        
        # Validate new password strength (Section 8: Password Strength Policy)
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg
        
        # Update password (always hash with bcrypt)
        user_repo.update(user_id, {"password_hash": hash_password(new_password)})
        return True, "Password changed."
    
    # =========================================================================
    # Deal Operations (Using DealRepository)
    # =========================================================================
    
    def get_deal(self, table: str, id: int) -> dict | None:
        """Get a deal by table and ID."""
        repo = self.get_deal_repository(table)
        return repo.get_by_id(id)
    
    def get_active_deals(self, table: str, limit: int = 5000) -> list[dict]:
        """Get active deals for a table."""
        repo = self.get_deal_repository(table)
        return repo.get_active_deals(limit)
    
    def create_deal(self, table: str, data: dict[str, Any], username: str = "") -> dict:
        """Create a new deal."""
        repo = self.get_deal_repository(table)
        if username:
            data["created_by"] = username
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        return repo.create(data)
    
    def update_deal(self, table: str, id: int, data: dict[str, Any], username: str = "") -> dict | None:
        """Update an existing deal."""
        repo = self.get_deal_repository(table)
        if username:
            data["last_edited_by"] = username
            data["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
        return repo.update(id, data)
    
    def delete_deal(self, table: str, id: int, username: str = "") -> bool:
        """Delete a deal (soft delete)."""
        repo = self.get_deal_repository(table)
        return repo.soft_delete(id, username)
    
    def search_deals(self, table: str, query: str) -> list[dict]:
        """Search deals by query."""
        repo = self.get_deal_repository(table)
        return repo.search(query)
    
    # =========================================================================
    # Client Operations (Using ClientRepository)
    # =========================================================================
    
    def get_client(self, id: int) -> dict | None:
        """Get a client by ID."""
        return self.clients.get_by_id(id)
    
    def get_client_by_phone(self, phone: str) -> dict | None:
        """Get a client by phone number."""
        return self.clients.get_by_phone(phone)
    
    def create_client(self, data: dict[str, Any]) -> dict:
        """Create a new client."""
        return self.clients.create(data)
    
    def update_client(self, id: int, data: dict[str, Any]) -> dict | None:
        """Update an existing client."""
        return self.clients.update(id, data)
    
    def sync_client_from_deal(self, deal_data: dict[str, Any], deal_table: str) -> dict | None:
        """Sync client data from a deal."""
        return self.clients.upsert_from_deal(deal_data, deal_table)
    
    def search_clients(self, query: str) -> list[dict]:
        """Search clients by query."""
        return self.clients.search(query)
    
    # =========================================================================
    # Property Operations (Using PropertyRepository)
    # =========================================================================
    
    def get_property(self, id: int) -> dict | None:
        """Get a property by ID."""
        return self.properties.get_by_id(id)
    
    def get_property_by_code(self, code: str) -> dict | None:
        """Get a property by code."""
        return self.properties.get_by_code(code)
    
    def create_property(self, data: dict[str, Any]) -> dict:
        """Create a new property."""
        return self.properties.create(data)
    
    def update_property(self, id: int, data: dict[str, Any]) -> dict | None:
        """Update an existing property."""
        return self.properties.update(id, data)
    
    def search_properties(self, query: str) -> list[dict]:
        """Search properties by query."""
        return self.properties.search(query)
    
    # =========================================================================
    # Audit Operations (Using AuditRepository)
    # =========================================================================
    
    def log_audit(
        self,
        table_name: str,
        record_id: int | None,
        action: str,
        username: str,
        summary: str = "",
        details: dict[str, Any] | None = None
    ) -> dict:
        """Log an audit action."""
        return self.audit.log_action(table_name, record_id, action, username, summary, details)
    
    def get_audit_logs(self, table_name: str, limit: int = 100) -> list[dict]:
        """Get audit logs for a table."""
        return self.audit.get_by_table(table_name, limit)
    
    def get_record_history(self, table_name: str, record_id: int) -> list[dict]:
        """Get audit history for a specific record."""
        return self.audit.get_by_record(table_name, record_id)
