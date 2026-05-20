"""Full PySide6 CRM application backed by the existing SQLite database.
This is the Qt replacement for the Tkinter UI in professional_crm.py. It keeps
the same database tables and business workflows while moving the desktop
experience to PySide6.
Run:
.venv\Scripts\python.exe qt_crm_app.py
"""
# FIX: Added missing underscores to __future__ import
from __future__ import annotations
import csv
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import socket
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from crm_core import AI_LIBS_AVAILABLE, APP_ROOT, DB_PATH, OUTPUT_DIR, IntelligenceService
from crm_core.db import SQLiteRepository
from crm_core.reports import (
    ReportResult,
    ReportService,
    export_report_csv,
    export_report_pdf,
    export_report_text,
)

try:
    from PySide6.QtCore import QDate, QEvent, Qt, QTimer, Signal
    from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPageLayout, QPageSize, QPixmap, QTextDocument
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
        QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
        QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QStackedWidget,
        QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
    )
except Exception as exc:  # pragma: no cover
    PYSIDE_IMPORT_ERROR = exc
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_IMPORT_ERROR = None
    PYSIDE_AVAILABLE = True

if not PYSIDE_AVAILABLE:  # pragma: no cover
    raise RuntimeError(
        "PySide6/Qt could not be imported. Reinstall PySide6 or rebuild the app "
        "with the PySide6 runtime files included."
    ) from PYSIDE_IMPORT_ERROR

def app_resource_path(*parts: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    bundled = bundle_root.joinpath(*parts)
    if bundled.exists():
        return bundled
    return APP_ROOT.joinpath(*parts)

def crm_logo_path() -> Path:
    return app_resource_path("company_logo", "RealEstateCRM_logo.png")

def crm_icon_path() -> Path:
    return app_resource_path("company_logo", "RealEstateCRM.ico")

def crm_app_icon() -> QIcon:
    icon_path = crm_icon_path()
    return QIcon(str(icon_path)) if icon_path.exists() else QIcon()

# NOTE: Trailing spaces in constants are preserved to match your original DB/schema logic.
COMMON_AREAS = [
    "Gulshan ", "Gulistan-e-Johar ", "Gulberg ", "Clifton ", "DHA ", "Defence ",
    "Saddar ", "Korangi ", "Landhi ", "Malir ", "North Nazimabad ", "Nazimabad ",
    "PECHS ", "Scheme 33 ", "Shah Faisal ", "Tariq Road ", "Bahadurabad ",
    "KDA Scheme ", "Military Account ", "Hyderi ", "Water Pump ", "FB Area ",
    "Liaquatabad ", "Jamshed Road ", "University Road ", "Super Highway ",
    "Rashid Minhas ", "Airport ", "Cantt ", "Garden ", "Boat Basin ", "Sea View ",
    "Marina ", "Gizri ", "Clifton Block 1 ", "Clifton Block 2 ", "Clifton Block 3 ",
    "Clifton Block 4 ", "Clifton Block 5 ", "Clifton Block 6 ", "Clifton Block 7 ",
    "Clifton Block 8 ", "Clifton Block 9 ", "DHA Phase 1 ", "DHA Phase 2 ",
    "DHA Phase 4 ", "DHA Phase 5 ", "DHA Phase 6 ", "DHA Phase 7 ", "DHA Phase 8 ",
]
DEAL_STAGES = ["Lead ", "Contacted ", "Visit Scheduled ", "Negotiation ", "Closed ", "Deal Done "]
DEAL_PRIORITIES = ["Low ", "Medium ", "High ", "Urgent "]
FACILITY_OPTIONS = [
    "lift ", "car parking ", "cctv ", "security ", "sweet water ", "salty water ",
    "gas ", "electercity 24/7 ", "electercity with loadshading ",
]
FACILITY_ALIASES = {
    "parking ": "car parking ", "car park ": "car parking ",
    "electricity 24/7 ": "electercity 24/7 ", "electric 24/7 ": "electercity 24/7 ",
    "electricity with load shedding ": "electercity with loadshading ",
    "electricity with loadshading ": "electercity with loadshading ",
    "electric with load shedding ": "electercity with loadshading ",
    "electric with loadshading ": "electercity with loadshading ",
    "load shedding ": "electercity with loadshading ", "loadshading ": "electercity with loadshading ",
}
LONG_TEXT_COLUMN_KEYS = {"facilities ", "remarks ", "approval_comment ", "description ", "notes ", "address "}
GLOBAL_SEARCH_HIDDEN_COLUMNS = {"cnic ", "password_hash "}
GLOBAL_SEARCH_MONEY_COLUMNS = {
    "amount ", "budget ", "budget_min ", "budget_max ", "monthly_rent ", "maintenance ",
    "maintenance_budget ", "maintenance_charge ", "deposit ", "demand ", "asking_price ",
    "sale_price ", "base_salary ", "commission_amount ", "deal_value ", "commissions_earned ",
    "bonuses ", "bonus ", "deductions ", "net_salary ", "total_income ", "total_expense ",
    "net_profit ", "expected_close_value ",
}
GLOBAL_SEARCH_PRIORITY_COLUMNS = [
    "id ", "date ", "date_created ", "date_posted ", "transaction_date ", "payment_date ",
    "client_name ", "owner_name ", "full_name ", "property_code ", "title ", "contact ",
    "contact_phone ", "phone ", "owner_contact ", "email ", "contact_email ",
    "property_requires ", "property_availability ", "property_type ", "location ",
    "budget ", "monthly_rent ", "demand ", "amount ", "status ", "approval_status ",
    "workflow_stage ", "priority ", "next_follow_up ", "remarks ", "notes ",
    "description ", "created_by ", "created_at ",
]
STAGE_PROBABILITY = {
    "Lead ": 10.0, "Contacted ": 25.0, "Visit Scheduled ": 45.0,
    "Negotiation ": 70.0, "Closed ": 90.0, "Deal Done ": 100.0,
}
DEAL_TABLES = ("rent_requirements ", "rent_availability ", "sale_requirements ", "sale_availability ")
GLOBAL_SEARCH_SOURCES = [
    ("Rent Requirement ", "rent_requirements "), ("Rent Availability ", "rent_availability "),
    ("Sale Requirement ", "sale_requirements "), ("Sale Availability ", "sale_availability "),
]
GLOBAL_SEARCH_SOURCE_LABELS = dict(GLOBAL_SEARCH_SOURCES)
LOCAL_SERVICE_PORT = 6090
DATE_FORM_KEYS = {"date ", "transaction_date ", "hire_date ", "next_follow_up "}
EMAIL_FORM_KEYS = {"email ", "company_email "}
PHONE_FORM_KEYS = {"contact ", "phone ", "owner_contact ", "company_phone "}
CNIC_FORM_KEYS = {"cnic "}
PERCENT_FORM_KEYS = {"commission_rate ", "deal_probability ", "default_commission ", "tax_rate "}
ROLE_PERMISSIONS = {
    "Super Admin ": ["dashboard ", "rent ", "financial ", "employees ", "reports ", "ai ", "settings ", "users ", "backup ", "delete "],
    "Admin ": ["dashboard ", "rent ", "financial ", "employees ", "reports ", "ai ", "settings ", "users ", "backup ", "delete "],
    "Manager ": ["dashboard ", "rent ", "financial_view ", "employees ", "reports ", "ai "],
    "Staff ": ["rent "],
    "Viewer ": ["dashboard ", "rent_view ", "employees_view ", "reports "],
}

def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").replace("Rs.", "").strip())
    except (TypeError, ValueError):
        return default

def clean_number_text(value: Any) -> str:
    return str(value or "").replace(",", "").replace("Rs.", "").strip()

def is_valid_number_text(value: Any) -> bool:
    text = clean_number_text(value)
    if not text:
        return True
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False

def is_valid_date_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_valid_email_text(value: Any) -> bool:
    text = str(value or " ").strip()
    if not text:
        return True
    if "  " in text or text.count("@ ") != 1:
        return False
    local, domain = text.split("@ ", 1)
    return bool(local) and ". " in domain and not domain.startswith(". ") and not domain.endswith(". ")

def is_valid_phone_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    allowed = set("0123456789+-() ")
    digits = "".join(ch for ch in text if ch.isdigit())
    return all(ch in allowed for ch in text) and 7 <= len(digits) <= 15

def is_valid_cnic_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) == 13 and all(ch.isdigit() or ch == "-" for ch in text)

def validate_form_value(
    key: str, label: str, value: Any, required: bool = False, numeric: bool = False,
    options: list[str] | None = None, strict_options: bool = False,
) -> None:
    text = str(value or " ").strip()
    clean_label = label.replace(" ", " ").strip()
    if required and not text:
        raise ValueError(f"Please enter {clean_label}.")
    if numeric and text and not is_valid_number_text(text):
        raise ValueError(f"Please enter a valid number for {clean_label}.")
    if key in DATE_FORM_KEYS and text and not is_valid_date_text(text):
        raise ValueError(f"{clean_label} must be in YYYY-MM-DD format.")
    if key in EMAIL_FORM_KEYS and text and not is_valid_email_text(text):
        raise ValueError(f"Please enter a valid email address for {clean_label}.")
    if key in PHONE_FORM_KEYS and text and not is_valid_phone_text(text):
        raise ValueError(f"Please enter a valid phone/contact number for {clean_label}.")
    if key in CNIC_FORM_KEYS and text and not is_valid_cnic_text(text):
        raise ValueError(f"{clean_label} must contain exactly 13 digits.")
    if key in PERCENT_FORM_KEYS and text and is_valid_number_text(text):
        number = safe_float(text)
        if number < 0 or number > 100:
            raise ValueError(f"{clean_label} must be between 0 and 100.")
    if strict_options and text and options and text not in options:
        raise ValueError(f"Please select a valid option for {clean_label}.")

def money(value: Any, symbol: str = "Rs.") -> str:
    return f"{symbol}{safe_float(value):,.0f}"

def normalize_facility_name(value: Any) -> str:
    text = str(value or " ").strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return FACILITY_ALIASES.get(text, text)

def parse_facilities(value: Any, options: list[str] | None = None) -> set[str]:
    option_list = options or FACILITY_OPTIONS
    lookup = {normalize_facility_name(option): option for option in option_list}
    selected: set[str] = set()
    if isinstance(value, (list, tuple, set)):
        tokens = [str(item) for item in value]
        raw_text = ", ".join(tokens)
    else:
        raw_text = str(value or "")
    tokens = re.split(r"[,;|\n]+", raw_text)
    for token in tokens:
        normalized = normalize_facility_name(token)
        if normalized in lookup:
            selected.add(lookup[normalized])
    haystack = normalize_facility_name(raw_text)
    for normalized, label in lookup.items():
        if normalized and normalized in haystack:
            selected.add(label)
    return selected

def gen_id(prefix: str = "") -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}"

def configure_legal_landscape_printer(printer: QPrinter) -> None:
    page_layout = QPageLayout(
        QPageSize(QPageSize.PageSizeId.Legal), QPageLayout.Orientation.Landscape,
        # FIX: QMarginsF must be a single token, not "QMargin sF" or "QMargins F"
        QMarginsF(7, 7, 7, 7),
    )
    printer.setPageLayout(page_layout)

def ensure_database() -> None:
    """Reuse the existing production schema initializer and migrations."""
    from professional_crm import Database
    Database.init_all()
    ensure_qt_schema()

def ensure_qt_schema() -> None:
    """Add Qt-screen columns that older deployed databases may be missing."""
    additions = {"rent_availability ": [("option1 ", "TEXT "), ("option2 ", "TEXT ")]}
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for table, columns in additions.items():
            existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
            for column, column_type in columns:
                if column not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            conn.commit()

