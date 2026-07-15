"""Table widgets and configuration."""
from __future__ import annotations
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QHeaderView, QStyledItemDelegate, QAbstractItemView, QSizePolicy
from typing import Any

class ExcelTableWidget(QTableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setTabKeyNavigation(False)

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            return self._handle_tab_event(event)
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            if self._handle_tab_event(event):
                return
        super().keyPressEvent(event)

    def _handle_tab_event(self, event) -> bool:
        reverse = event.key() == Qt.Key_Backtab or bool(event.modifiers() & Qt.ShiftModifier)
        if self.move_current_cell(reverse=reverse):
            event.accept()
            return True
        return False

    def move_current_cell(self, *, reverse: bool = False) -> bool:
        rows = self.rowCount()
        columns = self.columnCount()
        if rows <= 0 or columns <= 0:
            return False

        current_row = self.currentRow()
        current_column = self.currentColumn()
        step = -1 if reverse else 1
        total = rows * columns

        if current_row < 0 or current_column < 0:
            position = total - 1 if reverse else 0
        else:
            position = current_row * columns + current_column + step

        for _ in range(total):
            position %= total
            row = position // columns
            column = position % columns
            if not self.isRowHidden(row) and not self.isColumnHidden(column):
                self.setCurrentCell(row, column)
                item = self.item(row, column)
                if item:
                    self.scrollToItem(item)
                return True
            position += step
        return False


def configure_multi_select_table(table: QTableWidget) -> None:
    table.setAlternatingRowColors(True)
    table.setWordWrap(True)
    table.setTabKeyNavigation(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.ExtendedSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(36)


RESPONSIVE_TABLE_COLUMN_KEYS: dict[str, tuple[str, ...]] = {
    "rent_requirements": (
        "id",
        "date",
        "client_name",
        "client_status",
        "contact",
        "property_requires",
        "size",
        "floor",
        "location",
        "budget",
    ),
    "rent_availability": (
        "id",
        "date",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "monthly_rent",
        "status",
    ),
    "rented_properties": (
        "id",
        "closed_at",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "monthly_rent",
        "closed_status",
    ),
    "sale_requirements": (
        "id",
        "date",
        "client_name",
        "client_status",
        "contact",
        "property_requires",
        "size",
        "floor",
        "location",
        "budget",
    ),
    "sale_availability": (
        "id",
        "date",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "demand",
        "status",
    ),
    "sold_properties": (
        "id",
        "closed_at",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "demand",
        "closed_status",
    ),
    "broker_contacts": ("id", "name", "contact", "area", "office_address", "remarks"),
}

LOW_PRIORITY_TABLE_COLUMN_KEYS = {
    "measurement",
    "measurement_unit",
    "deposit",
    "maintenance_charge",
    "building_name",
    "bachelor_family",
    "persons",
    "workflow_stage",
    "facilities",
    "remarks",
    "notes",
    "description",
    "created_by",
    "created_at",
    "last_edited_by",
    "last_edited_at",
    "approval_status",
    "approval_comment",
    "deleted_by",
    "deleted_at",
    "source_id",
    "archived_by",
}


def responsive_table_columns(table: str, columns: list[ColumnSpec]) -> list[ColumnSpec]:
    by_key = {column.key: column for column in columns}
    preferred = RESPONSIVE_TABLE_COLUMN_KEYS.get(table)
    if preferred:
        visible = [by_key[key] for key in preferred if key in by_key]
        if visible:
            return visible
    compact = [column for column in columns if column.key not in LOW_PRIORITY_TABLE_COLUMN_KEYS]
    return (compact or columns)[:10]


def apply_responsive_table_layout(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    header.setMinimumSectionSize(72)
    header.setSectionResizeMode(QHeaderView.Interactive)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setWordWrap(True)
    table.verticalHeader().setDefaultSectionSize(40)


STATUS_COLUMN_KEYS = {"client_status", "client_broker", "status", "workflow_stage", "approval_status", "verification_status"}
PROPERTY_COLUMN_KEYS = {"property_requires", "property_availability", "property_type", "property_requirement"}


def style_workflow_table_item(item: QTableWidgetItem, key: str, text: str) -> None:
    item.setForeground(QColor("#0f172a"))
    normalized = (text or "").strip().lower()
    if key in PROPERTY_COLUMN_KEYS:
        item.setTextAlignment(Qt.AlignCenter)
        if "plot" in normalized:
            item.setBackground(QColor("#fef3c7"))
            item.setForeground(QColor("#92400e"))
        elif "shop" in normalized or "commercial" in normalized:
            item.setBackground(QColor("#e0f2fe"))
            item.setForeground(QColor("#075985"))
        else:
            item.setBackground(QColor("#dcfce7"))
            item.setForeground(QColor("#166534"))
    elif key in STATUS_COLUMN_KEYS:
        item.setTextAlignment(Qt.AlignCenter)
        if any(word in normalized for word in ("pending", "broker")):
            item.setBackground(QColor("#fef3c7"))
            item.setForeground(QColor("#92400e"))
        elif any(word in normalized for word in ("rented", "sold", "available", "approved", "owner")):
            item.setBackground(QColor("#dcfce7"))
            item.setForeground(QColor("#166534"))
        elif any(word in normalized for word in ("reject", "withdraw", "deleted")):
            item.setBackground(QColor("#fee2e2"))
            item.setForeground(QColor("#b91c1c"))
        else:
            item.setBackground(QColor("#dbeafe"))
            item.setForeground(QColor("#1d4ed8"))


def selected_table_row_indexes(table: QTableWidget, total_rows: int) -> list[int]:
    selection = table.selectionModel()
    rows: set[int] = set()
    if selection:
        rows.update(index.row() for index in selection.selectedRows())
        if not rows:
            rows.update(index.row() for index in selection.selectedIndexes())
    if not rows and 0 <= table.currentRow() < total_rows:
        rows.add(table.currentRow())
    return sorted(row for row in rows if 0 <= row < total_rows)


def select_all_table_rows(table: QTableWidget) -> None:
    if table.rowCount():
        table.selectAll()


def clear_table_selection(table: QTableWidget) -> None:
    table.clearSelection()
    table.setCurrentCell(-1, -1)



def configure_table_for_readability(table: QTableWidget) -> None:
    """Configure a read-only table (dialogs, previews) with word-wrap and no editing."""
    table.setAlternatingRowColors(True)
    table.setWordWrap(True)
    table.setTextElideMode(Qt.ElideNone)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
