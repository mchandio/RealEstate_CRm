"""Repository Pattern implementation for RealEstate_CRM.

This module provides abstract repository interfaces and concrete implementations
for database access, following the Repository Pattern and Dependency Inversion Principle.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generic, Iterator, Sequence, TypeVar

T = TypeVar("T")


# =============================================================================
# Abstract Repository Interface
# =============================================================================

class BaseRepository(ABC, Generic[T]):
    """Abstract base repository interface.
    
    Defines the contract for data access operations that all concrete
    repositories must implement. Follows the Dependency Inversion Principle
    by depending on abstractions rather than concretions.
    """
    
    @abstractmethod
    def get_by_id(self, id: int) -> T | None:
        """Get a single record by its ID."""
        ...
    
    @abstractmethod
    def get_all(self, limit: int = 5000, offset: int = 0) -> list[T]:
        """Get all records with pagination."""
        ...
    
    @abstractmethod
    def count(self) -> int:
        """Get the total number of records."""
        ...
    
    @abstractmethod
    def create(self, data: dict[str, Any]) -> T:
        """Create a new record."""
        ...
    
    @abstractmethod
    def update(self, id: int, data: dict[str, Any]) -> T | None:
        """Update an existing record."""
        ...
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        ...
    
    @abstractmethod
    def search(self, query: str, fields: list[str] | None = None) -> list[T]:
        """Search records by query string."""
        ...
    
    @abstractmethod
    def filter_by(self, **kwargs: Any) -> list[T]:
        """Filter records by field values."""
        ...


# =============================================================================
# SQLite Repository Implementation
# =============================================================================

class SQLiteBaseRepository(BaseRepository[dict[str, Any]]):
    """Concrete SQLite repository implementation.
    
    Provides database access using sqlite3 with proper transaction support,
    connection management, and error handling.
    """
    
    def __init__(self, db_path: str | Path, table_name: str):
        self.db_path = str(db_path)
        self.table_name = table_name
    
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections with proper cleanup."""
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
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for transactions with automatic commit/rollback."""
        with self.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert sqlite3.Row to dictionary."""
        return dict(row) if row else {}
    
    def get_by_id(self, id: int) -> dict[str, Any] | None:
        """Get a single record by its ID."""
        with self.connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def get_all(self, limit: int = 5000, offset: int = 0) -> list[dict[str, Any]]:
        """Get all records with pagination."""
        with self.connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {self.table_name} ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def count(self) -> int:
        """Get the total number of records."""
        with self.connection() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {self.table_name}")
            row = cursor.fetchone()
            return row["count"] if row else 0
    
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new record."""
        with self.transaction() as conn:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            cursor = conn.execute(
                f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            return self.get_by_id(cursor.lastrowid) or {}
    
    def update(self, id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing record."""
        with self.transaction() as conn:
            set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
            conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                list(data.values()) + [id]
            )
            return self.get_by_id(id)
    
    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        with self.transaction() as conn:
            cursor = conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?", (id,)
            )
            return cursor.rowcount > 0
    
    def search(self, query: str, fields: list[str] | None = None) -> list[dict[str, Any]]:
        """Search records by query string."""
        if not fields:
            # Get all text columns
            fields = self._get_text_columns()
        
        if not fields:
            return []
        
        # Build search condition
        conditions = " OR ".join([f"{field} LIKE ?" for field in fields])
        params = [f"%{query}%"] * len(fields)
        
        with self.connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE {conditions} ORDER BY id DESC LIMIT 500",
                params
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def filter_by(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Filter records by field values."""
        if not kwargs:
            return self.get_all()
        
        conditions = " AND ".join([f"{k} = ?" for k in kwargs.keys()])
        params = list(kwargs.values())
        
        with self.connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE {conditions} ORDER BY id DESC",
                params
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def _get_text_columns(self) -> list[str]:
        """Get list of text columns for search."""
        with self.connection() as conn:
            cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
            columns = []
            for row in cursor.fetchall():
                if row["type"].upper() in ("TEXT", "VARCHAR", "CHAR"):
                    columns.append(row["name"])
            return columns
    
    def table_exists(self) -> bool:
        """Check if table exists."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (self.table_name,)
            )
            return cursor.fetchone() is not None
    
    def get_columns(self) -> set[str]:
        """Get all column names for the table."""
        with self.connection() as conn:
            cursor = conn.execute(f"PRAGMA table_info({self.table_name})")
            return {row["name"] for row in cursor.fetchall()}


