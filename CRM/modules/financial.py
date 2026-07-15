"""Financial module."""
from __future__ import annotations
from PySide6.QtCore import QDate
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy, QTextEdit, QFileDialog
from typing import Any
from datetime import datetime
from pathlib import Path

# ─── CRM module imports ───
from CRM.modules.data_table import DataTablePage
from CRM.modules.phase_one import SummaryPage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import DATE_STORAGE_FORMAT, DATE_DISPLAY_FORMAT, OUTPUT_DIR

class FinancialModule(QWidget):
    def __init__(self, main: "ModernCRMWindow", income_spec: TableSpec, expense_spec: TableSpec):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Financials")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        tabs = QTabWidget()
        self.income = DataTablePage(main, income_spec)
        self.expenses = DataTablePage(main, expense_spec)
        self.summary = SummaryPage(main)
        tabs.addTab(self.income, "Income")
        tabs.addTab(self.expenses, "Expenses")
        tabs.addTab(self.summary, "Summary")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.income.refresh()
        self.expenses.refresh()
        self.summary.refresh()