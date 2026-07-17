"""Service Layer interfaces for RealEstate_CRM.

This module defines abstract service interfaces following the Dependency Inversion
Principle and Interface Segregation Principle. Concrete implementations depend
on these abstractions rather than on specific repository implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# =============================================================================
# Service Interfaces (Abstract Base Classes)
# =============================================================================

class DealServiceInterface(ABC):
    """Interface for deal-related business operations."""
    
    @abstractmethod
    def get_deal(self, table: str, id: int) -> dict[str, Any] | None:
        """Get a deal by table and ID."""
        ...
    
    @abstractmethod
    def get_active_deals(self, table: str, limit: int = 5000) -> list[dict[str, Any]]:
        """Get active deals for a table."""
        ...
    
    @abstractmethod
    def create_deal(self, table: str, data: dict[str, Any], username: str) -> dict[str, Any]:
        """Create a new deal."""
        ...
    
    @abstractmethod
    def update_deal(self, table: str, id: int, data: dict[str, Any], username: str) -> dict[str, Any] | None:
        """Update an existing deal."""
        ...
    
    @abstractmethod
    def delete_deal(self, table: str, id: int, username: str) -> bool:
        """Delete a deal (soft delete)."""
        ...
    
    @abstractmethod
    def advance_workflow(self, table: str, id: int, username: str) -> dict[str, Any] | None:
        """Advance deal to next workflow stage."""
        ...
    
    @abstractmethod
    def search_deals(self, table: str, query: str) -> list[dict[str, Any]]:
        """Search deals by query."""
        ...


class ClientServiceInterface(ABC):
    """Interface for client-related business operations."""
    
    @abstractmethod
    def get_client(self, id: int) -> dict[str, Any] | None:
        """Get a client by ID."""
        ...
    
    @abstractmethod
    def get_client_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Get a client by phone number."""
        ...
    
    @abstractmethod
    def create_client(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new client."""
        ...
    
    @abstractmethod
    def update_client(self, id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing client."""
        ...
    
    @abstractmethod
    def sync_from_deal(self, deal_data: dict[str, Any], deal_table: str) -> dict[str, Any]:
        """Sync client data from a deal."""
        ...
    
    @abstractmethod
    def search_clients(self, query: str) -> list[dict[str, Any]]:
        """Search clients by query."""
        ...


class PropertyServiceInterface(ABC):
    """Interface for property-related business operations."""
    
    @abstractmethod
    def get_property(self, id: int) -> dict[str, Any] | None:
        """Get a property by ID."""
        ...
    
    @abstractmethod
    def get_property_by_code(self, code: str) -> dict[str, Any] | None:
        """Get a property by code."""
        ...
    
    @abstractmethod
    def create_property(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new property."""
        ...
    
    @abstractmethod
    def update_property(self, id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing property."""
        ...
    
    @abstractmethod
    def sync_from_availability(self, availability_data: dict[str, Any], table: str) -> dict[str, Any]:
        """Sync property data from availability record."""
        ...
    
    @abstractmethod
    def search_properties(self, query: str) -> list[dict[str, Any]]:
        """Search properties by query."""
        ...


class AuthServiceInterface(ABC):
    """Interface for authentication-related operations."""
    
    @abstractmethod
    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """Authenticate user by username and password."""
        ...
    
    @abstractmethod
    def create_user(self, username: str, password: str, full_name: str, email: str, role: str) -> tuple[bool, str]:
        """Create a new user."""
        ...
    
    @abstractmethod
    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """Change user password."""
        ...
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        ...


class AuditServiceInterface(ABC):
    """Interface for audit logging operations."""
    
    @abstractmethod
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
        ...
    
    @abstractmethod
    def get_audit_logs(self, table_name: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get audit logs for a table."""
        ...
    
    @abstractmethod
    def get_record_history(self, table_name: str, record_id: int) -> list[dict[str, Any]]:
        """Get audit history for a specific record."""
        ...


class ReportingServiceInterface(ABC):
    """Interface for reporting operations."""
    
    @abstractmethod
    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get dashboard summary data."""
        ...
    
    @abstractmethod
    def get_deal_summary(self, deal_type: str) -> dict[str, Any]:
        """Get deal summary for rent or sale."""
        ...
    
    @abstractmethod
    def get_financial_summary(self) -> dict[str, Any]:
        """Get financial summary."""
        ...
