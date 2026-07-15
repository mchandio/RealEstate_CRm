"""Application Protocol definitions for decoupling modules from ModernCRMWindow.

Provides type-safe interfaces that modules can depend on instead of the full
window class, reducing tight coupling while maintaining zero wiring cost.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from CRM.services import CRMServices


@runtime_checkable
class AppHost(Protocol):
    """Protocol defining the interface modules need from ModernCRMWindow.
    
    ModernCRMWindow already implements all these methods, so no additional
    wiring is needed. Modules type-hint `host: AppHost` instead of 
    `main: ModernCRMWindow`.
    """
    
    @property
    def services(self) -> CRMServices:
        """CRMServices instance for database operations."""
        ...
    
    @property
    def current_user(self) -> dict[str, Any]:
        """Current logged-in user dict."""
        ...
    
    @property
    def role(self) -> str:
        """Current user's role string."""
        ...
    
    @property
    def currency_symbol(self) -> str:
        """Currency symbol from settings."""
        ...
    
    @property
    def company_name(self) -> str:
        """Company name from settings."""
        ...
    
    def refresh_dashboard(self) -> None:
        """Refresh the dashboard UI."""
        ...
    
    def update_status_bar(self, message: str | None = None) -> None:
        """Update the status bar message."""
        ...
    
    def reload_settings(self) -> None:
        """Reload application settings."""
        ...
    
    def switch_page(self, key: str) -> None:
        """Switch to a page by key."""
        ...
    
    def can_edit(self, permission: str) -> bool:
        """Check if current user has permission to edit."""
        ...
    
    def is_staff_restricted(self) -> bool:
        """Check if current user is staff-restricted."""
        ...
    
    def find_sources(self) -> list[tuple[str, str]]:
        """Get available search sources based on user permissions."""
        ...
    
    def api_allowed_tables(self) -> set[str]:
        """Get tables allowed by API for current user."""
        ...
    
    def api_can_write_table(self, table: str) -> bool:
        """Check if current user can write to the given table via API."""
        ...
    
    def after_record_saved(self, table: str, row_id: int | None) -> None:
        """Hook called after a record is saved/updated."""
        ...
    
    def log_audit(
        self,
        action: str,
        reference_table: str,
        reference_id: int | None,
        old_value: str = "",
        new_value: str = "",
    ) -> None:
        """Log an audit trail entry."""
        ...
    
    def can_delete_record(self, table: str, row_id: int) -> tuple[bool, str]:
        """Check if record can be deleted. Returns (ok, error_message)."""
        ...