class CRMServices:
    # FIX: Corrected __init__ method signature
    def __init__(self):
        self.repo = SQLiteRepository(DB_PATH)

    def fetch_all(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict]:
        return self.repo.fetch_all(query, params)

    def fetch_one(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> dict | None:
        return self.repo.fetch_one(query, params)

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        return self.repo.execute(query, params)

    def insert(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        with self.repo.connect() as conn:
            cur = conn.execute(query, params)
            conn.commit()
            return int(cur.lastrowid)

    # FIX: Corrected parameter typo `def ault` -> `default`
    def settings_get(self, key: str, default: str = " ") -> str:
        row = self.fetch_one("SELECT value FROM app_settings WHERE key=? ", (key,))
        return str(row["value"]) if row else default

    def settings_set(self, key: str, value: str) -> None:
        self.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?) ", (key, value))

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username: str, password: str) -> dict | None:
        row = self.fetch_one("SELECT * FROM users WHERE username=? AND is_active=1 ", (username,))
        if row and row.get("password_hash ") == self.hash_password(password):
            now = datetime.now()
            self.execute("UPDATE users SET last_login=? WHERE id=? ", (now, row["id"]))
            self.execute("INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?) ", (row["id"], now, "Success "))
            return row
        self.execute("INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?) ", (None, datetime.now(), "Failed "))
        return None

    def create_user(self, username: str, password: str, full_name: str, email: str, role: str) -> tuple[bool, str]:
        if self.fetch_one("SELECT id FROM users WHERE username=? ", (username,)):
            return False, "Username already exists."
        self.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at)
               VALUES (?,?,?,?,?,1,?) """,
            (username, self.hash_password(password), full_name, email, role, datetime.now()),
        )
        return True, "User created."

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        row = self.fetch_one("SELECT password_hash FROM users WHERE id=? ", (user_id,))
        if not row:
            return False, "User not found."
        if row["password_hash "] != self.hash_password(old_password):
            return False, "Current password is incorrect."
        self.execute("UPDATE users SET password_hash=? WHERE id=? ", (self.hash_password(new_password), user_id))
        return True, "Password changed."

@dataclass
class FieldSpec:
    label: str
    key: str
    kind: str = "entry"
    default: Any = ""
    options: list[str] = field(default_factory=list)
    required: bool = False
    numeric: bool = False

@dataclass
class ColumnSpec:
    key: str
    label: str
    formatter: Callable[[Any, str], str] | None = None
    width: int = 130

@dataclass
class TableSpec:
    title: str
    table: str
    columns: list[ColumnSpec]
    form_fields: list[FieldSpec]
    insert_columns: list[str]
    update_columns: list[str]
    permission: str = "rent"
    order_by: str = "id DESC"
    deal_table: bool = False

class ExcelTableWidget(QTableWidget):
    # FIX: Corrected __init__ and split identifiers
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
    table.setSelectionBehavior(QTableWidget.SelectItems)
    table.setSelectionMode(QTableWidget.ExtendedSelection)
    table.verticalHeader().setVisible(False)

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

class LoginDialog(QDialog):
    # FIX: Corrected __init__ and split method names
    def __init__(self, services: CRMServices):
        super().__init__()
        self.services = services
        self.current_user: dict | None = None
        self.setWindowTitle("Real Estate CRM Login")
        self.setWindowIcon(crm_app_icon())
        self.setMinimumWidth(430)
        self.setObjectName("LoginDialog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        title = QLabel("Real Estate CRM ")
        title.setObjectName("LoginTitle ")
        subtitle = QLabel("Sign in to open the Qt workspace ")
        subtitle.setObjectName("MutedText ")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        # FIX: Removed invalid space in method call
        self.password.setEchoMode(QLineEdit.Password)
        self.username.setText("admin ")
        self.username.selectAll()
        form.addRow("Username ", self.username)
        form.addRow("Password ", self.password)
        layout.addLayout(form)
        hint = QLabel("Default first-run account is admin / admin. ")
        hint.setObjectName("MutedText ")
        layout.addWidget(hint)
        buttons = QDialogButtonBox()
        self.login_button = buttons.addButton("Login ", QDialogButtonBox.AcceptRole)
        buttons.addButton("Cancel ", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        # FIX: Removed invalid space before dot
        self.password.returnPressed.connect(self.try_login)

    def try_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        user = self.services.login(username, password)
        if not user:
            QMessageBox.warning(self, "Login Failed ", "Invalid username or password. ")
            return
        self.current_user = user
        self.accept()

class RecordDialog(QDialog):
    # FIX: Corrected __init__ and multiple split identifiers
    def __init__(self, title: str, fields: list[FieldSpec], data: dict | None = None,
                 parent: QWidget | None = None, *, allow_save_new: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(860, 640)
        self.setMinimumSize(720, 520)
        self.widgets: dict[str, QWidget] = {}
        self.fields = fields
        self.save_and_new = False
        self.allow_save_new = allow_save_new
        data = data or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        heading = QLabel(title)
        heading.setObjectName("DialogTitle ")
        layout.addWidget(heading)
        hint = QLabel("Required fields are marked with *. Use Tab to move quickly between fields. ")
        hint.setObjectName("MutedText ")
        layout.addWidget(hint)
        if self._has_property_fields():
            layout.addLayout(self._template_bar())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 8, 0, 8)
        grid.setHorizontalSpacing(16)
        # FIX: Corrected split method name
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        row = 0
        col_group = 0
        for spec in fields:
            raw_default = spec.default() if callable(spec.default) else spec.default
            value = data.get(spec.key, raw_default)
            widget = self._make_widget(spec, value)
            self.widgets[spec.key] = widget
            label = QLabel(spec.label)
            label.setObjectName("RequiredLabel " if spec.required else "FormLabel ")
            if spec.kind in {"text ", "facilities "}:
                if col_group:
                    row += 1
                    col_group = 0
                label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                # FIX: Corrected split variable name
                grid.addWidget(label, row, 0)
                grid.addWidget(widget, row, 1, 1, 3)
                row += 1
                col_group = 0
                continue
            label_col = 0 if col_group == 0 else 2
            # FIX: Corrected split variable name
            field_col = 1 if col_group == 0 else 3
            grid.addWidget(label, row, label_col)
            grid.addWidget(widget, row, field_col)
            col_group += 1
            if col_group >= 2:
                row += 1
                col_group = 0
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        buttons = QDialogButtonBox()
        save = buttons.addButton("Save ", QDialogButtonBox.AcceptRole)
        save.clicked.connect(self.accept)
        if allow_save_new:
            save_new = buttons.addButton("Save & New ", QDialogButtonBox.ActionRole)
            save_new.clicked.connect(self.accept_save_new)
        cancel = buttons.addButton("Cancel ", QDialogButtonBox.RejectRole)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _has_property_fields(self) -> bool:
        keys = {field.key for field in self.fields}
        return bool({"property_requires ", "property_availability ", "size ", "floor "} & keys)

    def _template_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Quick fill "))
        templates = [
            ("Flat ", {"property_requires ": "flat ", "property_availability ": "flat ", "size ": "double-bed ", "floor ": "3rd "}),
            ("Shop ", {"property_requires ": "shop ", "property_availability ": "shop ", "size ": "ground floor ", "floor ": "Ground "}),
            ("House ", {"property_requires ": "house ", "property_availability ": "house ", "size ": "single story ", "floor ": "Ground "}),
            ("Office ", {"property_requires ": "office ", "property_availability ": "office ", "size ": "any floor ", "floor ": "1st "}),
            ("Plot ", {"property_requires ": "plot ", "property_availability ": "plot ", "size ": " ", "floor ": "-"}),
            ("Villa ", {"property_requires ": "villa ", "property_availability ": "villa ", "size ": "double story ", "floor ": "Ground "}),
        ]
        for label, values in templates:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, v=values: self.apply_template(v))
            bar.addWidget(button)
        bar.addStretch(1)
        return bar

    def apply_template(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            widget = self.widgets.get(key)
            if not widget:
                continue
            if isinstance(widget, QComboBox):
                idx = widget.findText(value)
                if idx < 0 and value:
                    widget.addItem(value)
                    idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setEditText(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)

    def _make_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        if spec.kind == "text ":
            widget = QTextEdit()
            widget.setMinimumHeight(82)
            widget.setMaximumHeight(120)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            widget.setPlainText(" " if value is None else str(value))
            return widget
        if spec.kind == "facilities ":
            return self._make_facilities_widget(spec, value)
        if spec.kind in {"combo ", "combo_other ", "autocomplete "}:
            widget = QComboBox()
            widget.addItems(spec.options)
            widget.setEditable(spec.kind != "combo ")
            if value not in (None, " "):
                idx = widget.findText(str(value))
                if idx < 0:
                    widget.addItem(str(value))
                    idx = widget.findText(str(value))
                if spec.kind == "combo ":
                    widget.setCurrentIndex(idx)
                elif idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setEditText(str(value))
            return widget
        if spec.kind == "date ":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd ")
            if value:
                date = QDate.fromString(str(value), "yyyy-MM-dd ")
                widget.setDate(date if date.isValid() else QDate.currentDate())
            else:
                widget.setDate(QDate.currentDate())
            return widget
        # FIX: Corrected split class name
        widget = QLineEdit()
        widget.setText(" " if value is None else str(value))
        if spec.numeric:
            widget.setPlaceholderText("0 ")
        elif spec.key in DATE_FORM_KEYS:
            widget.setPlaceholderText("YYYY-MM-DD ")
        elif spec.key in PHONE_FORM_KEYS:
            widget.setPlaceholderText("+92-300-0000000 ")
        elif spec.key in EMAIL_FORM_KEYS:
            widget.setPlaceholderText("name@example.com ")
        return widget

    def _make_facilities_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("FacilitiesBox ")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        # FIX: Corrected split method name
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = spec.options or FACILITY_OPTIONS
        selected = parse_facilities(value, options)
        boxes: list[QCheckBox] = []
        for index, label in enumerate(options):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("FacilityCheck ")
            checkbox.setChecked(label in selected)
            checkbox.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            grid.addWidget(checkbox, index // 3, index % 3)
            boxes.append(checkbox)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        frame.facility_boxes = boxes
        return frame

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for spec in self.fields:
            value = self.raw_value(spec)
            if spec.numeric:
                value = safe_float(value)
            values[spec.key] = value
        return values

    def raw_value(self, spec: FieldSpec) -> str:
        widget = self.widgets[spec.key]
        if spec.kind == "facilities ":
            boxes = getattr(widget, "facility_boxes ", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QDateEdit):
            return widget.date().toString("yyyy-MM-dd ")
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return " "

    def validate(self) -> tuple[bool, str]:
        try:
            for spec in self.fields:
                raw = self.raw_value(spec)
                widget = self.widgets[spec.key]
                effective_options: list[str] | None = spec.options if spec.options else None
                if spec.kind == "combo " and isinstance(widget, QComboBox):
                    effective_options = [widget.itemText(i) for i in range(widget.count())]
                validate_form_value(
                    # FIX: Corrected split variable name
                    spec.key,
                    spec.label,
                    raw,
                    required=spec.required,
                    numeric=spec.numeric,
                    options=effective_options,
                    strict_options=(spec.kind == "combo "),
                )
        except ValueError as exc:
            return False, str(exc)
        return True, " "

    def accept(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required ", message)
            return
        self.save_and_new = False
        super().accept()

    def accept_save_new(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required ", message)
            return
        self.save_and_new = True
        super().accept()

class CommentDialog(QDialog):
    # FIX: Corrected __init__
    def __init__(self, title: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.text = QTextEdit()
        self.text.setMinimumHeight(90)
        layout.addWidget(self.text)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self.text.toPlainText().strip()

class MetricCard(QFrame):
    # FIX: Corrected __init__
    def __init__(self, title: str, value: str, note: str = ""):
        super().__init__()
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("MetricTitle")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        note_label = QLabel(note)
        note_label.setObjectName("MetricNote")
        note_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(note_label)

class NavItem(QFrame):
    clicked = Signal(str)
    # FIX: Corrected __init__ and split variable names
    def __init__(self, key: str, label: str, abbreviation: str):
        super().__init__()
        self.key = key
        self._checked = False
        self.setObjectName("NavItem ")
        self.setProperty("active ", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 10, 0)
        layout.setSpacing(10)
        self.indicator = QFrame()
        self.indicator.setObjectName("NavIndicator ")
        self.indicator.setProperty("active ", False)
        self.indicator.setFixedSize(3, 22)
        layout.addWidget(self.indicator)
        self.icon = QLabel(abbreviation)
        self.icon.setObjectName("NavIcon ")
        self.icon.setProperty("active ", False)
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setFixedSize(26, 26)
        layout.addWidget(self.icon)
        self.text_label = QLabel(label)
        self.text_label.setObjectName("NavText ")
        self.text_label.setProperty("active ", False)
        self.text_label.setMinimumWidth(0)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.text_label, 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)

    def setChecked(self, checked: bool) -> None:
        self._checked = checked
        for widget in (self, self.indicator, self.icon, self.text_label):
            widget.setProperty("active ", checked)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def isChecked(self) -> bool:
        return self._checked

class DataTablePage(QWidget):
    # FIX: Corrected __init__ and multiple split identifiers
    def __init__(self, main: "ModernCRMWindow", spec: TableSpec, *,
                 extra_buttons: list[tuple[str, Callable[[], None], str]] | None = None):
        super().__init__()
        self.main = main
        self.services = main.services
        self.spec = spec
        self.rows: list[dict] = []
        self.extra_buttons = extra_buttons or []
        self._build()
        self.refresh()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel(self.spec.title)
        title.setObjectName("SectionTitle ")
        header.addWidget(title)
        header.addStretch(1)
        can_edit = self.main.can_edit(self.spec.permission) and bool(self.spec.form_fields)
        if can_edit:
            self.add_btn = QPushButton("Add ")
            self.add_btn.setObjectName("AccentButton ")
            self.add_btn.clicked.connect(self.add_record)
            header.addWidget(self.add_btn)
            self.edit_btn = QPushButton("Edit ")
            self.edit_btn.clicked.connect(self.edit_record)
            header.addWidget(self.edit_btn)
            self.delete_btn = QPushButton("Delete ")
            self.delete_btn.setObjectName("DangerButton ")
            self.delete_btn.clicked.connect(self.delete_record)
            header.addWidget(self.delete_btn)
        for label, callback, kind in self.extra_buttons:
            button = QPushButton(label)
            if kind:
                button.setObjectName(kind)
            button.clicked.connect(callback)
            header.addWidget(button)
        layout.addLayout(header)
        tools = QHBoxLayout()
        self.selection_label = QLabel("0 selected ")
        self.selection_label.setObjectName("SelectionCount ")
        select_all = QPushButton("Select All ")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection ")
        clear.clicked.connect(self.clear_selection)
        details = QPushButton("Details ")
        details.clicked.connect(self.show_details)
        copy = QPushButton("Copy Selected ")
        copy.clicked.connect(self.copy_selected_rows)
        refresh = QPushButton("Refresh ")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("Export ")
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
        # FIX: Corrected split function name
        configure_multi_select_table(self.table)
        if can_edit:
            self.table.doubleClicked.connect(self.edit_record)
        # FIX: Corrected split method name
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def selected_row_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_row_indexes()]

    def selected_row(self) -> dict | None:
        rows = self.selected_rows()
        return rows[0] if rows else None

    def require_single_row(self, action: str = "this action ") -> dict | None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select a row first. ")
            return None
        if len(rows) > 1:
            QMessageBox.information(self, "Select One ", f"Select only one row for {action}. ")
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
        self.selection_label.setText(f"{count} of {total} selected ")

    def show_details(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select a row first. ")
            return
        details: list[str] = []
        for row in rows:
            full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=? ", (row["id"],)) or row
            details.append(f"{self.spec.title} #{row.get('id')} ")
            details.append("-" * 72)
            details.extend(f"{key}: {value if value not in (None, '') else '-'} " for key, value in full.items())
            details.append(" ")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.spec.title} Details ")
        dialog.resize(720, 520)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas ", 10))
        text.setPlainText("\n".join(details))
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more rows first. ")
            return
        lines = ["\t".join(col.label for col in self.spec.columns)]
        for row in rows:
            lines.append("\t".join(str(row.get(col.key, " ") or " ") for col in self.spec.columns))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied ", f"{len(rows)} selected row(s) copied to clipboard. ")

    def refresh(self) -> None:
        columns = [col.key for col in self.spec.columns]
        sql = f"SELECT {', '.join(columns)} FROM {self.spec.table} ORDER BY {self.spec.order_by} "
        self.rows = self.services.fetch_all(sql)
        self.table.setColumnCount(len(self.spec.columns))
        self.table.setHorizontalHeaderLabels([col.label for col in self.spec.columns])
        self.table.setRowCount(len(self.rows))
        has_long_text = any(col.key in LONG_TEXT_COLUMN_KEYS for col in self.spec.columns)
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(self.spec.columns):
                value = row.get(col.key)
                # FIX: Corrected split keyword
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or " ")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setForeground(QColor("#0f172a "))
                if col.key in LONG_TEXT_COLUMN_KEYS:
                    item.setToolTip(text)
                    item.setText(text.replace("\r\n", "  ").replace("\n", "  "))
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if col.key in {"approval_status ", "workflow_stage ", "priority "}:
                    self._style_status_item(item, text)
                self.table.setItem(row_idx, col_idx, item)
            if has_long_text:
                self.table.setRowHeight(row_idx, 42)
        for idx, col in enumerate(self.spec.columns):
            self.table.setColumnWidth(idx, col.width)
        # FIX: Corrected split enum value
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.update_selection_label()

    def _style_status_item(self, item: QTableWidgetItem, text: str) -> None:
        colors = {
            "Approved ": "#dcfce7 ", "Pending ": "#fef3c7 ", "Resend ": "#fee2e2 ",
            "Urgent ": "#fee2e2 ", "High ": "#ffedd5 ", "Deal Done ": "#dcfce7 ",
        }
        if text in colors:
            item.setBackground(QColor(colors[text]))

    def add_record(self) -> None:
        while True:
            dialog = RecordDialog(f"Add {self.spec.title} ", self.spec.form_fields, parent=self, allow_save_new=True)
            if dialog.exec() != QDialog.Accepted:
                return
            vals = dialog.values()
            # FIX: Corrected split method name
            self._apply_defaults(vals, is_new=True)
            cols = self.spec.insert_columns
            placeholders = ", ".join(["?"] * len(cols))
            self.services.execute(f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders}) ", tuple(vals.get(col) for col in cols))
            self.refresh()
            self.main.refresh_dashboard()
            if not dialog.save_and_new:
                return

    def edit_record(self) -> None:
        row = self.require_single_row("editing ")
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=? ", (row["id"],))
        dialog = RecordDialog(f"Edit {self.spec.title} ", self.spec.form_fields, full, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        self._apply_defaults(vals, is_new=False)
        # FIX: Corrected split variable name
        cols = self.spec.update_columns
        assignments = ", ".join(f"{col}=? " for col in cols)
        params = tuple(vals.get(col) for col in cols) + (row["id"],)
        self.services.execute(f"UPDATE {self.spec.table} SET {assignments} WHERE id=? ", params)
        self.refresh()
        self.main.refresh_dashboard()

    def delete_record(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more rows first. ")
            return
        if not has_permission(self.main.role, "delete "):
            QMessageBox.warning(self, "Access Denied ", "You do not have permission to delete records. ")
            return
        ids = [row["id "] for row in rows]
        ask = QMessageBox.question(self, "Delete ", f"Delete {len(ids)} selected record(s) from {self.spec.table}? ")
        if ask != QMessageBox.Yes:
            return
        for row_id in ids:
            self.services.execute(f"DELETE FROM {self.spec.table} WHERE id=? ", (row_id,))
        self.refresh()
        self.main.refresh_dashboard()

    def export_csv(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV ", str(OUTPUT_DIR / f"{self.spec.table}_{datetime.now().strftime('%Y%m%d')}.csv "), "CSV Files (*.csv) ")
        if not path:
            return
        rows = self.selected_rows() or self.rows
        with open(path, "w ", newline=" ", encoding="utf-8 ") as handle:
            writer = csv.writer(handle)
            writer.writerow([col.label for col in self.spec.columns])
            for row in rows:
                writer.writerow([row.get(col.key, " ") for col in self.spec.columns])
        QMessageBox.information(self, "Exported ", f"Saved {len(rows)} row(s) to:\n{path} ")

    def _apply_defaults(self, vals: dict[str, Any], *, is_new: bool) -> None:
        now = datetime.now()
        if is_new:
            if "created_at " in self.spec.insert_columns:
                vals["created_at "] = now
            if "created_by " in self.spec.insert_columns:
                vals["created_by "] = self.main.current_user.get("username ", " ")
        if self.spec.deal_table:
            stage = vals.get("workflow_stage ") or "Lead "
            priority = vals.get("priority ") or "Medium "
            probability = safe_float(vals.get("deal_probability "), STAGE_PROBABILITY.get(stage, 10.0))
            if probability <= 0:
                probability = STAGE_PROBABILITY.get(stage, 10.0)
            vals["workflow_stage "] = stage
            vals["priority "] = priority
            vals["deal_probability "] = probability
            vals["expected_close_value "] = safe_float(vals.get("expected_close_value "), 0)
            if not vals["expected_close_value "]:
                for key in ("budget ", "monthly_rent ", "demand "):
                    if key in vals:
                        vals["expected_close_value "] = safe_float(vals.get(key))
                        break
            if is_new:
                vals["approval_status "] = "Pending "
                vals["approval_comment "] = " "

class DealModule(QWidget):
    # FIX: Corrected __init__ and split method name
    def __init__(self, main: "ModernCRMWindow", title: str, requirement_spec: TableSpec, availability_spec: TableSpec):
        super().__init__()
        self.main = main
        self.requirement_spec = requirement_spec
        self.availability_spec = availability_spec
        self.kind = "rent" if requirement_spec.table.startswith("rent") else "sale"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        top.addWidget(heading)
        top.addStretch(1)
        report_button = QPushButton(f"Generate {self.kind.title()} Report ")
        report_button.setObjectName("AccentButton ")
        report_button.clicked.connect(lambda: self.main.preview_report(self.kind))
        add_req = QPushButton("New Requirement ")
        add_av = QPushButton("New Availability ")
        add_req.clicked.connect(lambda: self.requirements.add_record())
        add_av.clicked.connect(lambda: self.availability.add_record())
        top.addWidget(add_req)
        top.addWidget(add_av)
        top.addWidget(report_button)
        layout.addLayout(top)
        tabs = QTabWidget()
        self.requirements = DataTablePage(main, requirement_spec, extra_buttons=self._deal_buttons(lambda: self.requirements, requirement_spec.table))
        self.availability = DataTablePage(main, availability_spec, extra_buttons=self._deal_buttons(lambda: self.availability, availability_spec.table))
        tabs.addTab(self.requirements, "Requirements ")
        tabs.addTab(self.availability, "Availability ")
        layout.addWidget(tabs, 1)

    def _deal_buttons(self, page_getter: Callable[[], DataTablePage], table: str) -> list[tuple[str, Callable[[], None], str]]:
        return [
            ("Workflow ", lambda: self.main.workflow_dialog(page_getter(), table), " "),
            ("Next Stage ", lambda: self.main.advance_stage(page_getter(), table), "AccentButton "),
            ("AI Match ", lambda: self.main.ai_match(page_getter(), table), " "),
            ("Approve ", lambda: self.main.set_approval(page_getter(), table, "Approved "), "AccentButton "),
            ("Resend ", lambda: self.main.set_approval(page_getter(), table, "Resend "), " "),
            ("Report ", lambda: self.main.preview_report("rent " if table.startswith("rent ") else "sale "), " "),
        ]

    def refresh(self) -> None:
        self.requirements.refresh()
        self.availability.refresh()

class SummaryPage(QWidget):
    # FIX: Corrected __init__ and split class name
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        refresh = QPushButton("Refresh Summary ")
        refresh.setObjectName("AccentButton ")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("Export ")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Financial Summary "))
        controls.addStretch(1)
        controls.addWidget(refresh)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        # FIX: Corrected split class name
        self.text.setFont(QFont("Consolas ", 10))
        layout.addWidget(self.text, 1)
        self.refresh()

    def refresh(self) -> None:
        s = self.main.services
        income = safe_float((s.fetch_one("SELECT SUM(amount) AS total FROM income_transactions ") or {}).get("total "))
        expenses = safe_float((s.fetch_one("SELECT SUM(amount) AS total FROM expense_transactions ") or {}).get("total "))
        profit = income - expenses
        lines = ["=" * 72, f"FINANCIAL SUMMARY - {datetime.now().strftime('%Y-%m-%d')}", f"Company: {self.main.company_name} ", "=" * 72, " ", "INCOME BY TYPE ", "-" * 72]
        for row in s.fetch_all("SELECT income_type, COUNT(*) AS qty, SUM(amount) AS total FROM income_transactions GROUP BY income_type "):
            lines.append(f"{row.get('income_type') or 'Other': <35} Qty:{row['qty']: >4} {money(row['total'], self.main.currency_symbol): >18} ")
        lines += [" ", f"TOTAL INCOME:   {money(income, self.main.currency_symbol)} ", " ", "EXPENSES BY CATEGORY ", "-" * 72]
        for row in s.fetch_all("SELECT expense_category, COUNT(*) AS qty, SUM(amount) AS total FROM expense_transactions GROUP BY expense_category "):
            lines.append(f"{row.get('expense_category') or 'Other': <35} Qty:{row['qty']: >4} {money(row['total'], self.main.currency_symbol): >18} ")
        margin = (profit / income * 100) if income else 0
        lines += [" ", f"TOTAL EXPENSES: {money(expenses, self.main.currency_symbol)} ", "=" * 72, f"NET PROFIT:     {money(profit, self.main.currency_symbol)} ", f"PROFIT MARGIN:  {margin:.1f}% ", "=" * 72]
        self.text.setPlainText("\n".join(lines))

    def export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Financial Summary ", str(OUTPUT_DIR / "financial_summary.txt "), "Text Files (*.txt) ")
        if path:
            Path(path).write_text(self.text.toPlainText(), encoding="utf-8 ")
            QMessageBox.information(self, "Exported ", f"Saved to:\n{path} ")

class FinancialModule(QWidget):
    # FIX: Corrected __init__ and split variable name
    def __init__(self, main: "ModernCRMWindow ", income_spec: TableSpec, expense_spec: TableSpec):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Financials ")
        heading.setObjectName("PageTitle ")
        layout.addWidget(heading)
        tabs = QTabWidget()
        self.income = DataTablePage(main, income_spec)
        self.expenses = DataTablePage(main, expense_spec)
        self.summary = SummaryPage(main)
        tabs.addTab(self.income, "Income ")
        tabs.addTab(self.expenses, "Expenses ")
        tabs.addTab(self.summary, "Summary ")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.income.refresh()
        self.expenses.refresh()
        self.summary.refresh()

class AttendancePage(QWidget):
    # FIX: Corrected __init__ and split variable names
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd ")
        load = QPushButton("Load ")
        load.clicked.connect(self.refresh)
        present = QPushButton("Mark Present ")
        present.setObjectName("AccentButton ")
        present.clicked.connect(lambda: self.mark("Present "))
        absent = QPushButton("Mark Absent ")
        absent.setObjectName("DangerButton ")
        absent.clicked.connect(lambda: self.mark("Absent "))
        leave = QPushButton("Mark Leave ")
        leave.clicked.connect(lambda: self.mark("Leave "))
        controls.addWidget(QLabel("Date "))
        controls.addWidget(self.date)
        controls.addWidget(load)
        controls.addStretch(1)
        controls.addWidget(present)
        controls.addWidget(absent)
        controls.addWidget(leave)
        layout.addLayout(controls)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected ")
        self.selection_label.setObjectName("SelectionCount ")
        select_all = QPushButton("Select All ")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection ")
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

    def refresh(self) -> None:
        date = self.date.date().toString("yyyy-MM-dd ")
        marked = self.main.services.fetch_all(
            """SELECT a.id, e.id AS employee_id, e.full_name, a.date, a.status, a.notes
               FROM attendance a JOIN employees e ON a.employee_id=e.id
               WHERE a.date=? ORDER BY e.full_name """,
            (date,),
        )
        if marked:
            self.rows = marked
        else:
            self.rows = [
                {"id ": None, "employee_id ": row["id"], "full_name ": row["full_name"], "date ": date, "status ": "Not Marked ", "notes ": " "}
                for row in self.main.services.fetch_all("SELECT id, full_name FROM employees WHERE status='Active' ORDER BY full_name ")
            ]
        headers = ["ID ", "Employee ", "Date ", "Status ", "Notes "]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            values = [row.get("id ") or " ", row.get("full_name ") or " ", row.get("date ") or " ", row.get("status ") or " ", row.get("notes ") or " "]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
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
        return rows[0] if rows else None

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected ")

    def mark(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more employee rows first. ")
            return
        date = self.date.date().toString("yyyy-MM-dd ")
        for row in rows:
            existing = self.main.services.fetch_one("SELECT id FROM attendance WHERE employee_id=? AND date=? ", (row["employee_id"], date))
            if existing:
                self.main.services.execute("UPDATE attendance SET status=? WHERE employee_id=? AND date=? ", (status, row["employee_id"], date))
            else:
                self.main.services.execute("INSERT INTO attendance (employee_id, date, status) VALUES (?,?,?) ", (row["employee_id"], date, status))
        self.refresh()

class SalaryPage(DataTablePage):
    # FIX: Corrected __init__ and split variable name
    def __init__(self, main: "ModernCRMWindow", spec: TableSpec):
        super().__init__(main, spec, extra_buttons=[("Pay Salary", self.pay_salary, "AccentButton")])

    def refresh(self) -> None:
        self.rows = self.main.services.fetch_all(
            """SELECT sp.id, e.full_name, sp.month, sp.year, sp.base_salary, sp.bonus,
                  sp.deductions, sp.net_salary, sp.payment_method
               FROM salary_payments sp JOIN employees e ON sp.employee_id=e.id
               ORDER BY sp.id DESC """
        )
        columns = self.spec.columns
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c.label for c in columns])
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            for c, col in enumerate(columns):
                value = row.get(col.key)
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or " ")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.update_selection_label()

    def pay_salary(self) -> None:
        employees = self.main.services.fetch_all("SELECT id, full_name, base_salary FROM employees WHERE status='Active' ORDER BY full_name ")
        if not employees:
            QMessageBox.information(self, "No Employees ", "No active employees found. ")
            return
        names = [f"{e['full_name']} (Base: {money(e['base_salary'], self.main.currency_symbol)}) " for e in employees]
        fields = [
            FieldSpec("Employee * ", "employee ", "combo ", options=names, required=True),
            FieldSpec("Month * ", "month ", "combo ", options=["January ", "February ", "March ", "April ", "May ", "June ", "July ", "August ", "September ", "October ", "November ", "December "], required=True),
            FieldSpec("Year * ", "year ", "entry ", str(datetime.now().year), required=True),
            FieldSpec("Base Salary * ", "base_salary ", "entry ", " ", required=True, numeric=True),
            FieldSpec("Bonus ", "bonus ", "entry ", "0 ", numeric=True),
            FieldSpec("Deductions ", "deductions ", "entry ", "0 ", numeric=True),
            FieldSpec("Net Salary ", "net_salary ", "entry ", " ", numeric=True),
            FieldSpec("Payment Method ", "payment_method ", "combo ", options=["Cash ", "Cheque ", "Bank Transfer ", "Online "]),
            FieldSpec("Notes ", "notes ", "entry "),
        ]
        dialog = RecordDialog("Pay Salary ", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        employee_name = str(vals["employee "]).split(" (Base: ")[0]
        employee = self.main.services.fetch_one("SELECT id FROM employees WHERE full_name=? ", (employee_name,))
        if not employee:
            QMessageBox.warning(self, "Employee ", "Employee not found. ")
            return
        base = safe_float(vals["base_salary "])
        bonus = safe_float(vals["bonus "])
        deductions = safe_float(vals["deductions "])
        net = safe_float(vals["net_salary "]) or (base + bonus - deductions)
        self.main.services.execute(
            """INSERT INTO salary_payments
               (employee_id, payment_date, month, year, base_salary, bonus, deductions,
                net_salary, payment_method, notes, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?) """,
            (employee["id"], datetime.now().strftime("%Y-%m-%d "), vals["month "], vals["year "], base, bonus, deductions, net, vals["payment_method "], vals["notes "], datetime.now())
        )
        self.refresh()

class EmployeesModule(QWidget):
    # FIX: Corrected __init__ and split variable name
    def __init__(self, main: "ModernCRMWindow ", employee_spec: TableSpec, salary_spec: TableSpec):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Employees ")
        heading.setObjectName("PageTitle ")
        layout.addWidget(heading)
        tabs = QTabWidget()
        self.employees = DataTablePage(main, employee_spec)
        self.attendance = AttendancePage(main)
        self.salary = SalaryPage(main, salary_spec)
        tabs.addTab(self.employees, "Employees ")
        tabs.addTab(self.attendance, "Attendance ")
        tabs.addTab(self.salary, "Salary History ")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.employees.refresh()
        self.attendance.refresh()
        self.salary.refresh()

class ReportsModule(QWidget):
    # FIX: Corrected __init__ and split variable name
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.last_report: ReportResult | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Reports")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        quick = QHBoxLayout()
        rent_btn = QPushButton("Rent Report ")
        sale_btn = QPushButton("Sale Report ")
        both_btn = QPushButton("Combined Report ")
        rent_btn.setObjectName("AccentButton ")
        rent_btn.clicked.connect(lambda: self.generate("rent "))
        sale_btn.clicked.connect(lambda: self.generate("sale "))
        both_btn.clicked.connect(lambda: self.generate("rent + sale "))
        quick.addWidget(rent_btn)
        quick.addWidget(sale_btn)
        quick.addWidget(both_btn)
        quick.addStretch(1)
        layout.addLayout(quick)
        controls = QHBoxLayout()
        self.report_type = QComboBox()
        self.report_type.addItems(["Rent ", "Sale ", "Rent + Sale ", "Financial ", "Properties ", "Clients ", "Employees ", "Attendance "])
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit(QDate.currentDate())
        for date_edit in (self.start_date, self.end_date):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd ")
        generate = QPushButton("Generate ")
        generate.setObjectName("AccentButton ")
        generate.clicked.connect(self.generate)
        export = QPushButton("Export ")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Report "))
        controls.addWidget(self.report_type)
        controls.addWidget(QLabel("From "))
        controls.addWidget(self.start_date)
        controls.addWidget(QLabel("To "))
        controls.addWidget(self.end_date)
        controls.addStretch(1)
        controls.addWidget(generate)
        controls.addWidget(export)
        layout.addLayout(controls)
        # FIX: Corrected split variable name
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas ", 9))
        layout.addWidget(self.preview, 1)

    def generate(self, report_type: str | None = None) -> None:
        kind = (report_type or self.report_type.currentText()).lower()
        start = self.start_date.date().toString("yyyy-MM-dd ")
        end = self.end_date.date().toString("yyyy-MM-dd ")
        svc = self.main.report_service
        if kind == "rent ":
            result = svc.rent_report(start, end)
        elif kind == "sale ":
            result = svc.sale_report(start, end)
        elif kind == "rent + sale ":
            result = svc.dealings_report(start, end)
        elif kind == "financial ":
            result = ReportResult("Financial Summary ", self.main.financial_text(), filename_slug="financial_summary ")
        elif kind == "properties ":
            result = ReportResult("Property Report ", self.main.generic_report("properties ", "PROPERTY REPORT "), filename_slug="property_report ")
        elif kind == "clients ":
            result = ReportResult("Client Report ", self.main.generic_report("clients ", "CLIENT REPORT "), filename_slug="client_report ")
        elif kind == "employees ":
            result = ReportResult("Employee Report ", self.main.generic_report("employees ", "EMPLOYEE REPORT "), filename_slug="employee_report ")
        else:
            result = ReportResult("Attendance Report ", self.main.attendance_report(), filename_slug="attendance_report ")
        self.last_report = result
        self.main.last_report = result
        self.preview.setPlainText(result.text)

    def export(self) -> None:
        if not self.last_report:
            QMessageBox.information(self, "Report ", "Generate a report first. ")
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, selected_filter = QFileDialog.getSaveFileName(self, "Export Report ", str(OUTPUT_DIR / f"{self.last_report.filename_slug}.pdf "), "PDF Files (*.pdf);;CSV Files (*.csv);;Text Files (*.txt) ")
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if suffix == ".csv " or "CSV " in selected_filter:
            export_report_csv(self.last_report, path)
        elif suffix == ".txt " or "Text " in selected_filter:
            export_report_text(self.last_report, path)
        else:
            export_report_pdf(self.last_report, path)
        QMessageBox.information(self, "Exported ", f"Saved to:\n{path} ")

class AIInsightsModule(QWidget):
    # FIX: Corrected __init__ and split variable name
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.last_text = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("AI Insights ")
        title.setObjectName("PageTitle ")
        layout.addWidget(title)
        controls = QHBoxLayout()
        self.status = QLabel(self._status_text())
        self.status.setObjectName("MutedText ")
        refresh = QPushButton("Refresh AI ")
        refresh.setObjectName("AccentButton ")
        refresh.clicked.connect(self.refresh)
        copy = QPushButton("Copy ")
        copy.clicked.connect(self.copy_report)
        export = QPushButton("Export TXT ")
        export.clicked.connect(self.export_report)
        controls.addWidget(self.status)
        controls.addStretch(1)
        controls.addWidget(refresh)
        controls.addWidget(copy)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas ", 9))
        layout.addWidget(self.preview, 1)
        self.refresh()

    def _status_text(self) -> str:
        if AI_LIBS_AVAILABLE:
            return "Local AI: pandas + numpy, NLP matching, regression, MLP-style lead scoring "
        return "AI libraries missing: install pandas and numpy "

    def refresh(self) -> None:
        self.main.reload_settings()
        self.last_text = self.main.intelligence_service.generate_report()
        self.preview.setPlainText(self.last_text)
        self.status.setText(self._status_text())

    def copy_report(self) -> None:
        if not self.last_text:
            self.refresh()
        QApplication.clipboard().setText(self.last_text)
        QMessageBox.information(self, "Copied ", "AI insights copied to clipboard. ")

    def export_report(self) -> None:
        if not self.last_text:
            self.refresh()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Export AI Insights ", str(OUTPUT_DIR / f"ai_insights_{datetime.now().strftime('%Y%m%d')}.txt "), "Text Files (*.txt) ")
        if not path:
            return
        Path(path).write_text(self.last_text, encoding="utf-8 ")
        QMessageBox.information(self, "Exported ", f"Saved to:\n{path} ")

class ReportPreviewDialog(QDialog):
    # FIX: Corrected __init__ and removed trailing spaces before parentheses
    def __init__(self, result: ReportResult, parent: QWidget | None = None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(result.title)
        self.resize(980, 680)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel(result.title)
        title.setObjectName("DialogTitle ")
        header.addWidget(title)
        header.addStretch(1)
        pdf = QPushButton("Export PDF ")
        csv_btn = QPushButton("Export CSV ")
        txt = QPushButton("Export TXT ")
        pdf.setObjectName("AccentButton ")
        pdf.clicked.connect(lambda: self.export("pdf "))
        csv_btn.clicked.connect(lambda: self.export("csv "))
        txt.clicked.connect(lambda: self.export("txt "))
        header.addWidget(pdf)
        header.addWidget(csv_btn)
        header.addWidget(txt)
        layout.addLayout(header)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas ", 9))
        self.preview.setPlainText(result.text)
        layout.addWidget(self.preview, 1)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def export(self, kind: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filters = {"pdf ": "PDF Files (*.pdf) ", "csv ": "CSV Files (*.csv) ", "txt ": "Text Files (*.txt) "}
        path, _ = QFileDialog.getSaveFileName(self, "Export Report ", str(OUTPUT_DIR / f"{self.result.filename_slug}.{kind} "), filters[kind])
        if not path:
            return
        if kind == "pdf ":
            export_report_pdf(self.result, path)
        elif kind == "csv ":
            export_report_csv(self.result, path)
        else:
            export_report_text(self.result, path)
        QMessageBox.information(self, "Exported ", f"Saved to:\n{path} ")

class UsersModule(QWidget):
    # FIX: Corrected __init__ and multiple split variable names
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        title = QLabel("User Management ")
        title.setObjectName("PageTitle ")
        layout.addWidget(title)
        controls = QHBoxLayout()
        add = QPushButton("Add User ")
        add.setObjectName("AccentButton ")
        add.clicked.connect(self.add_user)
        activate = QPushButton("Toggle Active ")
        activate.clicked.connect(self.toggle_active)
        refresh = QPushButton("Refresh ")
        refresh.clicked.connect(self.refresh)
        controls.addWidget(add)
        controls.addWidget(activate)
        controls.addStretch(1)
        controls.addWidget(refresh)
        layout.addLayout(controls)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected ")
        self.selection_label.setObjectName("SelectionCount ")
        select_all = QPushButton("Select All ")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection ")
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

    def refresh(self) -> None:
        self.rows = self.main.services.fetch_all("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id ")
        headers = ["ID ", "Username ", "Full Name ", "Email ", "Role ", "Active ", "Last Login "]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            values = [row["id "], row["username "], row["full_name "], row["email "], row["role "], "Yes " if row["is_active "] else "No ", row["last_login "] or " "]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value or " "))
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
        return rows[0] if rows else None

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected ")

    def add_user(self) -> None:
        fields = [
            FieldSpec("Username * ", "username ", required=True),
            FieldSpec("Password * ", "password ", required=True),
            FieldSpec("Full Name * ", "full_name ", required=True),
            FieldSpec("Email ", "email "),
            FieldSpec("Role ", "role ", "combo ", options=list(ROLE_PERMISSIONS)),
        ]
        dialog = RecordDialog("Add User ", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        ok, message = self.main.services.create_user(vals["username "], vals["password "], vals["full_name "], vals["email "], vals["role "])
        if not ok:
            QMessageBox.warning(self, "User ", message)
            return
        self.refresh()

    def toggle_active(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more users first. ")
            return
        if len(rows) > 1:
            ask = QMessageBox.question(self, "Toggle Users ", f"Toggle active status for {len(rows)} selected users? ")
            if ask != QMessageBox.Yes:
                return
        for row in rows:
            value = 0 if row["is_active "] else 1
            self.main.services.execute("UPDATE users SET is_active=? WHERE id=? ", (value, row["id"]))
        self.refresh()

class SettingsModule(QWidget):
    KEYS = [
        ("Company Name ", "company_name "), ("Company Address ", "company_address "),
        ("Company Phone ", "company_phone "), ("Company Email ", "company_email "),
        ("Currency Symbol ", "currency_symbol "), ("Default Commission % ", "default_commission "),
        ("Tax Rate % ", "tax_rate "), ("Bank Account ", "bank_account "),
    ]
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.inputs: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        title = QLabel("Settings ")
        title.setObjectName("PageTitle ")
        layout.addWidget(title)
        form_frame = QFrame()
        form_frame.setObjectName("Panel ")
        form = QFormLayout(form_frame)
        for label, key in self.KEYS:
            edit = QLineEdit(main.services.settings_get(key))
            self.inputs[key] = edit
            form.addRow(label, edit)
        layout.addWidget(form_frame)
        buttons = QHBoxLayout()
        save = QPushButton("Save Settings ")
        save.setObjectName("AccentButton ")
        save.clicked.connect(self.save)
        change = QPushButton("Change My Password ")
        change.clicked.connect(self.change_password)
        buttons.addWidget(save)
        buttons.addWidget(change)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        # FIX: Corrected split method name
        layout.addStretch(1)

    def save(self) -> None:
        for key, widget in self.inputs.items():
            self.main.services.settings_set(key, widget.text().strip())
        self.main.reload_settings()
        QMessageBox.information(self, "Settings ", "Settings saved. ")

    def change_password(self) -> None:
        fields = [
            FieldSpec("Current Password * ", "old_password ", required=True),
            FieldSpec("New Password * ", "new_password ", required=True),
        ]
        dialog = RecordDialog("Change Password ", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        # FIX: Corrected split variable name
        ok, message = self.main.services.change_password(self.main.current_user["id "], vals["old_password "], vals["new_password "])
        QMessageBox.information(self, "Password " if ok else "Password Error ", message)

class ApprovalsModule(QWidget):
    # FIX: Corrected __init__ and multiple split variable names
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        title = QLabel("Approval Center ")
        title.setObjectName("PageTitle ")
        layout.addWidget(title)
        controls = QHBoxLayout()
        approve = QPushButton("Approve ")
        approve.setObjectName("AccentButton ")
        approve.clicked.connect(lambda: self.set_status("Approved "))
        resend = QPushButton("Resend with Comment ")
        resend.clicked.connect(lambda: self.set_status("Resend "))
        refresh = QPushButton("Refresh ")
        refresh.clicked.connect(self.refresh)
        controls.addWidget(approve)
        controls.addWidget(resend)
        controls.addStretch(1)
        controls.addWidget(refresh)
        layout.addLayout(controls)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected ")
        self.selection_label.setObjectName("SelectionCount ")
        select_all = QPushButton("Select All ")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection ")
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

    def refresh(self) -> None:
        datasets = [
            ("Rent Req ", "rent_requirements ", "client_name "), ("Rent Av ", "rent_availability ", "owner_name "),
            ("Sale Req ", "sale_requirements ", "client_name "), ("Sale Av ", "sale_availability ", "owner_name "),
        ]
        rows: list[dict] = []
        for source, table, name_col in datasets:
            for row in self.main.services.fetch_all(
                f"""SELECT id, {name_col} AS name, location, approval_status, approval_comment
                    FROM {table}
                    WHERE approval_status='Pending' OR approval_status='Resend' 
                    ORDER BY id DESC """
            ):
                row["source "] = source
                row["table "] = table
                rows.append(row)
        self.rows = rows
        headers = ["Source ", "ID ", "Name ", "Location ", "Status ", "Comment "]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["source "], row["id "], row["name "], row["location "], row["approval_status "], row["approval_comment "]]
            for c, value in enumerate(values):
                text = str(value or " ")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setForeground(QColor("#0f172a "))
                if headers[c] == "Comment ":
                    item.setToolTip(text)
                    item.setText(text.replace("\r\n", "  ").replace("\n", "  "))
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
            self.table.setRowHeight(r, 42)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(5, 280)
        self.update_selection_label()

    def selected_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_indexes()]

    def selected(self) -> dict | None:
        rows = self.selected_rows()
        return rows[0] if rows else None

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected ")

    def set_status(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more records first. ")
            return
        comment = " "
        if status == "Resend ":
            dialog = CommentDialog("Resend ", "Comment for the user: ", self)
            if dialog.exec() != QDialog.Accepted:
                return
            comment = dialog.value()
            if not comment:
                QMessageBox.warning(self, "Comment ", "Comment is required for resend. ")
                return
        if len(rows) > 1:
            ask = QMessageBox.question(self, "Approval ", f"Set {len(rows)} selected record(s) to {status}? ")
            if ask != QMessageBox.Yes:
                return
        for row in rows:
            self.main.services.execute(
                f"""UPDATE {row['table']}
                    SET approval_status=?, approval_comment=?, approved_by=?, approved_at=?
                    WHERE id=? """,
                (status, comment, self.main.current_user["username "], datetime.now(), row["id"]),
            )
        self.refresh()
        self.main.refresh_all_pages()

class SearchDialog(QDialog):
    # FIX: Corrected __init__ and multiple split variable/method names
    def __init__(self, main: "ModernCRMWindow "):
        super().__init__(main)
        self.main = main
        self.rows: list[dict] = []
        self.display_columns: list[str] = []
        self.table_column_cache: dict[str, list[str]] = {}
        self.setWindowTitle("Global Search ")
        self.resize(1180, 640)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search all fields in rent/sale requirements and availability... ")
        button = QPushButton("Search ")
        button.setObjectName("AccentButton ")
        button.clicked.connect(self.search)
        bar.addWidget(self.query, 1)
        bar.addWidget(button)
        layout.addLayout(bar)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected ")
        self.selection_label.setObjectName("SelectionCount ")
        select_all = QPushButton("Select All ")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection ")
        clear.clicked.connect(self.clear_selection)
        copy = QPushButton("Copy Selected ")
        copy.clicked.connect(self.copy_selected_rows)
        print_voucher = QPushButton("Print Voucher ")
        print_voucher.setObjectName("AccentButton ")
        print_voucher.clicked.connect(self.print_voucher)
        save_pdf = QPushButton("Save Voucher PDF ")
        save_pdf.clicked.connect(self.save_voucher_pdf)
        selection.addWidget(self.selection_label)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        selection.addWidget(copy)
        selection.addWidget(print_voucher)
        selection.addWidget(save_pdf)
        layout.addLayout(selection)
        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        self.table.horizontalHeader().setStretchLastSection(False)
        # FIX: Corrected split method name
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.table, 1)
        self.query.returnPressed.connect(self.search)

    def search_sources(self) -> list[tuple[str, str]]:
        return list(GLOBAL_SEARCH_SOURCES)

    def table_columns(self, table: str) -> list[str]:
        if table not in self.table_column_cache:
            rows = self.main.services.fetch_all(f"PRAGMA table_info({table}) ")
            self.table_column_cache[table] = [row["name "] for row in rows if row.get("name ") not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
        return self.table_column_cache[table]

    def source_label(self, table: str) -> str:
        return GLOBAL_SEARCH_SOURCE_LABELS.get(table, table.replace("_", "  ").title())

    def field_label(self, key: str) -> str:
        if key == "_source ":
            return "Source "
        if key == "_table ":
            return "Table "
        return {"id ": "ID ", "sq_ft ": "Sq Ft ", "sq_ft_yards ": "Sq Ft / Yards ", "cnic ": "CNIC "}.get(key, key.replace("_", "  ").title())

    def display_value(self, key: str, value: Any) -> str:
        if value in (None, " "):
            return " "
        if key in GLOBAL_SEARCH_MONEY_COLUMNS and is_valid_number_text(value):
            return money(value, self.main.currency_symbol)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M ")
        return str(value)

    def ordered_display_columns(self, rows: list[dict]) -> list[str]:
        fields: set[str] = set()
        for row in rows:
            fields.update(row.get("_columns ", []))
        ordered = ["_source "]
        for key in GLOBAL_SEARCH_PRIORITY_COLUMNS:
            if key in fields and key not in ordered:
                ordered.append(key)
        for key in sorted(fields, key=lambda value: self.field_label(value).lower()):
            if key not in ordered:
                ordered.append(key)
        return ordered

    def search(self) -> None:
        term = self.query.text().strip().lower()
        if not term:
            return
        results: list[dict] = []
        for source, table in self.search_sources():
            columns = self.table_columns(table)
            if not columns:
                continue
            source_text = f"{source} {table.replace('_', ' ')} ".lower()
            if term in source_text:
                sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50 "
                params: tuple[Any, ...] = ()
            else:
                where = " OR ".join(f'LOWER(CAST(COALESCE("{col}", \'\') AS TEXT)) LIKE ? ' for col in columns)
                sql = f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 50 "
                params = tuple([f"%{term}% "] * len(columns))
            for row in self.main.services.fetch_all(sql, params):
                clean_row = {key: row.get(key) for key in columns}
                clean_row["_source "] = source
                clean_row["_table "] = table
                clean_row["_columns "] = columns
                results.append(clean_row)
        self.rows = results
        self.display_columns = self.ordered_display_columns(results)
        headers = [self.field_label(key) for key in self.display_columns]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(results))
        for r, row in enumerate(results):
            for c, key in enumerate(self.display_columns):
                # FIX: Corrected split variable name
                item = QTableWidgetItem(self.display_value(key, row.get(key)))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, min(max(self.table.columnWidth(col), 90), 230))
        self.update_selection_label()

    def selected_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_indexes()]

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected ")

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more search results first. ")
            return
        keys = self.display_columns or self.ordered_display_columns(rows)
        lines = ["\t".join(self.field_label(key) for key in keys)]
        for row in rows:
            lines.append("\t".join(self.display_value(key, row.get(key)) for key in keys))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied ", f"{len(rows)} selected result(s) copied to clipboard. ")

    def voucher_rows(self) -> list[dict]:
        rows = self.selected_rows()
        if rows:
            return rows
        if self.rows:
            return self.rows
        QMessageBox.information(self, "Search ", "Search first, then print or save the voucher. ")
        return []

    def voucher_html(self, rows: list[dict]) -> str:
        query = html.escape(self.query.text().strip() or "All visible results ")
        generated_at = datetime.now().strftime("%Y-%m-%d %I:%M %p ")
        user_name = html.escape(self.main.current_user.get("full_name ") or self.main.current_user.get("username ") or " ")
        company = html.escape(self.main.company_name)
        body_parts = [
            "<html><head><style>",
            """
            @page { size: legal landscape; margin: 7mm; }
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; color: #111827; margin: 0; font-size: 9.5pt; }
            .voucher { border: 2px solid #111827; padding: 12px; margin: 0 0 10px 0; page-break-inside: avoid; page-break-after: always; width: 100%; }
            .voucher:last-child { page-break-after: auto; }
            .top { display: table; width: 100%; border-bottom: 2px solid #111827; padding-bottom: 10px; margin-bottom: 14px; }
            .brand { display: table-cell; vertical-align: top; }
            .brand h1 { margin: 0; font-size: 18px; letter-spacing: 0; }
            .brand p { margin: 4px 0 0 0; color: #475569; font-size: 9pt; }
            .stamp { display: table-cell; text-align: right; vertical-align: top; font-size: 9pt; color: #475569; }
            .stamp strong { display: block; color: #2563eb; font-size: 13pt; margin-bottom: 4px; }
            .summary { width: 100%; border-collapse: collapse; margin-bottom: 10px; table-layout: fixed; }
            .summary td { border: 1px solid #cbd5e1; padding: 5px 7px; font-size: 9pt; overflow-wrap: anywhere; word-break: break-word; }
            .summary .label { width: 17%; background: #f1f5f9; font-weight: bold; color: #334155; }
            .fields { width: 100%; border-collapse: collapse; table-layout: fixed; }
            .fields th { background: #eaf2ff; color: #0f172a; border: 1px solid #bfdbfe; padding: 5px; text-align: left; font-size: 9pt; }
            .fields td { border: 1px solid #dbe3ef; padding: 5px; vertical-align: top; font-size: 8.7pt; overflow-wrap: anywhere; word-break: break-word; }
            .field-name { width: 18%; font-weight: bold; background: #f8fafc; color: #334155; }
            .footer { margin-top: 10px; font-size: 8pt; color: #64748b; text-align: center; }
            """,
            "</style></head><body>",
        ]
        for index, row in enumerate(rows, start=1):
            source = html.escape(str(row.get("_source ") or self.source_label(str(row.get("_table ") or " "))))
            record_id = html.escape(str(row.get("id ") or " "))
            status = html.escape(str(row.get("approval_status ") or row.get("status ") or row.get("workflow_stage ") or " "))
            body_parts.append("<div class='voucher'>")
            body_parts.append(f"<div class='top'><div class='brand'><h1>{company}</h1><p>Global Search Voucher</p></div><div class='stamp'><strong>{source}</strong>Voucher #{index:03d}<br>{generated_at}</div></div>")
            body_parts.append("<table class='summary'>")
            body_parts.append(f"<tr><td class='label'>Search</td><td>{query}</td><td class='label'>Record ID</td><td>{record_id}</td></tr><tr><td class='label'>Printed By</td><td>{user_name}</td><td class='label'>Status</td><td>{status or '-'}</td></tr>")
            body_parts.append("</table>")
            body_parts.append("<table class='fields'><tr><th>Field</th><th>Value</th><th>Field</th><th>Value</th></tr>")
            columns = [col for col in row.get("_columns ", []) if col not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
            if "_source " not in columns:
                columns = ["_source "] + columns
            cells: list[tuple[str, str]] = []
            for key in columns:
                value = row.get(key)
                display = self.display_value(key, value) or "-"
                cells.append((self.field_label(key), display))
            for offset in range(0, len(cells), 2):
                left = cells[offset]
                right = cells[offset + 1] if offset + 1 < len(cells) else (" ", " ")
                body_parts.append(f"<tr><td class='field-name'>{html.escape(left[0])}</td><td>{html.escape(left[1])}</td><td class='field-name'>{html.escape(right[0])}</td><td>{html.escape(right[1])}</td></tr>")
            body_parts.append("</table>")
            body_parts.append("<div class='footer'>Generated from Real Estate CRM global search. Verify record before deal finalization.</div>")
            body_parts.append("</div>")
        body_parts.append("</body></html>")
        return " ".join(body_parts)

    def print_voucher(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Search Voucher ")
        if dialog.exec() == QDialog.Accepted:
            doc.print_(printer)

    def save_voucher_pdf(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        default_name = f"global_search_voucher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf "
        path, _ = QFileDialog.getSaveFileName(self, "Save Search Voucher PDF ", str(OUTPUT_DIR / default_name), "PDF Files (*.pdf) ")
        if not path:
            return
        if not path.lower().endswith(".pdf "):
            path += ".pdf "
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc.print_(printer)
        QMessageBox.information(self, "Saved ", f"Voucher PDF saved:\n{path} ")

class ModernCRMWindow(QMainWindow):
    # FIX: Corrected __init__ and multiple split variable/method names
    def __init__(self, services: CRMServices, current_user: dict):
        super().__init__()
        self.services = services
        self.current_user = current_user
        self.role = current_user.get("role", "Staff")
        self.pages: dict[str, QWidget] = {}
        self.last_report: ReportResult | None = None
        self._api_server: ThreadingHTTPServer | None = None
        self.local_ip = self.get_local_ip()
        self.local_service_url = f"http://{self.local_ip}:{LOCAL_SERVICE_PORT}"
        self.reload_settings()
        self.setWindowTitle(f"Real Estate CRM - {current_user.get('full_name') or current_user.get('username')} ({self.role})")
        self.setWindowIcon(crm_app_icon())
        self.resize(1360, 840)
        self.setMinimumSize(1000, 660)
        self._build_specs()
        self._build_ui()
        self.start_local_service()
        self.refresh_all_pages()

    def reload_settings(self) -> None:
        self.company_name = self.services.settings_get("company_name ", "Real Estate Management ")
        self.currency_symbol = self.services.settings_get("currency_symbol ", "Rs. ")
        self.report_service = ReportService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)

    def _build_specs(self) -> None:
        m = lambda value, symbol: money(value, symbol)
        pct = lambda value, _symbol: f"{safe_float(value):.0f}% "
        self.specs = {
            "rent_req ": TableSpec("Rent Requirements ", "rent_requirements ", [
                ColumnSpec("id ", "ID ", width=64), ColumnSpec("date ", "Date ", width=96),
                ColumnSpec("client_name ", "Name ", width=150), ColumnSpec("contact ", "Contact ", width=120),
                ColumnSpec("property_requires ", "Property Requires ", width=150),
                ColumnSpec("size ", "Size ", width=110), ColumnSpec("measurement ", "Measurement ", width=120),
                ColumnSpec("budget ", "Budget ", m, 115), ColumnSpec("floor ", "Floor ", width=90),
                ColumnSpec("location ", "Location ", width=150), ColumnSpec("facilities ", "Facilities ", width=220),
                ColumnSpec("remarks ", "Remarks ", width=240), ColumnSpec("workflow_stage ", "Stage ", width=120),
                ColumnSpec("priority ", "Priority ", width=90), ColumnSpec("assigned_to ", "Assigned ", width=110),
                ColumnSpec("deal_probability ", "Probability ", pct, 100),
                ColumnSpec("approval_status ", "Approval ", width=100), ColumnSpec("approval_comment ", "Admin Comment ", width=240),
            ], deal_fields("client_name ", "property_requires ", "budget "), deal_insert_columns("client_name ", "property_requires ", "budget "), deal_update_columns("client_name ", "property_requires ", "budget "), deal_table=True),
            "rent_av ": TableSpec("Rent Availability ", "rent_availability ", [
                ColumnSpec("id ", "ID ", width=64), ColumnSpec("date ", "Date ", width=96),
                ColumnSpec("owner_name ", "Owner ", width=150), ColumnSpec("contact ", "Contact ", width=120),
                ColumnSpec("property_availability ", "Property Availability ", width=160),
                ColumnSpec("size ", "Size ", width=110), ColumnSpec("measurement ", "Measurement ", width=120),
                ColumnSpec("monthly_rent ", "Rent ", m, 115), ColumnSpec("deposit ", "Deposit ", m, 115),
                ColumnSpec("maintenance_charge ", "Maintenance ", m, 120), ColumnSpec("floor ", "Floor ", width=90),
                ColumnSpec("location ", "Location ", width=150), ColumnSpec("facilities ", "Facilities ", width=220),
                ColumnSpec("remarks ", "Remarks ", width=240), ColumnSpec("workflow_stage ", "Stage ", width=120),
                ColumnSpec("priority ", "Priority ", width=90), ColumnSpec("assigned_to ", "Assigned ", width=110),
                ColumnSpec("deal_probability ", "Probability ", pct, 100),
                ColumnSpec("approval_status ", "Approval ", width=100), ColumnSpec("approval_comment ", "Admin Comment ", width=240),
            ], availability_fields("owner_name ", "property_availability ", "monthly_rent "), availability_insert_columns("owner_name ", "property_availability ", "monthly_rent ") + ["deposit ", "maintenance_charge "], availability_update_columns("owner_name ", "property_availability ", "monthly_rent ") + ["deposit ", "maintenance_charge "], deal_table=True),
            "sale_req ": TableSpec("Sale Requirements ", "sale_requirements ", [
                ColumnSpec("id ", "ID ", width=64), ColumnSpec("date ", "Date ", width=96),
                ColumnSpec("client_name ", "Name ", width=150), ColumnSpec("contact ", "Contact ", width=120),
                ColumnSpec("property_requires ", "Property Requires ", width=150),
                ColumnSpec("size ", "Size ", width=110), ColumnSpec("measurement ", "Measurement ", width=120),
                ColumnSpec("budget ", "Budget ", m, 115), ColumnSpec("floor ", "Floor ", width=90),
                ColumnSpec("location ", "Location ", width=150), ColumnSpec("facilities ", "Facilities ", width=220),
                ColumnSpec("remarks ", "Remarks ", width=240), ColumnSpec("workflow_stage ", "Stage ", width=120),
                ColumnSpec("priority ", "Priority ", width=90), ColumnSpec("assigned_to ", "Assigned ", width=110),
                ColumnSpec("deal_probability ", "Probability ", pct, 100),
                ColumnSpec("approval_status ", "Approval ", width=100), ColumnSpec("approval_comment ", "Admin Comment ", width=240),
            ], deal_fields("client_name ", "property_requires ", "budget "), deal_insert_columns("client_name ", "property_requires ", "budget "), deal_update_columns("client_name ", "property_requires ", "budget "), deal_table=True),
            "sale_av ": TableSpec("Sale Availability ", "sale_availability ", [
                ColumnSpec("id ", "ID ", width=64), ColumnSpec("date ", "Date ", width=96),
                ColumnSpec("owner_name ", "Owner ", width=150), ColumnSpec("contact ", "Contact ", width=120),
                ColumnSpec("property_availability ", "Property Availability ", width=160),
                ColumnSpec("size ", "Size ", width=110), ColumnSpec("measurement ", "Measurement ", width=120),
                ColumnSpec("demand ", "Demand ", m, 120), ColumnSpec("floor ", "Floor ", width=90),
                ColumnSpec("location ", "Location ", width=150), ColumnSpec("facilities ", "Facilities ", width=220),
                ColumnSpec("remarks ", "Remarks ", width=240), ColumnSpec("workflow_stage ", "Stage ", width=120),
                ColumnSpec("priority ", "Priority ", width=90), ColumnSpec("assigned_to ", "Assigned ", width=110),
                ColumnSpec("deal_probability ", "Probability ", pct, 100),
                ColumnSpec("approval_status ", "Approval ", width=100), ColumnSpec("approval_comment ", "Admin Comment ", width=240),
            ], availability_fields("owner_name ", "property_availability ", "demand "), availability_insert_columns("owner_name ", "property_availability ", "demand "), availability_update_columns("owner_name ", "property_availability ", "demand "), deal_table=True),
            "properties ": property_spec(), "clients ": client_spec(), "income ": income_spec(), "expenses ": expense_spec(),
            "employees ": employee_spec(), "salary ": salary_spec(),
        }

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar ")
        sidebar.setFixedWidth(286)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 18, 18, 18)
        side.setSpacing(14)
        brand_card = QFrame()
        brand_card.setObjectName("BrandCard ")
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(12, 12, 12, 12)
        brand_layout.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("LogoImage ")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(58, 58)
        logo_pixmap = QPixmap(str(crm_logo_path()))
        if logo_pixmap.isNull():
            logo.setObjectName("LogoBadge ")
            logo.setText("RE ")
        else:
            logo.setPixmap(logo_pixmap.scaled(58, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_layout.addWidget(logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand = QLabel("Real Estate CRM ")
        brand.setObjectName("Brand ")
        brand_subtitle = QLabel("Property operations ")
        brand_subtitle.setObjectName("SidebarSubtle ")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_subtitle)
        brand_layout.addLayout(brand_text, 1)
        side.addWidget(brand_card)
        user_card = QFrame()
        user_card.setObjectName("UserCard ")
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(14, 12, 14, 12)
        user_layout.setSpacing(4)
        user_name = QLabel(str(self.current_user.get("full_name ") or self.current_user.get("username ") or "User "))
        user_name.setObjectName("SidebarUserName ")
        user_role = QLabel(str(self.role))
        user_role.setObjectName("RolePill ")
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_role, alignment=Qt.AlignLeft)
        side.addWidget(user_card)
        nav_shell = QFrame()
        # FIX: Corrected split method name
        nav_shell.setObjectName("NavShell ")
        nav_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.nav_shell = nav_shell
        self.nav_layout = QVBoxLayout(nav_shell)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        self.nav_buttons: dict[str, NavItem] = {}
        self.nav_keys: list[str] = []
        self._nav_section_count = 0
        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("SidebarNavScroll ")
        self.nav_scroll = nav_scroll
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # FIX: Corrected split enum value
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        nav_scroll.setWidget(nav_shell)
        side.addWidget(nav_scroll, 1)
        footer = QFrame()
        footer.setObjectName("SidebarFooter ")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 12, 12, 12)
        footer_layout.setSpacing(8)
        status_row = QHBoxLayout()
        dot = QLabel(" ")
        dot.setObjectName("StatusDot ")
        status_row.addWidget(dot)
        api_status = QLabel("Local API online ")
        api_status.setObjectName("SidebarStatusText ")
        status_row.addWidget(api_status)
        status_row.addStretch(1)
        footer_layout.addLayout(status_row)
        api_label = QLabel(self.local_service_url)
        api_label.setObjectName("SidebarSubtle ")
        api_label.setWordWrap(True)
        footer_layout.addWidget(api_label)
        logout = QPushButton("Logout ")
        logout.setObjectName("SidebarLogout ")
        logout.clicked.connect(self.logout)
        footer_layout.addWidget(logout)
        side.addWidget(footer)
        outer.addWidget(sidebar)
        content = QFrame()
        content.setObjectName("Content ")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(14)
        top = QHBoxLayout()
        self.page_title = QLabel(self.company_name)
        self.page_title.setObjectName("TopTitle ")
        search = QPushButton("Global Search ")
        search.clicked.connect(self.open_search)
        refresh = QPushButton("Refresh ")
        refresh.clicked.connect(self.refresh_all_pages)
        top.addWidget(self.page_title)
        top.addStretch(1)
        top.addWidget(search)
        top.addWidget(refresh)
        content_layout.addLayout(top)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        outer.addWidget(content, 1)
        self._build_pages()
        self._build_menu()
        self.setStyleSheet(APP_STYLE)

    def _build_menu(self) -> None:
        def action(label: str, slot: Callable) -> QAction:
            act = QAction(label, self)
            act.triggered.connect(slot)
            return act
        file_menu = self.menuBar().addMenu("File ")
        file_menu.addAction(action("Export All Tables ", self.export_all_tables))
        file_menu.addAction(action("Backup Database ", self.backup_database))
        file_menu.addSeparator()
        file_menu.addAction(action("Restart ", self.restart_app))
        file_menu.addAction(action("Logout ", self.logout))
        file_menu.addAction(action("Exit ", self.close))
        view_menu = self.menuBar().addMenu("View ")
        view_menu.addAction(action("Full Screen ", self.showFullScreen))
        view_menu.addAction(action("Exit Full Screen ", self.showNormal))
        tools_menu = self.menuBar().addMenu("Tools ")
        tools_menu.addAction(action("Global Search ", self.open_search))
        tools_menu.addAction(action("Refresh ", self.refresh_all_pages))
        tools_menu.addAction(action("API Health ", self.show_api_health))
        help_menu = self.menuBar().addMenu("Help ")
        help_menu.addAction(action("User Guide ", self.show_user_guide))
        help_menu.addAction(action("Roles & Permissions ", self.show_roles_info))
        help_menu.addAction(action("Developer Info ", self.show_developer_info))
        help_menu.addAction(action("About ", self.show_about))

    def get_local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8 ", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1 "

    def is_staff_restricted(self) -> bool:
        username = str(self.current_user.get("username ", " ")).strip().lower()
        role = str(self.role or " ").strip().lower()
        return role == "staff " or username in {"staff ", "staf "}

    def api_allowed_tables(self) -> set[str]:
        staff_tables = set(DEAL_TABLES)
        all_tables = {"rent_requirements ", "rent_availability ", "sale_requirements ", "sale_availability ",
                      "income_transactions ", "expense_transactions ", "clients ", "properties ", "employees "}
        return staff_tables if self.is_staff_restricted() else all_tables

    def start_local_service(self) -> None:
        app = self
        class CRMApiHandler(BaseHTTPRequestHandler):
            _rate_limit: dict[str, tuple[datetime, int]] = {}
            def log_message(self, _format: str, *args: Any) -> None:
                return
            def _send(self, payload: dict, status: int = 200) -> None:
                body = json.dumps(payload, default=str).encode("utf-8 ")
                self.send_response(status)
                self.send_header("Content-Type ", "application/json; charset=utf-8 ")
                self.send_header("Access-Control-Allow-Origin ", "* ")
                self.send_header("Access-Control-Allow-Methods ", "GET, POST, PUT, DELETE, OPTIONS ")
                self.send_header("Access-Control-Allow-Headers ", "Content-Type, Authorization, X-API-Key ")
                self.send_header("Content-Length ", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def _check_rate_limit(self) -> bool:
                client = self.client_address[0]
                now = datetime.now()
                stale = [ip for ip, (ts, _count) in self._rate_limit.items() if (now - ts).total_seconds() > 60]
                for ip in stale:
                    del self._rate_limit[ip]
                if client in self._rate_limit:
                    last, count = self._rate_limit[client]
                    if (now - last).total_seconds() < 1:
                        count += 1
                        if count > 30:
                            return False
                    else:
                        count = 1
                    self._rate_limit[client] = (now, count)
                else:
                    self._rate_limit[client] = (now, 1)
                return True
            def _table_columns(self, table: str) -> set[str]:
                return app.services.repo.table_columns(table)
            def _clean_payload(self, table: str, data: dict, *, add_create_meta: bool = False) -> tuple[dict, list[str]]:
                columns = self._table_columns(table)
                cleaned = {key: value for key, value in data.items() if key in columns and key != "id "}
                unknown = sorted(key for key in data if key not in columns or key == "id ")
                if add_create_meta:
                    if "created_by " in columns and "created_by " not in cleaned:
                        cleaned["created_by "] = app.current_user.get("username ", "api ")
                    if "created_at " in columns and "created_at " not in cleaned:
                        cleaned["created_at "] = str(datetime.now())
                return cleaned, unknown
            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin ", "* ")
                self.send_header("Access-Control-Allow-Methods ", "GET, POST, PUT, DELETE, OPTIONS ")
                self.send_header("Access-Control-Allow-Headers ", "Content-Type, Authorization, X-API-Key ")
                self.end_headers()
            def do_GET(self) -> None:
                if not self._check_rate_limit():
                    self._send({"ok ": False, "error ": "rate limit exceeded "}, 429)
                    return
                from urllib.parse import parse_qs
                path, _, query = self.path.partition("? ")
                params = {key: values[-1] for key, values in parse_qs(query).items()}
                if path in ("/ ", "/index "):
                    self._send({"ok ": True, "service ": "realestate-crm-api ", "version ": "qt-1.0 ", "message ": "Qt CRM API is running ", "routes ": ["/health ", "/meta ", "/users ", "/stats ", "/pipeline ", "/search?q=term ", "/records/<table> "]})
                    return
                if path in ("/health ", "/healthz "):
                    self._send({"ok ": True, "service ": "realestate-crm-api ", "port ": LOCAL_SERVICE_PORT})
                    return
                if path == "/meta ":
                    self._send({"ok ": True, "company ": app.company_name, "user ": app.current_user.get("full_name "), "role ": app.role, "url ": app.local_service_url, "db_size ": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0})
                    return
                if path == "/users ":
                    if not has_permission(app.role, "users "):
                        self._send({"ok ": False, "error ": "access denied "}, 403)
                        return
                    rows = app.services.fetch_all("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id ")
                    self._send({"ok ": True, "users ": rows})
                    return
                if path == "/stats ":
                    stats = {}
                    for table in sorted(app.api_allowed_tables()):
                        row = app.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} ")
                        stats[table] = row["count "] if row else 0
                    self._send({"ok ": True, "stats ": stats})
                    return
                if path == "/pipeline ":
                    stage = params.get("stage ") or None
                    if stage and stage not in DEAL_STAGES:
                        self._send({"ok ": False, "error ": f"invalid stage. allowed: {DEAL_STAGES} "}, 400)
                        return
                    rows = app.pipeline_rows(stage)
                    self._send({"ok ": True, "stage ": stage or "All ", "count ": len(rows), "totals ": app.pipeline_counts(), "rows ": rows})
                    return
                if path.startswith("/records/ "):
                    table = path.replace("/records/ ", "", 1).strip().lower()
                    if table not in app.api_allowed_tables():
                        self._send({"ok ": False, "error ": f"invalid table. allowed: {sorted(app.api_allowed_tables())} "}, 400)
                        return
                    try:
                        limit = min(int(params.get("limit ", 500)), 2000)
                        offset = int(params.get("offset ", 0))
                    except ValueError:
                        self._send({"ok ": False, "error ": "limit and offset must be integers "}, 400)
                        return
                    total_row = app.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} ")
                    rows = app.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ? ", (limit, offset))
                    self._send({"ok ": True, "table ": table, "count ": len(rows), "total ": total_row["count "] if total_row else 0, "rows ": rows})
                    return
                if path == "/search ":
                    q = params.get("q ", " ").strip().lower()
                    if not q:
                        self._send({"ok ": False, "error ": "query param 'q' is required "}, 400)
                        return
                    results = []
                    pattern = f"%{q}% "
                    for table in DEAL_TABLES:
                        source = GLOBAL_SEARCH_SOURCE_LABELS.get(table, table.replace("_", "  ").title())
                        columns = [column for column in sorted(app.services.repo.table_columns(table)) if column not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
                        if not columns:
                            continue
                        source_text = f"{source} {table.replace('_', ' ')} ".lower()
                        if q in source_text:
                            rows = app.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 20 ")
                        else:
                            where = " OR ".join(f'LOWER(CAST(COALESCE("{col}", \'\') AS TEXT)) LIKE ? ' for col in columns)
                            rows = app.services.fetch_all(f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 20 ", tuple([pattern] * len(columns)))
                        for row in rows:
                            fields = {column: row.get(column) for column in columns}
                            # FIX: Corrected split variable name
                            label = (fields.get("client_name ") or fields.get("owner_name ") or fields.get("full_name ") or fields.get("title ") or fields.get("property_code ") or fields.get("id "))
                            detail = (fields.get("contact ") or fields.get("contact_phone ") or fields.get("phone ") or fields.get("owner_contact ") or fields.get("email ") or fields.get("location ") or " ")
                            results.append({"table ": table, "source ": source, "id ": row.get("id "), "label ": str(label or " "), "detail ": str(detail or " "), "fields ": fields})
                    self._send({"ok ": True, "query ": q, "count ": len(results), "results ": results})
                    return
                self._send({"ok ": False, "error ": "not found "}, 404)
            def do_POST(self) -> None:
                self._write_record("POST ")
            def do_PUT(self) -> None:
                self._write_record("PUT ")
            def _write_record(self, method: str) -> None:
                if not self._check_rate_limit():
                    self._send({"ok ": False, "error ": "rate limit exceeded "}, 429)
                    return
                path = self.path.split("?", 1)[0]
                parts = path.strip("/").split("/")
                if method == "POST ":
                    if len(parts) != 2 or parts[0] != "records ":
                        self._send({"ok ": False, "error ": "POST requires /records/<table> "}, 400)
                        return
                    table = parts[1].lower()
                    row_id = None
                else:
                    if len(parts) != 3 or parts[0] != "records ":
                        self._send({"ok ": False, "error ": "PUT requires /records/<table>/<id> "}, 400)
                        return
                    table = parts[1].lower()
                    try:
                        row_id = int(parts[2])
                    except ValueError:
                        self._send({"ok ": False, "error ": "invalid id "}, 400)
                        return
                if table not in app.api_allowed_tables():
                    self._send({"ok ": False, "error ": "invalid table "}, 400)
                    return
                try:
                    length = int(self.headers.get("Content-Length ", 0))
                    body = self.rfile.read(length).decode("utf-8 ") if length else "{} "
                    data = json.loads(body)
                except Exception:
                    self._send({"ok ": False, "error ": "invalid JSON body "}, 400)
                    return
                if not isinstance(data, dict) or not data:
                    self._send({"ok ": False, "error ": "empty body "}, 400)
                    return
                cleaned, unknown = self._clean_payload(table, data, add_create_meta=(method == "POST "))
                if unknown:
                    self._send({"ok ": False, "error ": f"unknown fields: {unknown} "}, 400)
                    return
                if not cleaned:
                    self._send({"ok ": False, "error ": "no valid fields to save "}, 400)
                    return
                try:
                    if method == "POST ":
                        cols = ", ".join(cleaned)
                        placeholders = ", ".join("?" for _ in cleaned)
                        new_id = app.services.insert(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ", tuple(cleaned.values()))
                        self._send({"ok ": True, "table ": table, "id ": new_id, "message ": "record created "}, 201)
                    else:
                        set_clause = ", ".join(f"{key}=? " for key in cleaned)
                        app.services.execute(f"UPDATE {table} SET {set_clause} WHERE id=? ", tuple(cleaned.values()) + (row_id,))
                        self._send({"ok ": True, "table ": table, "id ": row_id, "message ": "record updated "})
                except Exception as exc:
                    self._send({"ok ": False, "error ": str(exc)}, 500)
            def do_DELETE(self) -> None:
                if not self._check_rate_limit():
                    self._send({"ok ": False, "error ": "rate limit exceeded "}, 429)
                    return
                parts = self.path.split("?", 1)[0].strip("/").split("/")
                if len(parts) != 3 or parts[0] != "records ":
                    self._send({"ok ": False, "error ": "DELETE requires /records/<table>/<id> "}, 400)
                    return
                table = parts[1].lower()
                if table not in app.api_allowed_tables():
                    self._send({"ok ": False, "error ": "invalid table "}, 400)
                    return
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok ": False, "error ": "invalid id "}, 400)
                    return
                try:
                    app.services.execute(f"DELETE FROM {table} WHERE id=? ", (row_id,))
                    self._send({"ok ": True, "table ": table, "id ": row_id, "message ": "record deleted "})
                except Exception as exc:
                    self._send({"ok ": False, "error ": str(exc)}, 500)
        def serve() -> None:
            try:
                self._api_server = ThreadingHTTPServer(("0.0.0.0 ", LOCAL_SERVICE_PORT), CRMApiHandler)
                self._api_server.serve_forever()
            except Exception as exc:
                print(f"Local API Error: {exc} ")
        threading.Thread(target=serve, daemon=True).start()

    def stop_local_service(self) -> None:
        try:
            if self._api_server:
                self._api_server.shutdown()
                self._api_server.server_close()
        except Exception:
            pass
        self._api_server = None

    def _nav_abbreviation(self, key: str, label: str) -> str:
        return {"dashboard ": "DB ", "rent ": "RN ", "sale ": "SL ", "properties ": "PR ", "clients ": "CL ",
                "financials ": "FI ", "employees ": "EM ", "reports ": "RP ", "ai ": "AI ",
                "approvals ": "AP ", "users ": "US ", "settings ": "ST "}.get(key, label[:2].upper())

    def _add_page(self, key: str, label: str, widget: QWidget) -> None:
        self.pages[key] = widget
        self.stack.addWidget(widget)
        button = NavItem(key, label, self._nav_abbreviation(key, label))
        button.clicked.connect(self.switch_page)
        self.nav_buttons[key] = button
        self.nav_keys.append(key)
        self.nav_layout.addWidget(button)

    def _add_nav_section(self, label: str) -> None:
        if self._nav_section_count:
            separator = QFrame()
            separator.setObjectName("NavSeparator ")
            separator.setFixedHeight(1)
            self.nav_layout.addWidget(separator)
        section = QLabel(label.upper())
        section.setObjectName("NavSection ")
        section.setFixedHeight(24)
        section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.nav_layout.addWidget(section)
        self._nav_section_count += 1

    def _build_pages(self) -> None:
        if not self.is_staff_restricted():
            self._add_nav_section("Overview ")
            self._add_page("dashboard ", "Dashboard ", self._dashboard_page())
        self._add_nav_section("Deal desk ")
        self._add_page("rent ", "Rent Dealings ", DealModule(self, "Rent Dealings ", self.specs["rent_req "], self.specs["rent_av "]))
        self._add_page("sale ", "Sale Dealings ", DealModule(self, "Sale Dealings ", self.specs["sale_req "], self.specs["sale_av "]))
        self._add_nav_section("Records ")
        self._add_page("properties ", "Properties ", DataTablePage(self, self.specs["properties "]))
        self._add_page("clients ", "Clients ", DataTablePage(self, self.specs["clients "]))
        if has_permission(self.role, "financial ") or has_permission(self.role, "financial_view "):
            self._add_page("financials ", "Financials ", FinancialModule(self, self.specs["income "], self.specs["expenses "]))
        if has_permission(self.role, "employees ") or has_permission(self.role, "employees_view "):
            self._add_page("employees ", "Employees ", EmployeesModule(self, self.specs["employees "], self.specs["salary "]))
        if has_permission(self.role, "reports "):
            self._add_page("reports ", "Reports ", ReportsModule(self))
        if has_permission(self.role, "ai "):
            self._add_nav_section("Intelligence ")
            self._add_page("ai ", "AI Insights ", AIInsightsModule(self))
        if self.role in ("Super Admin ", "Admin "):
            self._add_nav_section("Admin ")
            self._add_page("approvals ", "Approvals ", ApprovalsModule(self))
            self._add_page("users ", "Users ", UsersModule(self))
        if has_permission(self.role, "settings "):
            self._add_page("settings ", "Settings ", SettingsModule(self))
        self.nav_layout.addStretch(1)
        self.nav_shell.setMinimumHeight(self.nav_layout.sizeHint().height())
        if self.nav_keys:
            # FIX: Corrected split variable name
            self.switch_page(self.nav_keys[0])

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Dashboard ")
        title.setObjectName("PageTitle ")
        layout.addWidget(title)
        self.dashboard_grid = QGridLayout()
        self.dashboard_grid.setSpacing(14)
        layout.addLayout(self.dashboard_grid)
        # FIX: Corrected split class name
        self.pipeline_text = QTextEdit()
        self.pipeline_text.setReadOnly(True)
        self.pipeline_text.setFont(QFont("Consolas ", 9))
        layout.addWidget(self.pipeline_text, 1)
        return page

    def _nav_changed(self, row: int) -> None:
        if row >= 0:
            self.stack.setCurrentIndex(row)

    def switch_page(self, key: str) -> None:
        widget = self.pages.get(key)
        if not widget:
            return
        self.stack.setCurrentWidget(widget)
        for nav_key, button in self.nav_buttons.items():
            # FIX: Corrected split variable name
            button.setChecked(nav_key == key)

    def can_edit(self, permission: str) -> bool:
        if permission == "rent ":
            return has_permission(self.role, "rent ")
        return has_permission(self.role, permission)

    def refresh_all_pages(self) -> None:
        if "dashboard " in self.pages:
            self.refresh_dashboard()
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        errors: list[str] = []
        for widget in self.pages.values():
            if hasattr(widget, "refresh "):
                try:
                    widget.refresh()
                except Exception as exc:
                    errors.append(f"{widget.__class__.__name__}: {exc} ")
        if errors:
            QMessageBox.warning(self, "Refresh Issues ", "Some CRM pages could not refresh:\n\n " + "\n".join(errors[:6]))

    def refresh_dashboard(self) -> None:
        if "dashboard " not in self.pages or not hasattr(self, "dashboard_grid "):
            return
        while self.dashboard_grid.count():
            item = self.dashboard_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        metrics = [
            ("Rent Requirements ", self.count("rent_requirements "), "Client demand "),
            ("Rent Availability ", self.count("rent_availability "), "Listed for rent "),
            ("Sale Requirements ", self.count("sale_requirements "), "Buyer demand "),
            ("Sale Availability ", self.count("sale_availability "), "Listed for sale "),
            ("Clients ", self.count("clients "), "Contact records "),
            ("Employees ", self.count("employees "), "Team records "),
            ("Income ", money(self.sum_value("income_transactions ", "amount "), self.currency_symbol), "Total income "),
            ("Expenses ", money(self.sum_value("expense_transactions ", "amount "), self.currency_symbol), "Total expenses "),
        ]
        for idx, (title, value, note) in enumerate(metrics):
            self.dashboard_grid.addWidget(MetricCard(title, str(value), note), idx // 4, idx % 4)
        lines = ["PIPELINE ", "-" * 78]
        for row in self.pipeline_rows():
            lines.append(f"{row['source']: <9} #{row['id']: <4} {row['stage']: <16} {row['priority']: <7}  "
                         f"{row['name'][:22]: <22} {row['location'][:18]: <18} {money(row['amount'], self.currency_symbol): >12} ")
        self.pipeline_text.setPlainText("\n".join(lines))

    def count(self, table: str) -> int:
        row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} ")
        return int(row["count"]) if row else 0

    def sum_value(self, table: str, column: str) -> float:
        row = self.services.fetch_one(f"SELECT SUM({column}) AS total FROM {table} ")
        return safe_float(row["total"]) if row else 0

    def workflow_dialog(self, page: DataTablePage, table: str) -> None:
        row = page.require_single_row("workflow editing ")
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=? ", (row["id"],))
        fields = [
            FieldSpec("Workflow Stage ", "workflow_stage ", "combo ", options=DEAL_STAGES),
            FieldSpec("Priority ", "priority ", "combo ", options=DEAL_PRIORITIES),
            FieldSpec("Next Follow-up ", "next_follow_up "),
            FieldSpec("Assigned To ", "assigned_to ", "entry ", self.current_user.get("username ", " ")),
            FieldSpec("Probability % ", "deal_probability ", "entry ", numeric=True),
            FieldSpec("Expected Value ", "expected_close_value ", "entry ", numeric=True),
        ]
        dialog = RecordDialog("Deal Workflow ", fields, full, self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        stage = vals["workflow_stage "] or "Lead "
        closed_at = datetime.now() if stage == "Deal Done " else full.get("closed_at ")
        self.services.execute(f"""UPDATE {table}
            SET workflow_stage=?, priority=?, next_follow_up=?, assigned_to=?,
                deal_probability=?, expected_close_value=?, closed_at=?
            WHERE id=? """, (stage, vals["priority "] or "Medium ", vals["next_follow_up "], vals["assigned_to "],
                             safe_float(vals["deal_probability "], STAGE_PROBABILITY.get(stage, 10.0)),
                             safe_float(vals["expected_close_value "]), closed_at, row["id"]))
        page.refresh()
        self.refresh_dashboard()

    def advance_stage(self, page: DataTablePage, table: str) -> None:
        rows = page.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more rows first. ")
            return
        if len(rows) > 1:
            ask = QMessageBox.question(self, "Next Stage ", f"Advance {len(rows)} selected record(s) to their next stage? ")
            if ask != QMessageBox.Yes:
                return
        for row in rows:
            current = row.get("workflow_stage ") or "Lead "
            current = current if current in DEAL_STAGES else "Lead "
            next_stage = DEAL_STAGES[min(DEAL_STAGES.index(current) + 1, len(DEAL_STAGES) - 1)]
            closed_at = datetime.now() if next_stage == "Deal Done " else None
            self.services.execute(f"""UPDATE {table}
                SET workflow_stage=?, deal_probability=?, last_contacted=?, closed_at=COALESCE(?, closed_at)
                WHERE id=? """, (next_stage, STAGE_PROBABILITY.get(next_stage, 10.0), datetime.now().strftime("%Y-%m-%d "), closed_at, row["id"]))
        page.refresh()
        self.refresh_dashboard()

    def set_approval(self, page: DataTablePage, table: str, status: str) -> None:
        rows = page.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select ", "Select one or more rows first. ")
            return
        comment = " "
        if status == "Resend ":
            dialog = CommentDialog("Resend ", "Comment for the user: ", self)
            if dialog.exec() != QDialog.Accepted:
                return
            comment = dialog.value()
            if not comment:
                QMessageBox.warning(self, "Comment ", "Comment is required. ")
                return
        if len(rows) > 1:
            ask = QMessageBox.question(self, "Approval ", f"Set {len(rows)} selected record(s) to {status}? ")
            if ask != QMessageBox.Yes:
                return
        for row in rows:
            self.services.execute(f"""UPDATE {table}
                SET approval_status=?, approval_comment=?, approved_by=?, approved_at=?
                WHERE id=? """, (status, comment, self.current_user["username "], datetime.now(), row["id"]))
        page.refresh()

    def ai_match(self, page: DataTablePage, table: str) -> None:
        row = page.require_single_row("AI matching ")
        if not row:
            return
        text = self.ai_match_text(table, row["id"])
        dialog = QDialog(self)
        dialog.setWindowTitle("AI Smart Match ")
        dialog.resize(760, 460)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setFont(QFont("Consolas ", 10))
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        # FIX: Corrected split method name
        layout.addWidget(buttons)
        dialog.exec()

    def ai_match_text(self, table: str, row_id: int) -> str:
        try:
            return self.intelligence_service.match_report(table, row_id)
        except Exception as exc:
            fallback_header = f"Local AI match unavailable: {exc}\nUsing basic matching fallback.\n\n "
        else:
            fallback_header = " "
        target = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=? ", (row_id,))
        if not target:
            return "No record found. "
        if table == "rent_requirements ":
            rows = self.services.fetch_all("""SELECT id, owner_name AS name, location, monthly_rent AS amount, property_availability AS type
               FROM rent_availability WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
               ORDER BY ABS(COALESCE(monthly_rent,0)-COALESCE(?,0)) ASC LIMIT 10 """, (target.get("location ") or " ", target.get("property_requires ") or " ", target.get("budget ") or 0))
        elif table == "sale_requirements ":
            rows = self.services.fetch_all("""SELECT id, owner_name AS name, location, demand AS amount, property_availability AS type
               FROM sale_availability WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
               # FIX: Corrected split keyword
               ORDER BY ABS(COALESCE(demand,0)-COALESCE(?,0)) ASC LIMIT 10 """, (target.get("location ") or " ", target.get("property_requires ") or " ", target.get("budget ") or 0))
        elif table == "rent_availability ":
            rows = self.services.fetch_all("""SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
               FROM rent_requirements WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
               ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10 """, (target.get("location ") or " ", target.get("property_availability ") or " ", target.get("monthly_rent ") or 0))
        else:
            rows = self.services.fetch_all("""SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
               FROM sale_requirements WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
               ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10 """, (target.get("location ") or " ", target.get("property_availability ") or " ", target.get("demand ") or 0))
        lines = [f"Smart matches for {table} #{row_id} ", "-" * 72]
        for item in rows:
            lines.append(f"#{item['id']: <4} {str(item.get('name') or '-')[:24]: <24}  "
                         f"{str(item.get('location') or '-')[:18]: <18} {str(item.get('type') or '-')[:15]: <15}  "
                         f"{money(item.get('amount'), self.currency_symbol): >12} ")
        result = "\n".join(lines) if rows else "No close matches found. "
        return fallback_header + result

    def pipeline_counts(self) -> dict[str, int]:
        counts = {stage: 0 for stage in DEAL_STAGES}
        for table in DEAL_TABLES:
            rows = self.services.fetch_all(f"""SELECT COALESCE(NULLIF(workflow_stage,''), 'Lead') AS stage, COUNT(*) AS count
                FROM {table} GROUP BY COALESCE(NULLIF(workflow_stage,''), 'Lead') """)
            for row in rows:
                stage = row.get("stage ") if row.get("stage ") in DEAL_STAGES else "Lead "
                counts[stage] = counts.get(stage, 0) + int(row.get("count ") or 0)
        return counts

    def pipeline_rows(self, stage: str | None = None) -> list[dict]:
        datasets = [
            ("Rent Req ", "rent_requirements ", "client_name ", "property_requires ", "budget "),
            ("Rent Av ", "rent_availability ", "owner_name ", "property_availability ", "monthly_rent "),
            ("Sale Req ", "sale_requirements ", "client_name ", "property_requires ", "budget "),
            ("Sale Av ", "sale_availability ", "owner_name ", "property_availability ", "demand "),
        ]
        rows: list[dict] = []
        for source, table, name_col, type_col, amount_col in datasets:
            where = " "
            params: tuple[Any, ...] = ()
            if stage:
                where = "WHERE COALESCE(NULLIF(workflow_stage,''), 'Lead')=? "
                params = (stage,)
            for row in self.services.fetch_all(f"""SELECT id, {name_col} AS name, location, {type_col} AS property_type,
                       {amount_col} AS amount, workflow_stage, priority, expected_close_value
                 FROM {table} {where} ORDER BY id DESC LIMIT 20 """, params):
                rows.append({"source ": source, "id ": row["id"], "name ": row.get("name ") or " ", "location ": row.get("location ") or " ",
                             "stage ": row.get("workflow_stage ") or "Lead ", "priority ": row.get("priority ") or "Medium ",
                             "amount ": row.get("expected_close_value ") or row.get("amount ") or 0})
        return rows[:40]

    def open_report(self, kind: str) -> None:
        reports = self.pages.get("reports ")
        if isinstance(reports, ReportsModule):
            self.switch_page("reports ")
            reports.report_type.setCurrentText("Rent " if kind == "rent " else "Sale ")
            reports.generate(kind)
        else:
            self.preview_report(kind)

    def preview_report(self, kind: str) -> None:
        if kind == "sale ":
            result = self.report_service.sale_report()
        elif kind == "both ":
            result = self.report_service.dealings_report()
        else:
            result = self.report_service.rent_report()
        self.last_report = result
        ReportPreviewDialog(result, self).exec()

    def open_search(self) -> None:
        SearchDialog(self).exec()

    def financial_text(self) -> str:
        page = self.pages.get("financials ")
        if isinstance(page, FinancialModule):
            page.summary.refresh()
            return page.summary.text.toPlainText()
        return SummaryPage(self).text.toPlainText()

    # FIX: Corrected split function name
    def generic_report(self, table: str, title: str) -> str:
        rows = self.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC ")
        lines = ["=" * 78, title, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} ", "=" * 78, " "]
        for row in rows:
            important = []
            for key in ("id ", "client_name ", "owner_name ", "full_name ", "title ", "phone ", "contact ", "location ", "status ", "role "):
                if key in row and row[key] not in (None, " "):
                    important.append(f"{key}: {row[key]} ")
            lines.append(" | ".join(important) if important else str(row))
        lines.append(" ")
        lines.append(f"Total: {len(rows)} ")
        return "\n".join(lines)

    def attendance_report(self) -> str:
        rows = self.services.fetch_all("""SELECT a.date, e.full_name, a.status, a.notes
           FROM attendance a JOIN employees e ON a.employee_id=e.id
           ORDER BY a.date DESC, e.full_name """)
        lines = ["=" * 78, "ATTENDANCE REPORT ", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} ", "=" * 78, " "]
        for row in rows:
            lines.append(f"{row['date']: <12} {row['full_name'][:28]: <28} {row['status'] or '-': <10} {row['notes'] or ''} ")
        lines.append(" ")
        lines.append(f"Total rows: {len(rows)} ")
        return "\n".join(lines)

    def export_all_tables(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        base, _ = QFileDialog.getSaveFileName(self, "Export All Tables ", str(OUTPUT_DIR / f"crm_export_{datetime.now().strftime('%Y%m%d')}.csv "), "CSV Files (*.csv) ")
        if not base:
            return
        stem, ext = os.path.splitext(base)
        tables = ["rent_requirements ", "rent_availability ", "sale_requirements ", "sale_availability ",
                  "income_transactions ", "expense_transactions ", "employees ", "clients ", "properties ",
                  "attendance ", "salary_payments ", "users "]
        for table in tables:
            rows = self.services.fetch_all(f"SELECT * FROM {table} ")
            if not rows:
                continue
            with open(f"{stem}_{table}{ext} ", "w ", newline=" ", encoding="utf-8 ") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        # FIX: Corrected split method name
        QMessageBox.information(self, "Exported ", f"Tables exported with prefix:\n{stem} ")

    def backup_database(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Backup Database ", str(OUTPUT_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db "), "SQLite DB (*.db) ")
        if not path:
            return
        shutil.copy2(DB_PATH, path)
        QMessageBox.information(self, "Backup ", f"Database backed up to:\n{path} ")

    def show_api_health(self) -> None:
        QMessageBox.information(self, "Local API ", f"Local API service is available at:\n{self.local_service_url}\n\n "
                                "Useful routes:\n/health\n/meta\n/stats\n/pipeline\n/search?q=karachi\n/records/rent_requirements ")

    def show_text_dialog(self, title: str, text: str, *, width: int = 760, height: int = 560) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        # FIX: Corrected split method name
        preview.setReadOnly(True)
        preview.setWordWrapMode(preview.wordWrapMode())
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_user_guide(self) -> None:
        self.show_text_dialog("User Guide ", """PROFESSIONAL REAL ESTATE CRM - QT USER GUIDE
===============================================
DASHBOARD
View key totals, income/expense totals, and pipeline activity.
RENT AND SALE DEALINGS
Add requirements and available properties.
Edit records, advance workflow stage, approve/resend records, and run smart matching.
PROPERTIES AND CLIENTS
Maintain portfolio and contact records.
Use Details or Copy Row for quick review/sharing.
FINANCIALS
Record income and expense transactions.
Review and export profit/loss summary.
EMPLOYEES
Maintain employee records.
Mark attendance and process salary payments.
REPORTS
Generate rent, sale, combined, financial, property, client, employee, and attendance reports.
Export TXT, CSV, or PDF.
AI INSIGHTS
Run local pandas/numpy analysis for lead scoring, NLP keywords, matching, price guidance, and forecasts.
AI features stay offline on the local SQLite database.
LOCAL API
The Qt app runs the same lightweight local API service from app.py.
Check Help > API Health for URL and routes.
SECURITY
Role-based access controls remain active.
Admin roles can manage users, approvals, settings, backup, and delete records.
""")

    def show_roles_info(self) -> None:
        lines = ["ROLE-BASED ACCESS CONTROL ", "=" * 72,
                 "Feature            Super Admin  Admin   Manager   Staff   Viewer ", "-" * 72,
                 "Dashboard          Yes          Yes     Yes       No      Yes ",
                 "Rent/Sale Deals    Full         Full    Full      Add     View ",
                 "Properties         Full         Full    Full      Add     View ",
                 "Clients            Full         Full    Full      Add     View ",
                 "Financials         Full         Full    View      No      No ",
                 "Employees          Full         Full    Full      View    View ",
                 "Reports            Yes          Yes     Yes       No      Yes ",
                 "AI Insights         Yes          Yes     Yes       No      No ",
                 "Settings           Yes          Yes     No        No      No ",
                 "User Management    Yes          Yes     No        No      No ",
                 "Delete Records     Yes          Yes     No        No      No ",
                 "Backup/Export      Yes          Yes     No        No      No ", " ",
                 "Permissions configured in qt_crm_app.py: "]
        for role, permissions in ROLE_PERMISSIONS.items():
            lines.append(f"{role: <12}: {', '.join(permissions)} ")
        self.show_text_dialog("Roles & Permissions ", "\n".join(lines), width=780, height=560)

    def show_developer_info(self) -> None:
        QMessageBox.information(self, "Developer Info", "Developer: Muhammad Siddique\nEmail: info@msxhan.online\n\nApplication: Professional Real Estate CRM\nUI Framework: Python + PySide6/Qt")

    def show_about(self) -> None:
        QMessageBox.information(self, "About ", f"Professional Real Estate CRM\nVersion: Qt Migration\n\nBuilt with Python and PySide6\nDatabase: SQLite\nDB File: {DB_PATH}\nLocal API: {self.local_service_url}\n\nDeveloper: Muhammad Siddique\nEmail: info@msxhan.online\n\nCompany: {self.company_name}\nUser: {self.current_user.get('full_name')} ({self.role})\nYear: {datetime.now().year} ")

    def restart_app(self) -> None:
        self.stop_local_service()
        # FIX: Corrected missing dunder `__file__` variable
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent))
        QApplication.quit()

    def logout(self) -> None:
        if QMessageBox.question(self, "Logout", "Logout and return to the login screen?") != QMessageBox.Yes:
            return
        self.restart_app()

    def closeEvent(self, event: Any) -> None:
        self.stop_local_service()
        super().closeEvent(event)

# --- Spec Builders (unchanged logic) ---
def deal_common_fields(name_key: str, property_key: str, amount_key: str) -> list[FieldSpec]:
    name_label = "Name * " if name_key == "client_name " else "Owner Name * "
    property_label = "Property Requires " if "requires " in property_key else "Property Availability "
    amount_label = "Budget " if amount_key == "budget " else ("Rent " if amount_key == "monthly_rent " else "Demand ")
    return [
        FieldSpec("Date * ", "date ", "date ", required=True), FieldSpec(name_label, name_key, required=True),
        FieldSpec("Contact ", "contact "), FieldSpec(property_label, property_key, "combo_other ", options=["flat ", "banglow ", "shop ", "godam ", "plot ", "building ", "villa ", "house "]),
        FieldSpec("Size ", "size ", "combo_other ", options=["single-bed ", "double-bed ", "any floor ", "ground floor ", "single story ", "double story ", "mezzanine ", "basement "]),
        FieldSpec("Measurement ", "measurement "), FieldSpec(f"{amount_label} (Rs.) ", amount_key, numeric=True),
        FieldSpec("Floor ", "floor "), FieldSpec("Location * ", "location ", "autocomplete ", options=COMMON_AREAS, required=True),
        FieldSpec("Option 1 ", "option1 "), FieldSpec("Option 2 ", "option2 "),
        FieldSpec("Facilities ", "facilities ", "facilities ", options=FACILITY_OPTIONS),
        FieldSpec("Client / Broker ", "client_broker "), FieldSpec("Bachelor / Family ", "bachelor_family "),
        FieldSpec("Remarks ", "remarks ", "text "), FieldSpec("Workflow Stage ", "workflow_stage ", "combo ", "Lead ", DEAL_STAGES),
        FieldSpec("Priority ", "priority ", "combo ", "Medium ", DEAL_PRIORITIES), FieldSpec("Next Follow-up ", "next_follow_up "),
        FieldSpec("Assigned To ", "assigned_to "), FieldSpec("Probability % ", "deal_probability ", "entry ", " ", numeric=True),
        FieldSpec("Expected Value ", "expected_close_value ", "entry ", " ", numeric=True),
    ]

def deal_fields(name_key: str, property_key: str, amount_key: str) -> list[FieldSpec]:
    return deal_common_fields(name_key, property_key, amount_key)

def availability_fields(name_key: str, property_key: str, amount_key: str) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key)
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor ") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields

def deal_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return ["date ", name_key, "contact ", property_key, "size ", "measurement ", amount_key, "floor ", "location ", "option1 ", "option2 ", "facilities ", "client_broker ", "bachelor_family ", "remarks ", "workflow_stage ", "priority ", "next_follow_up ", "assigned_to ", "deal_probability ", "expected_close_value ", "approval_status ", "approval_comment ", "created_by ", "created_at "]

def deal_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return ["date ", name_key, "contact ", property_key, "size ", "measurement ", amount_key, "floor ", "location ", "option1 ", "option2 ", "facilities ", "client_broker ", "bachelor_family ", "remarks ", "workflow_stage ", "priority ", "next_follow_up ", "assigned_to ", "deal_probability ", "expected_close_value ", "approval_status ", "approval_comment "]

def availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return deal_insert_columns(name_key, property_key, amount_key)

def availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return deal_update_columns(name_key, property_key, amount_key)

def property_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Property Code ", "property_code ", "entry ", lambda: gen_id("PROP ")), FieldSpec("Title * ", "title ", required=True),
        FieldSpec("Type ", "property_type ", "combo ", options=["Apartment ", "House ", "Villa ", "Studio ", "Shop ", "Office ", "Warehouse ", "Plot "]),
        FieldSpec("Status ", "status ", "combo ", "Available ", ["Available ", "Rented ", "Sold ", "Reserved "]),
        FieldSpec("Owner Name ", "owner_name "), FieldSpec("Owner Contact ", "owner_contact "),
        FieldSpec("Location * ", "location ", "autocomplete ", options=COMMON_AREAS, required=True),
        FieldSpec("Area ", "area "), FieldSpec("Floor ", "floor ", "combo_other ", options=["Ground ", "1st ", "2nd ", "3rd ", "4th ", "5th ", "Top "]),
        FieldSpec("Monthly Rent ", "monthly_rent ", numeric=True), FieldSpec("Sale Price ", "sale_price ", numeric=True),
        FieldSpec("Maintenance ", "maintenance_charge ", numeric=True), FieldSpec("Facilities ", "facilities ", "facilities ", options=FACILITY_OPTIONS),
        FieldSpec("Description ", "description ", "text "),
    ]
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("property_code ", "Code ", width=110), ColumnSpec("title ", "Title ", width=180), ColumnSpec("property_type ", "Type ", width=110),
            ColumnSpec("status ", "Status ", width=100), ColumnSpec("owner_name ", "Owner ", width=150), ColumnSpec("location ", "Location ", width=160),
            ColumnSpec("monthly_rent ", "Rent ", m, 110), ColumnSpec("sale_price ", "Sale Price ", m, 120), ColumnSpec("maintenance_charge ", "Maintenance ", m, 120),
            ColumnSpec("facilities ", "Facilities ", width=220), ColumnSpec("description ", "Description ", width=240)]
    insert = ["property_code ", "title ", "property_type ", "status ", "owner_name ", "owner_contact ", "location ", "area ", "floor ", "monthly_rent ", "sale_price ", "maintenance_charge ", "facilities ", "description ", "created_at "]
    update = ["property_code ", "title ", "property_type ", "status ", "owner_name ", "owner_contact ", "location ", "area ", "floor ", "monthly_rent ", "sale_price ", "maintenance_charge ", "facilities ", "description "]
    return TableSpec("Properties ", "properties ", cols, fields, insert, update)

def client_spec() -> TableSpec:
    fields = [
        FieldSpec("Client Name * ", "client_name ", required=True), FieldSpec("Phone ", "phone "), FieldSpec("Email ", "email "),
        FieldSpec("Address ", "address ", "text "), FieldSpec("Client Type ", "client_type ", "combo ", "Tenant ", ["Tenant ", "Buyer ", "Seller ", "Investor ", "Other "]),
        FieldSpec("Status ", "status ", "combo ", "Active ", ["Active ", "Inactive "]), FieldSpec("Notes ", "notes ", "text "),
    ]
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("client_name ", "Name ", width=180), ColumnSpec("phone ", "Phone ", width=130),
            ColumnSpec("email ", "Email ", width=180), ColumnSpec("client_type ", "Type ", width=110), ColumnSpec("status ", "Status ", width=100),
            ColumnSpec("address ", "Address ", width=220), ColumnSpec("notes ", "Notes ", width=240)]
    insert = ["client_name ", "phone ", "email ", "address ", "client_type ", "status ", "notes ", "created_at "]
    update = ["client_name ", "phone ", "email ", "address ", "client_type ", "status ", "notes "]
    return TableSpec("Clients ", "clients ", cols, fields, insert, update)

def income_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Date * ", "transaction_date ", "date ", required=True), FieldSpec("Income Type * ", "income_type ", "combo ", options=["Rent ", "Deposit ", "Maintenance ", "Commission ", "Utility ", "Advance ", "Other "], required=True),
        FieldSpec("Amount * ", "amount ", numeric=True, required=True), FieldSpec("Client Name ", "tenant_name "), FieldSpec("Description ", "description "),
        FieldSpec("Receipt No ", "receipt_no ", "entry ", lambda: gen_id("RCP ")), FieldSpec("Payment Method ", "payment_method ", "combo ", "Cash ", ["Cash ", "Cheque ", "Bank Transfer ", "Online "]),
    ]
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("transaction_date ", "Date ", width=100), ColumnSpec("income_type ", "Type ", width=130), ColumnSpec("amount ", "Amount ", m, 120),
            ColumnSpec("tenant_name ", "Client ", width=150), ColumnSpec("description ", "Description ", width=220), ColumnSpec("receipt_no ", "Receipt No ", width=120), ColumnSpec("payment_method ", "Method ", width=120)]
    insert = ["transaction_date ", "income_type ", "amount ", "tenant_name ", "description ", "receipt_no ", "payment_method ", "created_by ", "created_at "]
    update = ["transaction_date ", "income_type ", "amount ", "tenant_name ", "description ", "receipt_no ", "payment_method "]
    return TableSpec("Income ", "income_transactions ", cols, fields, insert, update, permission="financial ")

def expense_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Date * ", "transaction_date ", "date ", required=True), FieldSpec("Category * ", "expense_category ", "combo ", options=["Maintenance ", "Utilities ", "Repair ", "Salary ", "Commission ", "Tax ", "Legal ", "Marketing ", "Other "], required=True),
        FieldSpec("Amount * ", "amount ", numeric=True, required=True), FieldSpec("Vendor Name ", "vendor_name "), FieldSpec("Description ", "description "),
        FieldSpec("Invoice No ", "invoice_no ", "entry ", lambda: gen_id("INV ")), FieldSpec("Payment Method ", "payment_method ", "combo ", "Cash ", ["Cash ", "Cheque ", "Bank Transfer ", "Online "]),
    ]
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("transaction_date ", "Date ", width=100), ColumnSpec("expense_category ", "Category ", width=130), ColumnSpec("amount ", "Amount ", m, 120),
            ColumnSpec("vendor_name ", "Vendor ", width=150), ColumnSpec("description ", "Description ", width=220), ColumnSpec("invoice_no ", "Invoice No ", width=120), ColumnSpec("payment_method ", "Method ", width=120)]
    insert = ["transaction_date ", "expense_category ", "amount ", "vendor_name ", "description ", "invoice_no ", "payment_method ", "created_by ", "created_at "]
    update = ["transaction_date ", "expense_category ", "amount ", "vendor_name ", "description ", "invoice_no ", "payment_method "]
    return TableSpec("Expenses ", "expense_transactions ", cols, fields, insert, update, permission="financial ")

def employee_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    pct = lambda value, _symbol: f"{safe_float(value):.1f}% "
    fields = [
        FieldSpec("Employee ID ", "employee_id ", "entry ", lambda: gen_id("EMP ")), FieldSpec("Full Name * ", "full_name ", required=True),
        FieldSpec("Phone ", "phone "), FieldSpec("Email ", "email "),
        FieldSpec("Position * ", "position ", "combo_other ", options=["Agent ", "Manager ", "Broker ", "Admin ", "Staff ", "Driver ", "Security ", "Cleaner "], required=True),
        FieldSpec("Department ", "department ", "combo_other ", options=["Sales ", "Rentals ", "Administration ", "Finance ", "Operations "]),
        FieldSpec("Hire Date ", "hire_date ", "date "), FieldSpec("Base Salary * ", "base_salary ", numeric=True, required=True),
        FieldSpec("Commission % ", "commission_rate ", "entry ", "5.0 ", numeric=True), FieldSpec("Address ", "address ", "text "),
        FieldSpec("Notes ", "notes ", "text "), FieldSpec("Status ", "status ", "combo ", "Active ", ["Active ", "Inactive ", "On Leave ", "Terminated "]),
    ]
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("employee_id ", "Emp ID ", width=110), ColumnSpec("full_name ", "Name ", width=170),
            ColumnSpec("position ", "Position ", width=130), ColumnSpec("department ", "Department ", width=130), ColumnSpec("phone ", "Phone ", width=130),
            ColumnSpec("base_salary ", "Salary ", m, 120), ColumnSpec("commission_rate ", "Commission ", pct, 110),
            ColumnSpec("status ", "Status ", width=100), ColumnSpec("notes ", "Notes ", width=220)]
    insert = ["employee_id ", "full_name ", "phone ", "email ", "position ", "department ", "hire_date ", "base_salary ", "commission_rate ", "address ", "notes ", "status ", "created_at "]
    update = ["employee_id ", "full_name ", "phone ", "email ", "position ", "department ", "hire_date ", "base_salary ", "commission_rate ", "address ", "notes ", "status "]
    return TableSpec("Employees ", "employees ", cols, fields, insert, update, permission="employees ")

def salary_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    cols = [ColumnSpec("id ", "ID ", width=64), ColumnSpec("full_name ", "Employee ", width=170), ColumnSpec("month ", "Month ", width=110), ColumnSpec("year ", "Year ", width=80),
            ColumnSpec("base_salary ", "Base Salary ", m, 120), ColumnSpec("bonus ", "Bonus ", m, 110), ColumnSpec("deductions ", "Deductions ", m, 120),
            ColumnSpec("net_salary ", "Net Salary ", m, 120), ColumnSpec("payment_method ", "Method ", width=120)]
    return TableSpec("Salary History ", "salary_payments ", cols, [], [], [], permission="employees ")

APP_STYLE = """
QMainWindow { background: #eef2f7; }
#Sidebar { background: #101827; border: none; }
#BrandCard { background: #172338; border: 1px solid #263650; border-radius: 10px; }
#LogoBadge { background: #2563eb; color: #ffffff; border-radius: 8px; min-width: 42px; max-width: 42px; min-height: 42px; max-height: 42px; font-size: 15px; font-weight: 900; }
#LogoImage { background: transparent; border: none; }
#Brand { color: #ffffff; font-size: 19px; font-weight: 900; }
#SidebarSubtle { color: #91a4c0; font-size: 12px; }
#SidebarStatusText { color: #dbeafe; font-size: 12px; font-weight: 800; }
#UserCard { background: #0f172a; border: 1px solid #263650; border-radius: 10px; }
#SidebarUserName { color: #ffffff; font-size: 14px; font-weight: 800; }
#RolePill { background: #e0f2fe; color: #075985; border-radius: 9px; padding: 3px 9px; font-size: 11px; font-weight: 800; }
#NavShell { background: transparent; border: none; }
QScrollArea#SidebarNavScroll { background: transparent; border: none; }
QScrollArea#SidebarNavScroll QScrollBar:vertical { background: #0f172a; border: none; border-radius: 4px; width: 8px; margin: 4px 0 4px 0; }
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical { background: #334155; border-radius: 4px; min-height: 34px; }
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical:hover { background: #475569; }
QScrollArea#SidebarNavScroll QScrollBar::add-line:vertical, QScrollArea#SidebarNavScroll QScrollBar::sub-line:vertical { height: 0; }
#NavSeparator { background: #22324c; border: none; min-height: 1px; max-height: 1px; margin: 8px 8px 5px 8px; }
#NavSection { color: #7f93b2; font-size: 10px; font-weight: 900; padding: 8px 8px 2px 8px; }
QFrame#NavItem { background: transparent; border: 1px solid transparent; border-radius: 9px; }
QFrame#NavItem:hover { background: #18243a; border-color: #2b3d5a; }
QFrame#NavItem[active="true"] { background: #2563eb; border-color: #3b82f6; }
QFrame#NavItem:hover QLabel#NavText { color: #ffffff; }
QFrame#NavItem:hover QLabel#NavIcon { background: #263956; }
#NavIndicator { background: transparent; border-radius: 2px; }
#NavIndicator[active="true"] { background: #bfdbfe; }
QLabel#NavIcon { background: #1e2b42; color: #dbeafe; border-radius: 6px; font-size: 10px; font-weight: 900; }
QLabel#NavIcon[active="true"] { background: #dbeafe; color: #1d4ed8; }
QLabel#NavText { color: #dbeafe; font-size: 13px; font-weight: 800; }
QLabel#NavText[active="true"] { color: #ffffff; }
#SidebarFooter { background: #0f172a; border: 1px solid #263650; border-radius: 10px; }
#StatusDot { background: #22c55e; border-radius: 5px; min-width: 10px; max-width: 10px; min-height: 10px; max-height: 10px; }
#SidebarLogout { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 7px; padding: 9px 12px; font-weight: 800; }
#SidebarLogout:hover { background: #eff6ff; border-color: #93c5fd; }
#Content { background: #eef2f7; }
#TopTitle { color: #0f172a; font-size: 18px; font-weight: 800; }
#PageTitle { color: #0f172a; font-size: 24px; font-weight: 800; }
#SectionTitle { color: #0f172a; font-size: 17px; font-weight: 800; }
#MetricCard, #Panel { background: white; border: 1px solid #d9e2ef; border-radius: 8px; }
#MetricTitle { color: #64748b; font-size: 12px; font-weight: 800; text-transform: uppercase; }
#MetricValue { color: #0f172a; font-size: 27px; font-weight: 900; }
#MetricNote { color: #64748b; font-size: 12px; }
#LoginTitle { color: #0f172a; font-size: 28px; font-weight: 900; }
#MutedText { color: #64748b; }
#SelectionCount { color: #64748b; font-size: 12px; font-weight: 800; }
QTableWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; selection-background-color: #dbeafe; }
QTableWidget { padding: 0; gridline-color: #e2e8f0; }
QTableWidget::item { color: #0f172a; padding: 5px; }
QTableWidget::item:selected { background: #dbeafe; color: #0f172a; }
QHeaderView::section { background: #f8fafc; color: #334155; border: none; border-bottom: 1px solid #d9e2ef; padding: 8px; font-weight: 800; }
QPushButton { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; font-weight: 600; }
QPushButton:hover { background: #f8fafc; }
#AccentButton { background: #2563eb; color: white; border: 1px solid #2563eb; }
#AccentButton:hover { background: #1d4ed8; }
#DangerButton { background: #dc2626; color: white; border: 1px solid #dc2626; }
#DangerButton:hover { background: #b91c1c; }
#FacilitiesBox { background: #f8fafc; border: 1px solid #d9e2ef; border-radius: 6px; }
QCheckBox#FacilityCheck { background: #e5e7eb; color: #0f172a; border-radius: 2px; padding: 4px 7px; font-weight: 700; spacing: 6px; }
QCheckBox#FacilityCheck:hover { background: #dbeafe; }
QCheckBox#FacilityCheck::indicator { width: 14px; height: 14px; }
QTabWidget::pane { border: 1px solid #d9e2ef; background: #ffffff; border-radius: 8px; }
QTabBar::tab { background: #f8fafc; padding: 9px 14px; border: 1px solid #d9e2ef; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #ffffff; color: #2563eb; font-weight: 800; }
"""

def main() -> int:
    if not PYSIDE_AVAILABLE:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        return 1
    ensure_database()
    services = CRMServices()
    app = QApplication(sys.argv)
    app.setWindowIcon(crm_app_icon())
    app.setStyleSheet(APP_STYLE)
    login = LoginDialog(services)
    if login.exec() != QDialog.Accepted or not login.current_user:
        return 0
    window = ModernCRMWindow(services, login.current_user)
    window.show()
    return app.exec()

# FIX: Corrected missing dunder `__name__` and `__main__`
if __name__ == "__main__":
    raise SystemExit(main())