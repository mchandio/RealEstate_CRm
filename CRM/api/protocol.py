"""AppContext protocol defining what API servers need from the application.

Extends AppHost with additional API-specific methods.
Decouples API handlers from the full ModernCRMWindow.
"""
from __future__ import annotations

from typing import Any

from CRM.protocols import AppHost


class AppContext(AppHost):
    """Interface that API servers use to interact with the CRM application.

    Extends AppHost with API-specific methods like local_service_url
    and pipeline operations.
    """

    @property
    def local_service_url(self) -> str:
        """Full URL of the local desktop API."""
        ...

    def pipeline_rows(self, stage: str | None = None) -> list[dict]:
        """Return pipeline rows optionally filtered by stage."""
        ...

    def pipeline_counts(self) -> dict[str, int]:
        """Return counts of records by deal stage."""
        ...
