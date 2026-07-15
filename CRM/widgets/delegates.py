"""Item delegates for the CRM application."""

from __future__ import annotations

from PySide6.QtWidgets import QStyledItemDelegate


class WrappingItemDelegate(QStyledItemDelegate):
    """No-op delegate - word wrap handled by QTableWidget.setWordWrap(True)."""
    pass
