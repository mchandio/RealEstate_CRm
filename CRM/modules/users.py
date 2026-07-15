"""User management module."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy
from typing import Any

# ─── CRM module imports ───
from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import ROLE_PERMISSIONS
from CRM.dialogs.record import RecordDialog
from CRM.widgets.table import ExcelTableWidget, configure_multi_select_table, selected_table_row_indexes, select_all_table_rows, clear_table_selection

class UsersModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        title = QLabel("User Management")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        controls = QHBoxLayout()
        add = QPushButton("Add User")
        add.setObjectName("AccentButton")
        add.clicked.connect(self.add_user)
        edit = QPushButton("Edit / Password")
        edit.clicked.connect(self.edit_user)
        remove = QPushButton("Remove User")
        remove.setObjectName("DangerButton")
        remove.clicked.connect(self.remove_user)
        activate = QPushButton("Toggle Active")
        activate.clicked.connect(self.toggle_active)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        controls.addWidget(add)
        controls.addWidget(edit)
        controls.addWidget(remove)
        controls.addWidget(activate)
        controls.addStretch(1)
        controls.addWidget(refresh)
        layout.addLayout(controls)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected")
        self.selection_label.setObjectName("SelectionCount")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        selection.addWidget(self.selection_label)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        layout.addLayout(selection)
        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        layout.addWidget(self.table, 1)
        self.refresh()

    def edit_user(self) -> None:
        row = self.selected()
        if not row:
            QMessageBox.information(self, "Select", "Select one user first.")
            return
        fields = [
            FieldSpec("Username *", "username", required=True),
            FieldSpec("New Password", "password"),
            FieldSpec("Full Name *", "full_name", required=True),
            FieldSpec("Email", "email"),
            FieldSpec("Role", "role", "combo", options=list(ROLE_PERMISSIONS)),
            FieldSpec("Active", "is_active", "combo", "Yes", ["Yes", "No"]),
        ]
        initial = dict(row)
        initial["password"] = ""
        initial["is_active"] = "Yes" if row.get("is_active") else "No"
        dialog = RecordDialog("Edit User / Password", fields, initial, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        vals["username"] = str(vals.get("username") or "").strip()
        if not vals.get("username") or not vals.get("full_name"):
            QMessageBox.warning(self, "User", "Username and full name are required.")
            return
        if self.main.services.fetch_one(
            "SELECT id FROM users WHERE LOWER(TRIM(username))=LOWER(?) AND id<>?",
            (vals["username"], row["id"]),
        ):
            QMessageBox.warning(self, "User", "Username already exists.")
            return
        params = [
            vals["username"],
            vals["full_name"],
            vals.get("email", ""),
            vals.get("role", "Staff"),
            1 if vals.get("is_active") == "Yes" else 0,
        ]
        set_clause = "username=?, full_name=?, email=?, role=?, is_active=?"
        if vals.get("password"):
            set_clause += ", password_hash=?"
            params.append(self.main.services.hash_password(vals["password"]))
        params.append(row["id"])
        self.main.services.execute(f"UPDATE users SET {set_clause} WHERE id=?", tuple(params))
        self.refresh()

    def remove_user(self) -> None:
        row = self.selected()
        if not row:
            QMessageBox.information(self, "Select", "Select one user first.")
            return
        if row["id"] == self.main.current_user.get("id"):
            QMessageBox.warning(self, "User", "You cannot remove your own user while logged in.")
            return
        ask = QMessageBox.question(self, "Remove User", f"Remove login access for {row['username']}?")
        if ask != QMessageBox.Yes:
            return
        self.main.services.execute("UPDATE users SET is_active=0 WHERE id=?", (row["id"],))
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.main.services.fetch_all(
            "SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id"
        )
        headers = ["ID", "Username", "Full Name", "Email", "Role", "Active", "Last Login"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            values = [row["id"], row["username"], row["full_name"], row["email"], row["role"], "Yes" if row["is_active"] else "No", row["last_login"] or ""]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
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

    def add_user(self) -> None:
        fields = [
            FieldSpec("Username *", "username", required=True),
            FieldSpec("Password *", "password", required=True),
            FieldSpec("Full Name *", "full_name", required=True),
            FieldSpec("Email", "email"),
            FieldSpec("Role", "role", "combo", options=list(ROLE_PERMISSIONS)),
        ]
        dialog = RecordDialog("Add User", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        vals["username"] = str(vals.get("username") or "").strip()
        ok, message = self.main.services.create_user(vals["username"], vals["password"], vals["full_name"], vals["email"], vals["role"])
        if not ok:
            QMessageBox.warning(self, "User", message)
            return
        self.refresh()

    def toggle_active(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more users first.")
            return
        if len(rows) > 1:
            ask = QMessageBox.question(self, "Toggle Users", f"Toggle active status for {len(rows)} selected users?")
            if ask != QMessageBox.Yes:
                return
        for row in rows:
            value = 0 if row["is_active"] else 1
            self.main.services.execute("UPDATE users SET is_active=? WHERE id=?", (value, row["id"]))
        self.refresh()