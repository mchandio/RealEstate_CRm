"""Salary management page."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy
from typing import Any
from datetime import datetime

# ─── CRM module imports ───
from CRM.constants import PY_DATE_STORAGE_FORMAT
from CRM.utils import safe_float, money
from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.dialogs.record import RecordDialog

class SalaryPage(DataTablePage):
    def __init__(self, main: "ModernCRMWindow", spec: TableSpec):
        super().__init__(
            main,
            spec,
            extra_buttons=[("Pay Salary", self.pay_salary, "AccentButton")],
        )

    def refresh(self) -> None:
        where_parts: list[str] = []
        params: list[Any] = []
        keyword = self.keyword_input.text().strip()
        if keyword:
            searchable = (
                "e.full_name", "sp.month", "sp.year", "sp.payment_method", "sp.notes",
                "sp.base_salary", "sp.bonus", "sp.deductions", "sp.net_salary",
            )
            where_parts.append(
                "(" + " OR ".join(f"LOWER(CAST(COALESCE({column}, '') AS TEXT)) LIKE ?" for column in searchable) + ")"
            )
            params.extend([f"%{keyword.lower()}%"] * len(searchable))
        start = self._active_date(self.start_date)
        end = self._active_date(self.end_date)
        if start:
            where_parts.append("date(sp.payment_date) >= date(?)")
            params.append(start)
        if end:
            where_parts.append("date(sp.payment_date) <= date(?)")
            params.append(end)
        sort_map = {
            "id": "sp.id",
            "full_name": "e.full_name",
            "month": "sp.month",
            "year": "sp.year",
            "base_salary": "sp.base_salary",
            "bonus": "sp.bonus",
            "deductions": "sp.deductions",
            "net_salary": "sp.net_salary",
            "payment_method": "sp.payment_method",
        }
        sort_expr = sort_map.get(str(self.sort_combo.currentData() or "id"), "sp.id")
        direction = self.direction_combo.currentData() or "DESC"
        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        self.rows = self.host.services.fetch_all(
            f"""SELECT sp.id, e.full_name, sp.month, sp.year, sp.base_salary, sp.bonus,
                       sp.deductions, sp.net_salary, sp.payment_method
                FROM salary_payments sp JOIN employees e ON sp.employee_id=e.id
                {where_sql}
                ORDER BY {sort_expr} {direction}, sp.id DESC""",
            tuple(params),
        )
        columns = self.spec.columns
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c.label for c in columns])
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            for c, col in enumerate(columns):
                value = row.get(col.key)
                text = col.formatter(value, self.host.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.update_selection_label()

    def pay_salary(self) -> None:
        employees = self.host.services.fetch_all("SELECT id, full_name, base_salary FROM employees WHERE status='Active' ORDER BY full_name")
        if not employees:
            QMessageBox.information(self, "No Employees", "No active employees found.")
            return
        names = [f"{e['full_name']} (Base: {money(e['base_salary'], self.host.currency_symbol)})" for e in employees]
        fields = [
            FieldSpec("Employee *", "employee", "combo", options=names, required=True),
            FieldSpec("Month *", "month", "combo", options=[
                "January", "February", "March", "April", "May", "June", "July", "August",
                "September", "October", "November", "December",
            ], required=True),
            FieldSpec("Year *", "year", "entry", str(datetime.now().year), required=True),
            FieldSpec("Base Salary *", "base_salary", "entry", "", required=True, numeric=True),
            FieldSpec("Bonus", "bonus", "entry", "0", numeric=True),
            FieldSpec("Deductions", "deductions", "entry", "0", numeric=True),
            FieldSpec("Net Salary", "net_salary", "entry", "", numeric=True),
            FieldSpec("Payment Method", "payment_method", "combo", options=["Cash", "Cheque", "Bank Transfer", "Online"]),
            FieldSpec("Notes", "notes", "entry"),
        ]
        dialog = RecordDialog("Pay Salary", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        employee_name = str(vals["employee"]).split(" (Base:")[0]
        employee = self.host.services.fetch_one("SELECT id FROM employees WHERE full_name=?", (employee_name,))
        if not employee:
            QMessageBox.warning(self, "Employee", "Employee not found.")
            return
        base = safe_float(vals["base_salary"])
        bonus = safe_float(vals["bonus"])
        deductions = safe_float(vals["deductions"])
        net = safe_float(vals["net_salary"]) or (base + bonus - deductions)
        self.host.services.execute(
            """INSERT INTO salary_payments
               (employee_id, payment_date, month, year, base_salary, bonus, deductions,
                net_salary, payment_method, notes, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                employee["id"],
                datetime.now().strftime(PY_DATE_STORAGE_FORMAT),
                vals["month"],
                vals["year"],
                base,
                bonus,
                deductions,
                net,
                vals["payment_method"],
                vals["notes"],
                datetime.now(),
            ),
        )
        self.refresh()