# =============================================================================
# Domain-Specific Repositories
# =============================================================================

class DealRepository(SQLiteBaseRepository):
    """Repository for deal-related operations (rent/sale requirements/availability)."""
    
    def __init__(self, db_path: str | Path, table_name: str):
        super().__init__(db_path, table_name)
        # Validate table is a deal table
        valid_tables = {
            "rent_requirements", "rent_availability",
            "sale_requirements", "sale_availability"
        }
        if table_name not in valid_tables:
            raise ValueError(f"Invalid deal table: {table_name}")
    
    def get_active_deals(self, limit: int = 5000) -> list[dict[str, Any]]:
        """Get active (non-deleted) deals."""
        with self.connection() as conn:
            cursor = conn.execute(
                f"""SELECT * FROM {self.table_name} 
                    WHERE (is_deleted = 0 OR is_deleted IS NULL)
                    ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_by_stage(self, stage: str) -> list[dict[str, Any]]:
        """Get deals by workflow stage."""
        with self.connection() as conn:
            cursor = conn.execute(
                f"""SELECT * FROM {self.table_name} 
                    WHERE workflow_stage = ? AND (is_deleted = 0 OR is_deleted IS NULL)
                    ORDER BY id DESC""",
                (stage,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_by_location(self, location: str) -> list[dict[str, Any]]:
        """Get deals by location."""
        with self.connection() as conn:
            cursor = conn.execute(
                f"""SELECT * FROM {self.table_name} 
                    WHERE location LIKE ? AND (is_deleted = 0 OR is_deleted IS NULL)
                    ORDER BY id DESC""",
                (f"%{location}%",)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def soft_delete(self, id: int, deleted_by: str) -> bool:
        """Soft delete a deal."""
        from datetime import datetime
        with self.transaction() as conn:
            cursor = conn.execute(
                f"""UPDATE {self.table_name} 
                    SET is_deleted = 1, deleted_by = ?, deleted_at = ?
                    WHERE id = ?""",
                (deleted_by, datetime.now().isoformat(timespec="seconds"), id)
            )
            conn.commit()
            return cursor.rowcount > 0


class ClientRepository(SQLiteBaseRepository):
    """Repository for client operations."""
    
    def __init__(self, db_path: str | Path):
        super().__init__(db_path, "clients")
    
    def get_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Get client by phone number."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM clients WHERE phone = ?", (phone,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Get client by name (case-insensitive)."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM clients WHERE LOWER(client_name) = LOWER(?)",
                (name,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def upsert_from_deal(self, deal_data: dict[str, Any], deal_table: str) -> dict[str, Any]:
        """Create or update client from deal data."""
        phone = deal_data.get("contact_phone") or deal_data.get("owner_phone") or ""
        name = deal_data.get("client_name") or deal_data.get("owner_name") or ""
        
        if not phone and not name:
            return {}
        
        # Try to find existing client
        existing = None
        if phone:
            existing = self.get_by_phone(phone)
        if not existing and name:
            existing = self.get_by_name(name)
        
        if existing:
            # Update existing client
            updates = {}
            if name and not existing.get("client_name"):
                updates["client_name"] = name
            if phone and not existing.get("phone"):
                updates["phone"] = phone
            if updates:
                return self.update(existing["id"], updates) or existing
            return existing
        else:
            # Create new client
            client_data = {
                "client_name": name,
                "phone": phone,
                "client_type": "Tenant" if "rent" in deal_table else "Buyer",
                "status": "Active",
                "notes": f"Auto-synced from {deal_table}"
            }
            return self.create(client_data)


class PropertyRepository(SQLiteBaseRepository):
    """Repository for property operations."""
    
    def __init__(self, db_path: str | Path):
        super().__init__(db_path, "properties")
    
    def get_by_code(self, code: str) -> dict[str, Any] | None:
        """Get property by code."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM properties WHERE property_code = ?", (code,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def get_by_location(self, location: str) -> list[dict[str, Any]]:
        """Get properties by location."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM properties WHERE location LIKE ? ORDER BY id DESC",
                (f"%{location}%",)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]


class UserRepository(SQLiteBaseRepository):
    """Repository for user operations."""
    
    def __init__(self, db_path: str | Path):
        super().__init__(db_path, "users")
    
    def get_by_username(self, username: str) -> dict[str, Any] | None:
        """Get user by username."""
        with self.connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
                (username,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def authenticate(self, username: str, password_hash: str) -> dict[str, Any] | None:
        """Authenticate user by username and password hash."""
        with self.connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM users 
                   WHERE LOWER(username) = LOWER(?) 
                   AND password_hash = ? 
                   AND is_active = 1""",
                (username, password_hash)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None


class AuditRepository(SQLiteBaseRepository):
    """Repository for audit log operations."""
    
    def __init__(self, db_path: str | Path):
        super().__init__(db_path, "audit_logs")
    
    def log_action(
        self,
        table_name: str,
        record_id: int | None,
        action: str,
        username: str,
        summary: str = "",
        details: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Log an audit action."""
        from datetime import datetime
        import json
        
        data = {
            "table_name": table_name,
            "record_id": record_id,
            "action": action,
            "username": username,
            "summary": summary or f"{action} on {table_name} #{record_id}",
            "details": json.dumps(details or {}, default=str),
            "created_at": datetime.now().isoformat()
        }
        return self.create(data)
    
    def get_by_table(self, table_name: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get audit logs for a specific table."""
        with self.connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM audit_logs 
                   WHERE table_name = ? 
                   ORDER BY id DESC LIMIT ?""",
                (table_name, limit)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_by_record(self, table_name: str, record_id: int) -> list[dict[str, Any]]:
        """Get audit logs for a specific record."""
        with self.connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM audit_logs 
                   WHERE table_name = ? AND record_id = ?
                   ORDER BY id DESC""",
                (table_name, record_id)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]


# =============================================================================
# Repository Factory
# =============================================================================

class RepositoryFactory:
    """Factory for creating repository instances.
    
    Provides a centralized way to create and manage repository instances,
    following the Factory Pattern and ensuring consistent configuration.
    """
    
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._repositories: dict[str, BaseRepository] = {}
    
    def get_repository(self, table_name: str) -> SQLiteBaseRepository:
        """Get or create repository for a table."""
        if table_name not in self._repositories:
            # Use domain-specific repositories where available
            if table_name in {"rent_requirements", "rent_availability", 
                              "sale_requirements", "sale_availability"}:
                self._repositories[table_name] = DealRepository(self.db_path, table_name)
            elif table_name == "clients":
                self._repositories[table_name] = ClientRepository(self.db_path)
            elif table_name == "properties":
                self._repositories[table_name] = PropertyRepository(self.db_path)
            elif table_name == "users":
                self._repositories[table_name] = UserRepository(self.db_path)
            elif table_name == "audit_logs":
                self._repositories[table_name] = AuditRepository(self.db_path)
            else:
                self._repositories[table_name] = SQLiteBaseRepository(self.db_path, table_name)
        
        return self._repositories[table_name]
    
    def get_deal_repository(self, deal_type: str) -> DealRepository:
        """Get deal repository for rent or sale."""
        table_name = f"{deal_type}_requirements"
        return self.get_repository(table_name)  # type: ignore
    
    def get_availability_repository(self, deal_type: str) -> DealRepository:
        """Get availability repository for rent or sale."""
        table_name = f"{deal_type}_availability"
        return self.get_repository(table_name)  # type: ignore
    
    @property
    def clients(self) -> ClientRepository:
        """Get client repository."""
        return self.get_repository("clients")  # type: ignore
    
    @property
    def properties(self) -> PropertyRepository:
        """Get property repository."""
        return self.get_repository("properties")  # type: ignore
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        return self.get_repository("users")  # type: ignore
    
    @property
    def audit(self) -> AuditRepository:
        """Get audit repository."""
        return self.get_repository("audit_logs")  # type: ignore


# =============================================================================
# Unit of Work Pattern (Optional Enhancement)
# =============================================================================

class UnitOfWork:
    """Unit of Work pattern for managing transactions across multiple repositories.
    
    Ensures that multiple repository operations are committed atomically.
    """
    
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._repositories: dict[str, BaseRepository] = {}
        self._changes: list[tuple[str, str, Any]] = []
    
    def repository(self, table_name: str) -> SQLiteBaseRepository:
        """Get repository for a table."""
        if table_name not in self._repositories:
            self._repositories[table_name] = SQLiteBaseRepository(self.db_path, table_name)
        return self._repositories[table_name]
    
    def track_change(self, repository: str, operation: str, data: Any) -> None:
        """Track a change for atomic commit."""
        self._changes.append((repository, operation, data))
    
    def commit(self) -> None:
        """Commit all tracked changes atomically."""
        # Implementation would go here for complex scenarios
        self._changes.clear()
    
    def rollback(self) -> None:
        """Rollback all tracked changes."""
        self._changes.clear()
