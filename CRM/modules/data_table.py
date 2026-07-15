"""DataTablePage - Generic data table view."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy, QLineEdit, QComboBox, QDateEdit, QApplication, QFileDialog, QTextEdit, QDialogButtonBox, QDialog
from typing import Any, Callable
from datetime import datetime
import csv
import re

# ─── CRM module imports ───
from crm_core.constants import CLOSED_AVAILABILITY_ARCHIVES
from CRM.constants import DATE_STORAGE_FORMAT, DATE_DISPLAY_FORMAT, PY_DATE_STORAGE_FORMAT, PY_DATE_DISPLAY_FORMAT, PHONE_FORM_KEYS, EMAIL_FORM_KEYS, CNIC_FORM_KEYS, PERCENT_FORM_KEYS, LONG_TEXT_COLUMN_KEYS, PHASE1_TABLES, OUTPUT_DIR
from CRM.utils import is_date_key, format_date_display, quote_identifier
from CRM.constants import has_permission, is_admin_role
from CRM.widgets.table import ExcelTableWidget, RESPONSIVE_TABLE_COLUMN_KEYS, LOW_PRIORITY_TABLE_COLUMN_KEYS, STATUS_COLUMN_KEYS, PROPERTY_COLUMN_KEYS, configure_multi_select_table, style_workflow_table_item, apply_responsive_table_layout, responsive_table_columns, selected_table_row_indexes, select_all_table_rows, clear_table_selection
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.protocols import AppHost
from CRM.dialogs.record import RecordDialog

class DataTablePage(QWidget):
    def __init__(
        self,
        host: AppHost,
        spec: TableSpec,
        *,
        extra_buttons: list[tuple[str, Callable[[], None], str]] | None = None,
    ):
        super().__init__()
        self.host = host
        self.services = host.services
        self.spec = spec
        self.rows: list[dict] = []
        self.extra_buttons = extra_buttons or []
        self.text_filter_inputs: dict[str, QLineEdit] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(self.spec.title)
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        can_edit = self.host.can_edit(self.spec.permission) and bool(self.spec.form_fields)
        if can_edit:
            self.add_btn = QPushButton("Add")
            self.add_btn.setObjectName("AccentButton")
            self.add_btn.clicked.connect(self.add_record)
            header.addWidget(self.add_btn)
            self.edit_btn = QPushButton("Edit")
            self.edit_btn.clicked.connect(self.edit_record)
            header.addWidget(self.edit_btn)
            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setObjectName("DangerButton")
            self.delete_btn.clicked.connect(self.delete_record)
            header.addWidget(self.delete_btn)

        for label, callback, kind in self.extra_buttons:
            button = QPushButton(label)
            if kind:
                button.setObjectName(kind)
            button.clicked.connect(callback)
            header.addWidget(button)
        layout.addLayout(header)

        filters = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("Keyword")
        self.keyword_input.returnPressed.connect(self.refresh)
        filters.addWidget(self.keyword_input, 2)

        self.sort_combo = QComboBox()
        for col in self.spec.columns:
            if self.sort_combo.findData(col.key) < 0:
                self.sort_combo.addItem(f"Sort by {col.label}", col.key)
        default_sort = self._default_sort_key()
        default_index = self.sort_combo.findData(default_sort)
        if default_index >= 0:
            self.sort_combo.setCurrentIndex(default_index)
        self.sort_combo.currentIndexChanged.connect(lambda _index: self.refresh())
        filters.addWidget(self.sort_combo, 1)

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Descending", "DESC")
        self.direction_combo.addItem("Ascending", "ASC")
        if " ASC" in f" {self.spec.order_by.upper()}":
            self.direction_combo.setCurrentIndex(1)
        self.direction_combo.currentIndexChanged.connect(lambda _index: self.refresh())
        filters.addWidget(self.direction_combo)

        self.start_date = self._blank_date_edit("Start date")
        self.end_date = self._blank_date_edit("End date")
        self.start_date.dateChanged.connect(lambda _date: self.refresh())
        self.end_date.dateChanged.connect(lambda _date: self.refresh())
        filters.addWidget(self.start_date)
        filters.addWidget(self.end_date)

        find_btn = QPushButton("Find")
        find_btn.clicked.connect(self.refresh)
        filters.addWidget(find_btn)
        clear_filters = QPushButton("Clear")
        clear_filters.clicked.connect(self.clear_filters)
        filters.addWidget(clear_filters)
        layout.addLayout(filters)

        if self.spec.table == "broker_contacts":
            broker_filters = QHBoxLayout()
            for key, placeholder in (
                ("area", "Area filter"),
                ("office_address", "Office address filter"),
                ("home_address", "Home address filter"),
            ):
                input_widget = QLineEdit()
                input_widget.setPlaceholderText(placeholder)
                input_widget.returnPressed.connect(self.refresh)
                self.text_filter_inputs[key] = input_widget
                broker_filters.addWidget(input_widget, 1)
            layout.addLayout(broker_filters)

        tools = QHBoxLayout()
        self.selection_label = QLabel("0 selected")
        self.selection_label.setObjectName("SelectionCount")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        details = QPushButton("Details")
        details.clicked.connect(self.show_details)
        copy = QPushButton("Copy Selected")
        copy.clicked.connect(self.copy_selected_rows)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("Export")
        export.clicked.connect(self.export_csv)
        tools.addWidget(self.selection_label)
        tools.addStretch(1)
        tools.addWidget(select_all)
        tools.addWidget(clear)
        tools.addWidget(details)
        tools.addWidget(copy)
        tools.addWidget(refresh)
        tools.addWidget(export)
        layout.addLayout(tools)

        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        if can_edit:
            self.table.doubleClicked.connect(self.edit_record)
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def _default_sort_key(self) -> str:
        first = str(self.spec.order_by or "id DESC").split(",", 1)[0].strip()
        key = first.split()[0].strip('"[]`') if first else "id"
        available = {col.key for col in self.spec.columns}
        return key if key in available else "id"

    def _blank_date_edit(self, text: str) -> QDateEdit:
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        date_edit.setMinimumDate(QDate(1900, 1, 1))
        date_edit.setSpecialValueText(text)
        date_edit.setDate(date_edit.minimumDate())
        return date_edit

    def _active_date(self, date_edit: QDateEdit) -> str:
        if date_edit.date() <= date_edit.minimumDate():
            return ""
        return date_edit.date().toString(DATE_STORAGE_FORMAT)

    def clear_filters(self) -> None:
        widgets = (
            self.keyword_input,
            self.sort_combo,
            self.direction_combo,
            self.start_date,
            self.end_date,
            *self.text_filter_inputs.values(),
        )
        for widget in widgets:
            widget.blockSignals(True)
        self.keyword_input.clear()
        for input_widget in self.text_filter_inputs.values():
            input_widget.clear()
        default_index = self.sort_combo.findData(self._default_sort_key())
        self.sort_combo.setCurrentIndex(default_index if default_index >= 0 else 0)
        self.direction_combo.setCurrentIndex(1 if " ASC" in f" {self.spec.order_by.upper()}" else 0)
        self.start_date.setDate(self.start_date.minimumDate())
        self.end_date.setDate(self.end_date.minimumDate())
        for widget in widgets:
            widget.blockSignals(False)
        self.refresh()

    def _is_date_filter_key(self, key: str) -> bool:
        return is_date_key(key) or key.endswith("_at") or key in {"due_at", "assigned_at", "initiated_at", "open_date", "close_date", "completion_date", "effective_date"}

    def _date_filter_key(self, available_columns: set[str]) -> str | None:
        for col in self.spec.columns:
            if col.key in available_columns and self._is_date_filter_key(col.key):
                return col.key
        for key in ("date", "transaction_date", "payment_date", "hire_date", "created_at", "last_edited_at"):
            if key in available_columns:
                return key
        return None

    def _append_text_filter(
        self,
        where_parts: list[str],
        params: list[Any],
        available_columns: set[str],
        column: str,
        value: str,
    ) -> None:
        if column not in available_columns:
            return
        terms = [term.strip().lower() for term in re.split(r"[,;]+", value or "") if term.strip()]
        if not terms:
            return
        quoted = quote_identifier(column)
        where_parts.append(
            "(" + " OR ".join(f"LOWER(CAST(COALESCE({quoted}, '') AS TEXT)) LIKE ?" for _term in terms) + ")"
        )
        params.extend([f"%{term}%" for term in terms])

    def selected_row_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_row_indexes()]

    def selected_row(self) -> dict | None:
        rows = self.selected_rows()
        if not rows:
            return None
        return rows[0]

    def require_single_row(self, action: str = "this action") -> dict | None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select a row first.")
            return None
        if len(rows) > 1:
            QMessageBox.information(self, "Select One", f"Select only one row for {action}.")
            return None
        return rows[0]

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        count = len(self.selected_row_indexes())
        total = len(self.rows)
        self.selection_label.setText(f"{count} of {total} selected")

    def show_details(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select a row first.")
            return
        details: list[str] = []
        for row in rows:
            full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
            details.append(f"{self.spec.title} #{row.get('id')}")
            details.append("-" * 72)
            for key, value in full.items():
                if value in (None, ""):
                    display = "-"
                elif is_date_key(key):
                    display = format_date_display(value)
                else:
                    display = value
                details.append(f"{key}: {display}")
            details.append("")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.spec.title} Details")
        dialog.resize(720, 520)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 10))
        text.setPlainText("\n".join(details))
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        lines = ["\t".join(col.label for col in self.spec.columns)]
        for row in rows:
            lines.append("\t".join(str(row.get(col.key, "") or "") for col in self.spec.columns))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"{len(rows)} selected row(s) copied to clipboard.")

    def refresh(self) -> None:
        available_columns = self.services.table_columns(self.spec.table)
        columns = [col.key for col in self.spec.columns if col.key in available_columns]
        if not columns:
            columns = [col.key for col in self.spec.columns]
        where_parts: list[str] = []
        params: list[Any] = []
        if "is_deleted" in available_columns:
            where_parts.append("COALESCE(is_deleted, 0)=0")
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(self.spec.table)
        if closed_rule and "status" in available_columns:
            where_parts.append("LOWER(COALESCE(status, ''))<>LOWER(?)")
            params.append(closed_rule[0])
        keyword = self.keyword_input.text().strip()
        if keyword:
            searchable = [
                col for col in available_columns
                if col not in {"password_hash", "is_deleted", "deleted_by", "deleted_at"}
            ]
            if searchable:
                where_parts.append(
                    "(" + " OR ".join(f"CAST({quote_identifier(col)} AS TEXT) LIKE ?" for col in searchable) + ")"
                )
                params.extend([f"%{keyword}%"] * len(searchable))
        for column, input_widget in self.text_filter_inputs.items():
            self._append_text_filter(where_parts, params, available_columns, column, input_widget.text())
        date_key = self._date_filter_key(available_columns)
        start = self._active_date(self.start_date)
        end = self._active_date(self.end_date)
        if date_key and start:
            where_parts.append(f"date({quote_identifier(date_key)}) >= date(?)")
            params.append(start)
        if date_key and end:
            where_parts.append(f"date({quote_identifier(date_key)}) <= date(?)")
            params.append(end)
        sort_key = self.sort_combo.currentData() or self._default_sort_key()
        if sort_key not in available_columns:
            sort_key = "id" if "id" in available_columns else columns[0]
        direction = self.direction_combo.currentData() or "DESC"
        select_columns = ", ".join(quote_identifier(col) for col in columns)
        sql = f"SELECT {select_columns} FROM {quote_identifier(self.spec.table)}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += f" ORDER BY {quote_identifier(sort_key)} {direction}"
        if sort_key != "id" and "id" in available_columns:
            sql += f", {quote_identifier('id')} DESC"
        self.rows = self.services.fetch_all(sql, tuple(params))
        display_columns = responsive_table_columns(self.spec.table, self.spec.columns)
        self.table.setColumnCount(len(display_columns))
        self.table.setHorizontalHeaderLabels([col.label for col in display_columns])
        self.table.setRowCount(len(self.rows))
        has_long_text = any(col.key in LONG_TEXT_COLUMN_KEYS for col in display_columns)
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(display_columns):
                value = row.get(col.key)
                text = col.formatter(value, self.host.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                style_workflow_table_item(item, col.key, text)
                if col.key in LONG_TEXT_COLUMN_KEYS:
                    item.setToolTip(text)
                    item.setText(text.replace("\r\n", " ").replace("\n", " "))
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif len(text) > 28:
                    item.setToolTip(text)
                self.table.setItem(row_idx, col_idx, item)
            if has_long_text:
                self.table.setRowHeight(row_idx, 42)
        apply_responsive_table_layout(self.table)
        self.update_selection_label()

    def add_record(self) -> None:
        while True:
            dialog = RecordDialog(f"Add {self.spec.title}", self.spec.form_fields, parent=self, allow_save_new=True)
            if dialog.exec() != QDialog.Accepted:
                return
            vals = dialog.values()
            self._apply_defaults(vals, is_new=True)
            cols = self.spec.insert_columns
            placeholders = ", ".join(["?"] * len(cols))
            new_id = self.services.insert(
                f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals.get(col) for col in cols),
            )
            self.refresh()
            self.host.after_record_saved(self.spec.table, new_id)
            self.host.refresh_dashboard()
            self.host.update_status_bar(f"{self.spec.title} record saved")
            if not dialog.save_and_new:
                return

    def edit_record(self) -> None:
        row = self.require_single_row("editing")
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],))
        dialog = RecordDialog(f"Edit {self.spec.title}", self.spec.form_fields, full, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        self._apply_defaults(vals, is_new=False)
        cols = self.spec.update_columns
        if self.spec.table in PHASE1_TABLES and not is_admin_role(self.host.role):
            approval_id = self.services.submit_approval(
                "edit",
                self.spec.table,
                int(row["id"]),
                {col: vals.get(col) for col in cols},
                str(self.host.current_user.get("username") or ""),
            )
            QMessageBox.information(self, "Pending Approval", f"Edit request #{approval_id} was sent for admin approval.")
            self.host.update_status_bar(f"{self.spec.title} edit sent for approval")
            return
        assignments = ", ".join(f"{col}=?" for col in cols)
        if self.spec.table in PHASE1_TABLES:
            extra_cols = []
            if "last_edited_by" in self.services.table_columns(self.spec.table):
                extra_cols.append("last_edited_by")
                vals["last_edited_by"] = self.host.current_user.get("username", "")
            if "last_edited_at" in self.services.table_columns(self.spec.table):
                extra_cols.append("last_edited_at")
                vals["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            cols = cols + extra_cols
            assignments = ", ".join(f"{col}=?" for col in cols)
        params = tuple(vals.get(col) for col in cols) + (row["id"],)
        self.services.execute(f"UPDATE {self.spec.table} SET {assignments} WHERE id=?", params)
        self.refresh()
        self.host.after_record_saved(self.spec.table, row["id"])
        self.host.refresh_dashboard()
        self.host.update_status_bar(f"{self.spec.title} record updated")

    def delete_record(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        if not has_permission(self.host.role, "delete") and self.spec.table not in PHASE1_TABLES:
            QMessageBox.warning(self, "Access Denied", "You do not have permission to delete records.")
            return
        ids = [row["id"] for row in rows]
        ask = QMessageBox.question(self, "Recycle", f"Move {len(ids)} selected record(s) from {self.spec.title} to recycle?")
        if ask != QMessageBox.Yes:
            return
        if self.spec.table in PHASE1_TABLES and not is_admin_role(self.host.role):
            for row_id in ids:
                self.services.submit_approval(
                    "delete",
                    self.spec.table,
                    int(row_id),
                    {},
                    str(self.host.current_user.get("username") or ""),
                )
            QMessageBox.information(self, "Pending Approval", f"{len(ids)} delete request(s) were sent for admin approval.")
            self.host.update_status_bar(f"{len(ids)} delete request(s) sent for approval")
            return
        for row_id in ids:
            ok, message = self.host.can_delete_record(self.spec.table, int(row_id))
            if not ok:
                QMessageBox.warning(self, "Related Records", message)
                return
        if "is_deleted" in self.services.table_columns(self.spec.table):
            for row_id in ids:
                self.services.execute(
                    f"UPDATE {self.spec.table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                    (self.host.current_user.get("username", ""), datetime.now().isoformat(timespec="seconds"), row_id),
                )
                self.host.log_audit("delete", self.spec.table, int(row_id))
            self.refresh()
            self.host.refresh_dashboard()
            self.host.update_status_bar(f"{len(ids)} {self.spec.title.lower()} record(s) recycled")
            return
        for row_id in ids:
            self.services.execute(f"DELETE FROM {self.spec.table} WHERE id=?", (row_id,))
            self.host.log_audit("delete", self.spec.table, int(row_id))
        self.refresh()
        self.host.refresh_dashboard()
        self.host.update_status_bar(f"{len(ids)} {self.spec.title.lower()} record(s) deleted")

    def export_csv(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            str(OUTPUT_DIR / f"{self.spec.table}_{datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        rows = self.selected_rows() or self.rows
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([col.label for col in self.spec.columns])
            for row in rows:
                writer.writerow([row.get(col.key, "") for col in self.spec.columns])
        QMessageBox.information(self, "Exported", f"Saved {len(rows)} row(s) to:\n{path}")
        self.host.update_status_bar(f"{self.spec.title} exported")

    def _apply_defaults(self, vals: dict[str, Any], *, is_new: bool) -> None:
        now = datetime.now()
        if is_new:
            if "created_at" in self.spec.insert_columns:
                vals["created_at"] = now
            if "created_by" in self.spec.insert_columns:
                vals["created_by"] = self.host.current_user.get("username", "")