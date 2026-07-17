"""Commission calculation module."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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


def commission_spec() -> TableSpec:
    """Create spec for commissions table."""
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)

    return TableSpec(
        "Commissions",
        "commissions",
        [
            ColumnSpec("id", "ID", width=64),
            ColumnSpec("deal_type", "Deal Type", width=100),
            ColumnSpec("deal_table", "Source Table", width=130),
            ColumnSpec("deal_amount", "Deal Amount", m, 130),
            ColumnSpec("commission_rate", "Rate %", width=80),
            ColumnSpec("total_commission", "Commission", m, 130),
            ColumnSpec("status", "Status", width=90),
            ColumnSpec("approved_by", "Approved By", width=110),
            ColumnSpec("approved_at", "Approved", d, 110),
            ColumnSpec("paid_at", "Paid", d, 110),
            ColumnSpec("payment_method", "Method", width=100),
            ColumnSpec("notes", "Notes", width=180),
            ColumnSpec("created_at", "Created", d, 110),
        ],
        [
            FieldSpec("Deal ID", "deal_id", "entry", required=True, numeric=True),
            FieldSpec("Deal Type", "deal_type", "combo",
                     options=["rent_availability", "sale_availability"], required=True),
            FieldSpec("Deal Table", "deal_table", "combo",
                     options=["rent_availability", "sale_availability"], required=True),
            FieldSpec("Deal Amount", "deal_amount", "entry", required=True, numeric=True),
            FieldSpec("Commission Rate %", "commission_rate", "entry", numeric=True, default="5.0"),
            FieldSpec("Total Commission", "total_commission", "entry", numeric=True),
            FieldSpec("Status", "status", "combo",
                     options=["Pending", "Approved", "Paid", "Cancelled"], default="Pending"),
            FieldSpec("Payment Method", "payment_method", "combo",
                     options=["Cash", "Cheque", "Bank Transfer", "Other"]),
            FieldSpec("Notes", "notes", "text"),
        ],
        ["deal_id", "deal_type", "deal_table", "deal_amount", "commission_rate",
         "total_commission", "status", "payment_method", "notes",
         "created_by", "created_at"],
        ["deal_amount", "commission_rate", "total_commission", "status",
         "payment_method", "notes", "last_edited_by", "last_edited_at"],
        permission="financial",
        order_by="created_at DESC, id DESC",
    )


def commission_split_spec() -> TableSpec:
    """Create spec for commission_splits table."""
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)

    return TableSpec(
        "Commission Splits",
        "commission_splits",
        [
            ColumnSpec("id", "ID", width=64),
            ColumnSpec("commission_id", "Commission ID", width=100),
            ColumnSpec("agent_name", "Agent", width=150),
            ColumnSpec("split_percentage", "Split %", width=80),
            ColumnSpec("split_amount", "Amount", m, 130),
            ColumnSpec("status", "Status", width=80),
            ColumnSpec("paid_at", "Paid", d, 110),
            ColumnSpec("payment_method", "Method", width=100),
            ColumnSpec("notes", "Notes", width=180),
            ColumnSpec("created_at", "Created", d, 110),
        ],
        [
            FieldSpec("Agent Name", "agent_name", "entry", required=True),
            FieldSpec("Agent ID (Employee)", "agent_id", "entry", numeric=True),
            FieldSpec("Split Percentage", "split_percentage", "entry", required=True, numeric=True, default="100"),
            FieldSpec("Split Amount", "split_amount", "entry", numeric=True),
            FieldSpec("Status", "status", "combo",
                     options=["Pending", "Paid"], default="Pending"),
            FieldSpec("Payment Method", "payment_method", "combo",
                     options=["Cash", "Cheque", "Bank Transfer", "Other"]),
            FieldSpec("Notes", "notes", "text"),
        ],
        ["commission_id", "agent_id", "agent_name", "split_percentage", "split_amount",
         "status", "payment_method", "notes", "created_at"],
        ["split_percentage", "split_amount", "status", "payment_method", "notes"],
        permission="financial",
        order_by="created_at DESC, id DESC",
    )


class CommissionDetailDialog(QDialog):
    """Dialog showing commission detail with splits."""

    def __init__(self, commission_row: dict, splits: list[dict],
                 currency_symbol: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Commission Detail - #{commission_row.get('id', '')}")
        self.setMinimumSize(700, 450)

        layout = QVBoxLayout(self)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setMaximumHeight(100)

        deal_amount = commission_row.get("deal_amount", 0)
        rate = commission_row.get("commission_rate", 0)
        total_commission = commission_row.get("total_commission", 0)
        status = commission_row.get("status", "Pending")

        info.setPlainText(
            f"Commission #{commission_row.get('id', '')} | Status: {status}\n"
            f"Deal Amount: {money(deal_amount, currency_symbol)} | "
            f"Rate: {rate}% | "
            f"Total Commission: {money(total_commission, currency_symbol)}"
        )
        layout.addWidget(info)

        # Splits table
        table = QTableWidget()
        headers = ["Agent", "Split %", "Amount", "Status", "Paid", "Method"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(splits))
        table.setAlternatingRowColors(True)

        for row_idx, s in enumerate(splits):
            items = [
                str(s.get("agent_name", "")),
                f"{s.get('split_percentage', 0):.1f}%",
                money(s.get("split_amount", 0), currency_symbol),
                str(s.get("status", "")),
                format_date_display(s.get("paid_at")),
                str(s.get("payment_method", "") or ""),
            ]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if s.get("status", "").lower() == "paid":
                    item.setBackground(QColor("#e8f5e9"))
                table.setItem(row_idx, col_idx, item)

        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)


class CommissionModule(QWidget):
    """Module for commission tracking."""

    def __init__(self, main: "ModernCRMWindow", services: CRMServices):
        super().__init__()
        self.main = main
        self.services = services

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Commission Tracking")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        tabs = QTabWidget()

        # Commissions tab
        self.commission_spec = commission_spec()
        self.commissions = DataTablePage(
            main,
            self.commission_spec,
            extra_buttons=[
                ("View Splits", self._view_splits, ""),
                ("Approve", self._approve_commission, "AccentButton"),
                ("Mark Paid", self._mark_paid, ""),
                ("Add Split", self._add_split, ""),
            ]
        )

        # Splits tab
        self.split_spec = commission_split_spec()
        self.splits = DataTablePage(main, self.split_spec)

        tabs.addTab(self.commissions, "Commissions")
        tabs.addTab(self.splits, "Agent Splits")
        layout.addWidget(tabs, 1)

    def _view_splits(self) -> None:
        """View splits for selected commission."""
        row = self.commissions.require_single_row("viewing splits")
        if not row:
            return

        splits = self.services.fetch_all(
            "SELECT * FROM commission_splits WHERE commission_id=? ORDER BY id",
            (row["id"],)
        )

        dialog = CommissionDetailDialog(row, splits, self.main.currency_symbol, self)
        dialog.exec()

    def _approve_commission(self) -> None:
        """Approve selected commission."""
        row = self.commissions.require_single_row("approving")
        if not row:
            return

        if row.get("status") == "Approved":
            QMessageBox.information(self, "Already Approved", "This commission is already approved.")
            return

        now = datetime.now().isoformat(timespec="seconds")
        self.services.execute(
            """UPDATE commissions SET status='Approved', approved_by=?, approved_at=?,
               last_edited_by=?, last_edited_at=? WHERE id=?""",
            (self.main.current_user.get("username", ""), now,
             self.main.current_user.get("username", ""), now, row["id"])
        )
        QMessageBox.information(self, "Approved", f"Commission #{row['id']} approved.")
        self.commissions.refresh()

    def _mark_paid(self) -> None:
        """Mark commission as paid."""
        row = self.commissions.require_single_row("marking paid")
        if not row:
            return

        if row.get("status") not in ("Pending", "Approved"):
            QMessageBox.information(self, "Invalid Status", "Commission must be approved before marking as paid.")
            return

        now = datetime.now().isoformat(timespec="seconds")
        self.services.execute(
            """UPDATE commissions SET status='Paid', paid_at=?,
               last_edited_by=?, last_edited_at=? WHERE id=?""",
            (now, self.main.current_user.get("username", ""), now, row["id"])
        )
        QMessageBox.information(self, "Paid", f"Commission #{row['id']} marked as paid.")
        self.commissions.refresh()

    def _add_split(self) -> None:
        """Add split for selected commission."""
        row = self.commissions.require_single_row("adding split")
        if not row:
            return

        from CRM.dialogs.record import RecordDialog
        dialog = RecordDialog("Add Commission Split", self.split_spec.form_fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        vals = dialog.values()
        commission_id = row["id"]
        commission_total = row.get("total_commission", 0)

        # Auto-calculate split_amount if not set
        split_pct = float(vals.get("split_percentage", 100))
        if not vals.get("split_amount") and commission_total:
            vals["split_amount"] = round(commission_total * (split_pct / 100), 2)

        # Set commission_id from selected row
        vals["commission_id"] = commission_id

        cols = self.split_spec.insert_columns
        placeholders = ", ".join(["?"] * len(cols))
        self.services.insert(
            f"INSERT INTO commission_splits ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals.get(col) for col in cols)
        )
        QMessageBox.information(self, "Added", "Commission split added.")
        self.splits.refresh()

    def refresh(self) -> None:
        self.commissions.refresh()
        self.splits.refresh()
