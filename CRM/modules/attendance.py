"""Attendance tracking page."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy, QLineEdit, QComboBox, QDateEdit
from typing import Any
from datetime import datetime

# ─── CRM module imports ───
from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import DATE_STORAGE_FORMAT, DATE_DISPLAY_FORMAT
from CRM.utils import format_date_display
from CRM.widgets.table import ExcelTableWidget, configure_multi_select_table, selected_table_row_indexes, select_all_table_rows, clear_table_selection
from crm_core.attendance import ATTENDANCE_STATUSES, LEAVE_TYPES, calculate_attendance, summarize_attendance, format_minutes

class AttendancePage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.date = QDateEdit(QDate.currentDate())
        self.end_date = QDateEdit(QDate.currentDate())
        for date_edit in (self.date, self.end_date):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Keyword")
        self.keyword_input.returnPressed.connect(self.refresh)
        self.check_in_input = QLineEdit()
        self.check_in_input.setPlaceholderText("Check in HH:MM")
        self.check_out_input = QLineEdit()
        self.check_out_input.setPlaceholderText("Check out HH:MM")
        self.status_combo = QComboBox()
        for status in ATTENDANCE_STATUSES:
            if status != "Not Marked":
                self.status_combo.addItem(status)
        self.leave_type_combo = QComboBox()
        for leave_type in LEAVE_TYPES:
            self.leave_type_combo.addItem(leave_type or "No Leave Type", leave_type)
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Sort by Employee", "employee")
        self.sort_combo.addItem("Sort by Date", "date")
        self.sort_combo.addItem("Sort by Status", "status")
        self.sort_combo.currentIndexChanged.connect(lambda _index: self.refresh())
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Ascending", "ASC")
        self.direction_combo.addItem("Descending", "DESC")
        self.direction_combo.currentIndexChanged.connect(lambda _index: self.refresh())
        load = QPushButton("Load")
        load.clicked.connect(self.refresh)
        present = QPushButton("Mark Present")
        present.setObjectName("AccentButton")
        present.clicked.connect(lambda: self.mark("Present"))
        check_in_now = QPushButton("Check In Now")
        check_in_now.setObjectName("AccentButton")
        check_in_now.clicked.connect(self.check_in_now)
        check_out_now = QPushButton("Check Out Now")
        check_out_now.clicked.connect(self.check_out_now)
        apply_status = QPushButton("Apply Status")
        apply_status.clicked.connect(lambda: self.mark(str(self.status_combo.currentText() or "Present")))
        absent = QPushButton("Mark Absent")
        absent.setObjectName("DangerButton")
        absent.clicked.connect(lambda: self.mark("Absent"))
        leave = QPushButton("Mark Leave")
        leave.clicked.connect(lambda: self.mark("Leave"))
        controls.addWidget(QLabel("Start"))
        controls.addWidget(self.date)
        controls.addWidget(QLabel("End"))
        controls.addWidget(self.end_date)
        controls.addWidget(self.keyword_input)
        controls.addWidget(self.check_in_input)
        controls.addWidget(self.check_out_input)
        controls.addWidget(self.status_combo)
        controls.addWidget(self.leave_type_combo)
        controls.addWidget(self.sort_combo)
        controls.addWidget(self.direction_combo)
        controls.addWidget(load)
        controls.addStretch(1)
        controls.addWidget(check_in_now)
        controls.addWidget(check_out_now)
        controls.addWidget(apply_status)
        controls.addWidget(present)
        controls.addWidget(absent)
        controls.addWidget(leave)
        layout.addLayout(controls)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected")
        self.selection_label.setObjectName("SelectionCount")
        self.summary_label = QLabel("No attendance loaded")
        self.summary_label.setObjectName("MutedText")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        selection.addWidget(self.selection_label)
        selection.addWidget(self.summary_label, 1)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        layout.addLayout(selection)
        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        start_date = self.date.date()
        end_date = self.end_date.date()
        if end_date < start_date:
            end_date = start_date
            self.end_date.setDate(end_date)
        start = start_date.toString(DATE_STORAGE_FORMAT)
        end = end_date.toString(DATE_STORAGE_FORMAT)
        keyword = self.keyword_input.text().strip()
        where_parts = ["a.date BETWEEN ? AND ?"]
        params: list[Any] = [start, end]
        if keyword:
            where_parts.append(
                "(LOWER(e.full_name) LIKE ? OR LOWER(CAST(a.status AS TEXT)) LIKE ? OR "
                "LOWER(CAST(a.notes AS TEXT)) LIKE ? OR LOWER(CAST(a.date AS TEXT)) LIKE ?)"
            )
            params.extend([f"%{keyword.lower()}%"] * 4)
        sort_expr = {
            "employee": "e.full_name",
            "date": "a.date",
            "status": "a.status",
        }.get(str(self.sort_combo.currentData() or "employee"), "e.full_name")
        direction = self.direction_combo.currentData() or "ASC"
        marked = self.main.services.fetch_all(
            f"""SELECT a.id, e.id AS employee_id, e.full_name, a.date, a.check_in, a.check_out,
                       a.shift_name, a.scheduled_start, a.scheduled_end, a.status,
                       a.leave_type, a.worked_minutes, a.late_minutes,
                       a.early_leave_minutes, a.overtime_minutes, a.notes
                FROM attendance a JOIN employees e ON a.employee_id=e.id
                WHERE {' AND '.join(where_parts)}
                ORDER BY {sort_expr} {direction}, a.id DESC""",
            tuple(params),
        )
        if marked or start != end:
            self.rows = marked
        else:
            self.rows = [
                {
                    "id": None,
                    "employee_id": row["id"],
                    "full_name": row["full_name"],
                    "date": start,
                    "check_in": "",
                    "check_out": "",
                    "shift_name": "Office",
                    "scheduled_start": "09:30",
                    "scheduled_end": "18:00",
                    "status": "Not Marked",
                    "leave_type": "",
                    "worked_minutes": 0,
                    "late_minutes": 0,
                    "early_leave_minutes": 0,
                    "overtime_minutes": 0,
                    "notes": "",
                }
                for row in self.main.services.fetch_all("SELECT id, full_name FROM employees WHERE status='Active' ORDER BY full_name")
                if not keyword or keyword.lower() in str(row["full_name"] or "").lower()
            ]
        self.rows = [calculate_attendance(row) for row in self.rows]
        headers = ["ID", "Employee", "Date", "In", "Out", "Status", "Worked", "Late", "OT", "Notes"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            values = [
                row.get("id") or "",
                row.get("full_name") or "",
                format_date_display(row.get("date")),
                row.get("check_in") or "",
                row.get("check_out") or "",
                row.get("status") or "",
                format_minutes(row.get("worked_minutes")),
                format_minutes(row.get("late_minutes")),
                format_minutes(row.get("overtime_minutes")),
                row.get("notes") or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.update_summary()
        self.update_selection_label()

    def selected_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_indexes()]

    def selected(self) -> dict | None:
        rows = self.selected_rows()
        if not rows:
            return None
        return rows[0]

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected")

    def update_summary(self) -> None:
        summary = summarize_attendance(self.rows)
        self.summary_label.setText(
            "Present: {present} | Absent: {absent} | Leave: {leave} | Late: {late} | Hours: {hours} | OT: {ot}".format(
                present=summary["present_days"],
                absent=summary["absent_days"],
                leave=summary["leave_days"],
                late=summary["late_days"],
                hours=format_minutes(summary["worked_minutes"]),
                ot=format_minutes(summary["overtime_minutes"]),
            )
        )

    def check_in_now(self) -> None:
        self.check_in_input.setText(datetime.now().strftime("%H:%M"))
        self.mark("Present")

    def check_out_now(self) -> None:
        self.check_out_input.setText(datetime.now().strftime("%H:%M"))
        self.mark("Present")

    def mark(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more employee rows first.")
            return
        for row in rows:
            date = row.get("date") or self.date.date().toString(DATE_STORAGE_FORMAT)
            base = {
                **row,
                "date": date,
                "status": status,
                "check_in": self.check_in_input.text().strip() or row.get("check_in") or "",
                "check_out": self.check_out_input.text().strip() or row.get("check_out") or "",
                "leave_type": self.leave_type_combo.currentData() or row.get("leave_type") or "",
                "last_edited_at": datetime.now().isoformat(timespec="seconds"),
            }
            calculated = calculate_attendance(base)
            existing = self.main.services.fetch_one(
                "SELECT id FROM attendance WHERE employee_id=? AND date=?",
                (row["employee_id"], date),
            )
            if existing:
                self.main.services.execute(
                    """UPDATE attendance
                       SET status=?, check_in=?, check_out=?, shift_name=?, scheduled_start=?,
                           scheduled_end=?, leave_type=?, worked_minutes=?, late_minutes=?,
                           early_leave_minutes=?, overtime_minutes=?, last_edited_at=?
                       WHERE employee_id=? AND date=?""",
                    (
                        calculated["status"],
                        calculated.get("check_in") or "",
                        calculated.get("check_out") or "",
                        calculated.get("shift_name") or "Office",
                        calculated.get("scheduled_start") or "09:30",
                        calculated.get("scheduled_end") or "18:00",
                        calculated.get("leave_type") or "",
                        calculated.get("worked_minutes") or 0,
                        calculated.get("late_minutes") or 0,
                        calculated.get("early_leave_minutes") or 0,
                        calculated.get("overtime_minutes") or 0,
                        calculated.get("last_edited_at") or datetime.now().isoformat(timespec="seconds"),
                        row["employee_id"],
                        date,
                    ),
                )
            else:
                self.main.services.execute(
                    """INSERT INTO attendance
                       (employee_id, date, check_in, check_out, shift_name, scheduled_start,
                        scheduled_end, status, leave_type, worked_minutes, late_minutes,
                        early_leave_minutes, overtime_minutes, last_edited_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["employee_id"],
                        date,
                        calculated.get("check_in") or "",
                        calculated.get("check_out") or "",
                        calculated.get("shift_name") or "Office",
                        calculated.get("scheduled_start") or "09:30",
                        calculated.get("scheduled_end") or "18:00",
                        calculated["status"],
                        calculated.get("leave_type") or "",
                        calculated.get("worked_minutes") or 0,
                        calculated.get("late_minutes") or 0,
                        calculated.get("early_leave_minutes") or 0,
                        calculated.get("overtime_minutes") or 0,
                        calculated.get("last_edited_at") or datetime.now().isoformat(timespec="seconds"),
                    ),
                )
        self.refresh()