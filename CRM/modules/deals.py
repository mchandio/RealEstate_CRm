"""Deal module."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy
from typing import Any

# ─── CRM module imports ───
from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices

class DealModule(QWidget):
    def __init__(
        self,
        main: "ModernCRMWindow",
        title: str,
        requirement_spec: TableSpec,
        availability_spec: TableSpec,
        closed_spec: TableSpec | None = None,
        closed_label: str | None = None,
    ):
        super().__init__()
        self.main = main
        self.requirement_spec = requirement_spec
        self.availability_spec = availability_spec
        self.closed_spec = closed_spec
        self.kind = "rent" if requirement_spec.table.startswith("rent") else "sale"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        top.addWidget(heading)
        top.addStretch(1)

        layout.addLayout(top)

        tabs = QTabWidget()
        self.requirements = DataTablePage(
            main,
            requirement_spec,
            extra_buttons=self._deal_buttons(lambda: self.requirements, requirement_spec.table),
        )
        self.availability = DataTablePage(
            main,
            availability_spec,
            extra_buttons=self._deal_buttons(lambda: self.availability, availability_spec.table),
        )
        self.closed = DataTablePage(main, closed_spec) if closed_spec else None
        tabs.addTab(self.requirements, "Requirements")
        tabs.addTab(self.availability, "Availability")
        if self.closed:
            tabs.addTab(self.closed, closed_label or closed_spec.title)
        layout.addWidget(tabs, 1)

    def _deal_buttons(self, page_getter: Callable[[], DataTablePage], table: str) -> list[tuple[str, Callable[[], None], str]]:
        buttons = [
            ("Mark Pending", lambda: self.main.mark_records_workflow(page_getter(), table, "Pending"), "WarningButton"),
            ("AI Match", lambda: self.main.ai_match(page_getter(), table), ""),
            ("Report", lambda: self.main.preview_report("rent" if table.startswith("rent") else "sale"), ""),
        ]
        if table == "rent_availability":
            buttons.insert(0, ("Mark Rented", lambda: self.main.mark_availability_closed(page_getter(), table, "Rented"), "AccentButton"))
        elif table == "sale_availability":
            buttons.insert(0, ("Mark Sold", lambda: self.main.mark_availability_closed(page_getter(), table, "Sold"), "AccentButton"))
        return buttons

    def refresh(self) -> None:
        self.requirements.refresh()
        self.availability.refresh()
        if self.closed:
            self.closed.refresh()