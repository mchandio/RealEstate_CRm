"""Installment tracking module."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QMessageBox, QDialog, QTextEdit, QDialogButtonBox,
    QTableWidget, QTableWidgetItem
)
from typing import Any
from datetime import datetime

from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.utils import money, format_date_display
from dateutil.relativedelta import relativedelta


def installment_schedule_spec() -> TableSpec:
    """Create spec for installment_schedules table."""
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    
    return TableSpec(
        "Installment Schedules",
        "installment_schedules",
        [
            ColumnSpec("id", "ID", width=64),
            ColumnSpec("deal_type", "Deal Type", width=100),
            ColumnSpec("deal_table", "Source Table", width=130),
            ColumnSpec("total_amount", "Total Amount", m, 130),
            ColumnSpec("installment_count", "Installments", width=100),
            ColumnSpec("installment_amount", "Per Installment", m, 130),
            ColumnSpec("frequency", "Frequency", width=100),
            ColumnSpec("start_date", "Start Date", d, 110),
            ColumnSpec("end_date", "End Date", d, 110),
            ColumnSpec("status", "Status", width=100),
            ColumnSpec("notes", "Notes", width=200),
            ColumnSpec("created_at", "Created", d, 110),
        ],
        [
            FieldSpec("Deal ID", "deal_id", "entry", required=True, numeric=True),
            FieldSpec("Deal Type", "deal_type", "combo", 
                     options=["rent_availability", "sale_availability"], required=True),
            FieldSpec("Deal Table", "deal_table", "combo",
                     options=["rent_availability", "sale_availability"], required=True),
            FieldSpec("Total Amount", "total_amount", "entry", required=True, numeric=True),
            FieldSpec("Installment Count", "installment_count", "entry", required=True, numeric=True),
            FieldSpec("Per Installment", "installment_amount", "entry", numeric=True),
            FieldSpec("Frequency", "frequency", "combo",
                     options=["monthly", "quarterly", "yearly"], default="monthly"),
            FieldSpec("Start Date", "start_date", "date", required=True),
            FieldSpec("End Date", "end_date", "date"),
            FieldSpec("Status", "status", "combo",
                     options=["Active", "Completed", "Cancelled", "Defaulted"], default="Active"),
            FieldSpec("Notes", "notes", "text"),
        ],
        ["deal_id", "deal_type", "deal_table", "total_amount", "installment_count",
         "installment_amount", "frequency", "start_date", "end_date", "status", "notes",
         "created_by", "created_at"],
        ["total_amount", "installment_count", "installment_amount", "frequency",
         "end_date", "status", "notes", "last_edited_by", "last_edited_at"],
        permission="financial",
        order_by="created_at DESC, id DESC",
    )


def installment_payment_spec() -> TableSpec:
    """Create spec for installment_payments table."""
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    
    return TableSpec(
        "Installment Payments",
        "installment_payments",
        [
            ColumnSpec("id", "ID", width=64),
            ColumnSpec("schedule_id", "Schedule ID", width=90),
            ColumnSpec("installment_number", "Installment #", width=100),
            ColumnSpec("due_date", "Due Date", d, 110),
            ColumnSpec("amount", "Amount Due", m, 120),
            ColumnSpec("paid_amount", "Paid Amount", m, 120),
            ColumnSpec("paid_date", "Paid Date", d, 110),
            ColumnSpec("status", "Status", width=80),
            ColumnSpec("penalty", "Penalty", m, 100),
            ColumnSpec("late_days", "Late Days", width=80),
            ColumnSpec("payment_method", "Method", width=100),
            ColumnSpec("receipt_no", "Receipt #", width=100),
            ColumnSpec("notes", "Notes", width=180),
        ],
        [
            FieldSpec("Schedule ID", "schedule_id", "entry", required=True, numeric=True),
            FieldSpec("Installment Number", "installment_number", "entry", required=True, numeric=True),
            FieldSpec("Due Date", "due_date", "date", required=True),
            FieldSpec("Amount Due", "amount", "entry", required=True, numeric=True),
            FieldSpec("Paid Amount", "paid_amount", "entry", numeric=True),
            FieldSpec("Paid Date", "paid_date", "date"),
            FieldSpec("Status", "status", "combo",
                     options=["Pending", "Paid", "Late", "Partial", "Waived"], default="Pending"),
            FieldSpec("Penalty", "penalty", "entry", numeric=True),
            FieldSpec("Late Days", "late_days", "entry", numeric=True),
            FieldSpec("Payment Method", "payment_method", "combo",
                     options=["Cash", "Cheque", "Bank Transfer", "Online", "Other"]),
            FieldSpec("Receipt No", "receipt_no", "entry"),
            FieldSpec("Notes", "notes", "text"),
        ],
        ["schedule_id", "installment_number", "due_date", "amount", "paid_amount",
         "paid_date", "status", "penalty", "late_days", "payment_method", "receipt_no",
         "notes", "created_by", "created_at"],
        ["paid_amount", "paid_date", "status", "penalty", "late_days", "payment_method",
         "receipt_no", "notes"],
        permission="financial",
        order_by="due_date DESC, id DESC",
    )


class InstallmentSummaryDialog(QDialog):
    """Dialog showing installment payment summary."""
    
    def __init__(self, schedule_row: dict, payments: list[dict], 
                 currency_symbol: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Installment Summary - Schedule #{schedule_row.get('id', '')}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # Header info
        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(120)
        
        total_amount = schedule_row.get("total_amount", 0)
        installment_count = schedule_row.get("installment_count", 0)
        installment_amount = schedule_row.get("installment_amount", 0)
        frequency = schedule_row.get("frequency", "monthly")
        status = schedule_row.get("status", "Active")
        
        paid_total = sum(p.get("paid_amount", 0) for p in payments)
        paid_count = sum(1 for p in payments if p.get("status") == "Paid")
        pending_count = sum(1 for p in payments if p.get("status") == "Pending")
        late_count = sum(1 for p in payments if p.get("status") == "Late")
        total_penalty = sum(p.get("penalty", 0) for p in payments)
        
        info.setPlainText(
            f"Schedule #{schedule_row.get('id', '')} | Status: {status}\n"
            f"Total Amount: {money(total_amount, currency_symbol)} | "
            f"Installments: {installment_count} x {money(installment_amount, currency_symbol)}\n"
            f"Frequency: {frequency.title()}\n\n"
            f"Paid: {paid_count} ({money(paid_total, currency_symbol)}) | "
            f"Pending: {pending_count} | Late: {late_count} | "
            f"Total Penalty: {money(total_penalty, currency_symbol)}"
        )
        layout.addWidget(info)
        
        # Payments table
        table = QTableWidget()
        headers = ["#", "Due Date", "Amount", "Paid", "Paid Date", "Status", "Penalty", "Method"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(payments))
        table.setAlternatingRowColors(True)
        
        for row_idx, p in enumerate(payments):
            items = [
                str(p.get("installment_number", "")),
                format_date_display(p.get("due_date")),
                money(p.get("amount", 0), currency_symbol),
                money(p.get("paid_amount", 0), currency_symbol),
                format_date_display(p.get("paid_date")),
                str(p.get("status", "")),
                money(p.get("penalty", 0), currency_symbol),
                str(p.get("payment_method", "") or ""),
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Color coding for status
                status_val = p.get("status", "").lower()
                if status_val == "paid":
                    item.setBackground(QColor("#e8f5e9"))
                elif status_val == "late":
                    item.setBackground(QColor("#ffebee"))
                elif status_val == "partial":
                    item.setBackground(QColor("#fff3e0"))
                table.setItem(row_idx, col_idx, item)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)


class InstallmentModule(QWidget):
    """Module for installment tracking."""
    
    def __init__(self, main: "ModernCRMWindow", services: CRMServices):
        super().__init__()
        self.main = main
        self.services = services
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        heading = QLabel("Installment Tracking")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        
        tabs = QTabWidget()
        
        # Schedules tab
        self.schedule_spec = installment_schedule_spec()
        self.schedules = DataTablePage(
            main, 
            self.schedule_spec,
            extra_buttons=[
                ("View Payments", self._view_payments, ""),
                ("Generate Payments", self._generate_payments, "AccentButton"),
                ("Summary", self._show_summary, ""),
            ]
        )
        
        # Payments tab
        self.payment_spec = installment_payment_spec()
        self.payments = DataTablePage(main, self.payment_spec)
        
        tabs.addTab(self.schedules, "Schedules")
        tabs.addTab(self.payments, "All Payments")
        layout.addWidget(tabs, 1)
    
    def _view_payments(self) -> None:
        """View payments for selected schedule.
        
        Optimized to fetch all payment data in a single query (Phase 7: N+1 fix).
        """
        row = self.schedules.require_single_row("viewing payments")
        if not row:
            return
        
        # Single query fetches all payments for this schedule
        payments = self.services.fetch_all(
            "SELECT * FROM installment_payments WHERE schedule_id=? ORDER BY installment_number",
            (row["id"],)
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Payments for Schedule #{row['id']}")
        dialog.setMinimumSize(800, 500)
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        headers = ["#", "Due Date", "Amount", "Paid", "Paid Date", "Status", "Method", "Receipt"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(payments))
        table.setAlternatingRowColors(True)
        
        for row_idx, p in enumerate(payments):
            items = [
                str(p.get("installment_number", "")),
                format_date_display(p.get("due_date")),
                money(p.get("amount", 0), self.main.currency_symbol),
                money(p.get("paid_amount", 0), self.main.currency_symbol),
                format_date_display(p.get("paid_date")),
                str(p.get("status", "")),
                str(p.get("payment_method", "") or ""),
                str(p.get("receipt_no", "") or ""),
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                status_val = p.get("status", "").lower()
                if status_val == "paid":
                    item.setBackground(QColor("#e8f5e9"))
                elif status_val == "late":
                    item.setBackground(QColor("#ffebee"))
                table.setItem(row_idx, col_idx, item)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()
    
    def _generate_payments(self) -> None:
        """Auto-generate payment records from schedule."""
        row = self.schedules.require_single_row("generating payments")
        if not row:
            return
        
        schedule_id = row["id"]
        count = row.get("installment_count", 0)
        amount = row.get("installment_amount", 0)
        start_date = row.get("start_date", "")
        frequency = row.get("frequency", "monthly")
        
        if not count or not amount or not start_date:
            QMessageBox.warning(self, "Invalid", "Schedule missing installment count, amount, or start date.")
            return
        
        # Auto-calculate installment_amount if not set
        if not amount and row.get("total_amount") and count:
            amount = round(float(row["total_amount"]) / count, 2)
            self.services.execute(
                "UPDATE installment_schedules SET installment_amount=? WHERE id=?",
                (amount, schedule_id)
            )
        
        # Check existing payments
        existing = self.services.fetch_one(
            "SELECT COUNT(*) as cnt FROM installment_payments WHERE schedule_id=?",
            (schedule_id,)
        )
        if existing and existing.get("cnt", 0) > 0:
            ask = QMessageBox.question(
                self, "Existing Payments",
                f"Schedule already has {existing['cnt']} payment(s). Generate more?",
            )
            if ask != QMessageBox.Yes:
                return
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        generated = 0
        
        for i in range(1, count + 1):
            if frequency == "quarterly":
                due = start + relativedelta(months=(i - 1) * 3)
            elif frequency == "yearly":
                due = start + relativedelta(years=i - 1)
            else:
                # Default to monthly
                due = start + relativedelta(months=i - 1)
            
            self.services.insert(
                """INSERT INTO installment_payments 
                   (schedule_id, installment_number, due_date, amount, status, created_by)
                   VALUES (?, ?, ?, ?, 'Pending', ?)""",
                (schedule_id, i, due.strftime("%Y-%m-%d"), amount,
                 self.main.current_user.get("username", ""))
            )
            generated += 1
        
        QMessageBox.information(self, "Generated", f"Created {generated} payment record(s).")
        self.payments.refresh()
    
    def _show_summary(self) -> None:
        """Show summary for selected schedule."""
        row = self.schedules.require_single_row("viewing summary")
        if not row:
            return
        
        payments = self.services.fetch_all(
            "SELECT * FROM installment_payments WHERE schedule_id=? ORDER BY installment_number",
            (row["id"],)
        )
        
        dialog = InstallmentSummaryDialog(row, payments, self.main.currency_symbol, self)
        dialog.exec()
    
    def refresh(self) -> None:
        self.schedules.refresh()
        self.payments.refresh()
