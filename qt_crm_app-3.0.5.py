"""Full PySide6 CRM application backed by the existing SQLite database.

This is the Qt replacement for the Tkinter UI in professional_crm.py. It keeps
the same database tables and business workflows while moving the desktop
experience to PySide6.

Run:
    .venv\\Scripts\\python.exe qt_crm_app.py
"""

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
    # FIX: Removed any whitespace inside QMarginsF
    from PySide6.QtCore import QDate, QEvent, QMarginsF, Qt, Signal
    from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPageLayout, QPageSize, QPixmap, QTextDocument
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDateEdit,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSizePolicy,
        QStackedWidget,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
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


COMMON_AREAS = [
    "Gulshan", "Gulistan-e-Johar", "Gulberg", "Clifton", "DHA", "Defence",
    "Saddar", "Korangi", "Landhi", "Malir", "North Nazimabad", "Nazimabad",
    "PECHS", "Scheme 33", "Shah Faisal", "Tariq Road", "Bahadurabad",
    "KDA Scheme", "Military Account", "Hyderi", "Water Pump", "FB Area",
    "Liaquatabad", "Jamshed Road", "University Road", "Super Highway",
    "Rashid Minhas", "Airport", "Cantt", "Garden", "Boat Basin", "Sea View",
    "Marina", "Gizri", "Clifton Block 1", "Clifton Block 2", "Clifton Block 3",
    "Clifton Block 4", "Clifton Block 5", "Clifton Block 6", "Clifton Block 7",
    "Clifton Block 8", "Clifton Block 9", "DHA Phase 1", "DHA Phase 2",
    "DHA Phase 4", "DHA Phase 5", "DHA Phase 6", "DHA Phase 7", "DHA Phase 8",
]

DEAL_STAGES = ["Lead", "Contacted", "Visit Scheduled", "Negotiation", "Closed", "Deal Done"]
DEAL_PRIORITIES = ["Low", "Medium", "High", "Urgent"]
FACILITY_OPTIONS = [
    "lift",
    "car parking",
    "cctv",
    "security",
    "sweet water",
    "salty water",
    "gas",
    "electercity 24/7",
    "electercity with loadshading",
]
FACILITY_ALIASES = {
    "parking": "car parking",
    "car park": "car parking",
    "electricity 24/7": "electercity 24/7",
    "electric 24/7": "electercity 24/7",
    "electricity with load shedding": "electercity with loadshading",
    "electricity with loadshading": "electercity with loadshading",
    "electric with load shedding": "electercity with loadshading",
    "electric with loadshading": "electercity with loadshading",
    "load shedding": "electercity with loadshading",
    "loadshading": "electercity with loadshading",
}
OWNER_BROKER_OPTIONS = ["O", "B"]
LONG_TEXT_COLUMN_KEYS = {"facilities", "remarks", "description", "notes", "address"}
GLOBAL_SEARCH_HIDDEN_COLUMNS = {"cnic", "password_hash"}
GLOBAL_SEARCH_MONEY_COLUMNS = {
    "amount",
    "budget",
    "budget_min",
    "budget_max",
    "monthly_rent",
    "maintenance",
    "maintenance_budget",
    "maintenance_charge",
    "deposit",
    "demand",
    "asking_price",
    "sale_price",
    "base_salary",
    "commission_amount",
    "deal_value",
    "commissions_earned",
    "bonuses",
    "bonus",
    "deductions",
    "net_salary",
    "total_income",
    "total_expense",
    "net_profit",
    "expected_close_value",
}
STAGE_PROBABILITY = {
    "Lead": 10.0,
    "Contacted": 25.0,
    "Visit Scheduled": 45.0,
    "Negotiation": 70.0,
    "Closed": 90.0,
    "Deal Done": 100.0,
}
DEAL_TABLES = ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability")
GLOBAL_SEARCH_SOURCES = [
    ("Rent Requirement", "rent_requirements"),
    ("Rent Availability", "rent_availability"),
    ("Sale Requirement", "sale_requirements"),
    ("Sale Availability", "sale_availability"),
]
GLOBAL_SEARCH_SOURCE_LABELS = dict(GLOBAL_SEARCH_SOURCES)
FIND_SOURCE_ORDER = {table: index for index, (_label, table) in enumerate(GLOBAL_SEARCH_SOURCES)}
FIND_SOURCE_PERMISSIONS = {
    "rent_requirements": ("rent", "rent_view"),
    "rent_availability": ("rent", "rent_view"),
    "sale_requirements": ("sale", "sale_view"),
    "sale_availability": ("sale", "sale_view"),
}
FIND_RESULT_COLUMNS = {
    "rent_requirements": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_created", "created_at"), ""),
        ("client_name", "Name", ("client_name",), ""),
        ("client_status", "Owner/Broker", ("client_status", "client_broker", "broker", "preferred_broker"), "O"),
        ("contact", "Contact No.", ("contact", "contact_phone"), ""),
        ("property_requires", "Property Requirement", ("property_requires", "property_type"), ""),
        ("size", "Size", ("size", "size_beds", "sq_ft", "sq_ft_yards"), ""),
        ("budget", "Budget", ("budget", "budget_max", "budget_min"), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
    "rent_availability": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_posted", "created_at"), ""),
        ("owner_name", "Name", ("owner_name",), ""),
        ("broker", "Owner/Broker", ("broker", "posted_by_broker", "client_broker", "posted_by"), ""),
        ("contact", "Contact No.", ("contact", "contact_phone"), ""),
        ("property_availability", "Property Availability", ("property_availability", "property_type"), ""),
        ("size", "Size", ("size", "size_beds", "sq_ft", "sq_ft_yards"), ""),
        ("monthly_rent", "Rent", ("monthly_rent",), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
    "sale_requirements": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_created", "created_at"), ""),
        ("client_name", "Name", ("client_name",), ""),
        ("client_status", "Owner/Broker", ("client_status", "client_broker", "broker", "preferred_broker"), "O"),
        ("contact", "Contact No.", ("contact", "contact_phone"), ""),
        ("property_requires", "Property Requirement", ("property_requires", "property_type"), ""),
        ("size", "Size", ("size", "size_beds", "sq_ft", "sq_ft_yards"), ""),
        ("budget", "Budget", ("budget", "budget_max", "budget_min"), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
    "sale_availability": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_posted", "created_at"), ""),
        ("owner_name", "Name", ("owner_name",), ""),
        ("broker", "Owner/Broker", ("broker", "posted_by_broker", "client_broker", "posted_by"), ""),
        ("contact", "Contact No.", ("contact", "contact_phone"), ""),
        ("property_availability", "Property Availability", ("property_availability", "property_type"), ""),
        ("size", "Size", ("size", "size_beds", "sq_ft", "sq_ft_yards"), ""),
        ("demand", "Demand", ("demand", "asking_price"), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
}
FIND_ALL_COLUMN_ORDER = [
    "_source", "id", "date", "client_name", "owner_name", "client_status", "broker",
    "contact", "property_requires", "property_availability", "size", "budget",
    "monthly_rent", "demand", "floor", "location", "facilities", "remarks",
]
FIND_ALL_COLUMN_LABELS = {
    "_source": "Type",
    "id": "Sr No.",
    "date": "Date",
    "client_name": "Name",
    "owner_name": "Name",
    "client_status": "Owner/Broker",
    "broker": "Owner/Broker",
    "contact": "Contact No.",
    "property_requires": "Property Requirement",
    "property_availability": "Property Availability",
    "budget": "Budget",
    "monthly_rent": "Rent",
    "demand": "Demand",
    "floor": "Floor",
    "location": "Location",
    "facilities": "Facilities",
    "remarks": "Remarks",
}
LOCAL_SERVICE_PORT = int(os.getenv("CRM_DESKTOP_API_PORT", "6091"))
LAN_WEB_HOST = os.getenv("CRM_LAN_WEB_HOST", os.getenv("API_HOST", "0.0.0.0"))
LAN_WEB_PORT = int(os.getenv("CRM_LAN_WEB_PORT", os.getenv("API_PORT", "6090")))
LAN_WEB_ENABLED = os.getenv("CRM_LAN_WEB_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
DATE_FORM_KEYS = {"date", "transaction_date", "hire_date", "next_follow_up"}
DATE_STORAGE_FORMAT = "yyyy-MM-dd"
DATE_DISPLAY_FORMAT = "dd/MM/yyyy"
PY_DATE_STORAGE_FORMAT = "%Y-%m-%d"
PY_DATE_DISPLAY_FORMAT = "%d/%m/%Y"
PY_DATE_INPUT_FORMATS = (PY_DATE_STORAGE_FORMAT, PY_DATE_DISPLAY_FORMAT, "%d-%m-%Y")
EMAIL_FORM_KEYS = {"email", "company_email"}
PHONE_FORM_KEYS = {"contact", "phone", "owner_contact", "company_phone"}
CNIC_FORM_KEYS = {"cnic"}
PERCENT_FORM_KEYS = {"commission_rate", "deal_probability", "default_commission", "tax_rate"}

ROLE_PERMISSIONS = {
    "Super Admin": ["dashboard", "rent", "sale", "properties", "clients", "financial", "employees", "reports", "ai", "settings", "users", "backup", "delete"],
    "Admin": ["dashboard", "rent", "sale", "properties", "clients", "financial", "employees", "reports", "ai", "settings", "users", "backup", "delete"],
    "Manager": ["dashboard", "rent", "sale", "properties", "clients", "financial_view", "employees", "reports", "ai"],
    "Staff": ["rent", "sale"],
    "Viewer": ["dashboard", "rent_view", "sale_view", "reports"],
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])


def allowed_find_sources(role: str, *, staff_restricted: bool = False) -> list[tuple[str, str]]:
    if staff_restricted:
        return list(GLOBAL_SEARCH_SOURCES)
    return [
        (label, table)
        for label, table in GLOBAL_SEARCH_SOURCES
        if any(has_permission(role, permission) for permission in FIND_SOURCE_PERMISSIONS.get(table, ()))
    ]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").replace("Rs.", "").strip())
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", "").strip()))
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
    return parse_py_date(text) is not None


def parse_py_date(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in PY_DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text[:10], fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_qdate(value: Any) -> QDate:
    parsed = parse_py_date(value)
    if parsed:
        return QDate(parsed.year, parsed.month, parsed.day)
    return QDate.currentDate()


def is_date_key(key: str) -> bool:
    return key in DATE_FORM_KEYS or key.endswith("_date")


def format_date_display(value: Any, _symbol: str = "") -> str:
    parsed = parse_py_date(value)
    if parsed:
        return parsed.strftime(PY_DATE_DISPLAY_FORMAT)
    return "" if value in (None, "") else str(value)


def is_valid_email_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if " " in text or text.count("@") != 1:
        return False
    local, domain = text.split("@", 1)
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def is_valid_phone_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    return text.isdigit() and text.startswith("03") and len(text) == 11


def is_valid_cnic_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) == 13 and all(ch.isdigit() or ch == "-" for ch in text)


def validate_form_value(
    key: str,
    label: str,
    value: Any,
    *,
    required: bool = False,
    numeric: bool = False,
    options: list[str] | None = None,
    strict_options: bool = False,
) -> None:
    text = str(value or "").strip()
    clean_label = label.replace("*", "").strip()
    if required and not text:
        raise ValueError(f"Please enter {clean_label}.")
    if numeric and text and not is_valid_number_text(text):
        raise ValueError(f"Please enter a valid number for {clean_label}.")
    if is_date_key(key) and text and not is_valid_date_text(text):
        raise ValueError(f"{clean_label} must be in DD/MM/YYYY format.")
    if key in EMAIL_FORM_KEYS and text and not is_valid_email_text(text):
        raise ValueError(f"Please enter a valid email address for {clean_label}.")
    if key in PHONE_FORM_KEYS and text and not is_valid_phone_text(text):
        raise ValueError(f"{clean_label} must start with 03 and contain exactly 11 digits with no special characters.")
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
    text = str(value or "").strip().lower()
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
        QPageSize(QPageSize.PageSizeId.Legal),
        QPageLayout.Orientation.Landscape,
        QMarginsF(7, 7, 7, 7),
        QPageLayout.Unit.Millimeter,
    )
    printer.setPageLayout(page_layout)


def ensure_database() -> None:
    """Reuse the existing production schema initializer and migrations."""
    from professional_crm import Database

    Database.init_all()
    ensure_qt_schema()


def ensure_qt_schema() -> None:
    """Add Qt-screen columns that older deployed databases may be missing."""
    additions = {
        "rent_requirements": [
            ("client_status", "TEXT DEFAULT 'O'"),
            ("broker", "TEXT"),
        ],
        "rent_availability": [
            ("client_broker", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
        ],
        "sale_requirements": [
            ("client_status", "TEXT DEFAULT 'O'"),
            ("broker", "TEXT"),
        ],
        "sale_availability": [
            ("client_broker", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
        ],
    }
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        for table, columns in additions.items():
            existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
            for column, column_type in columns:
                if column not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    existing.add(column)
            if table in {"rent_requirements", "sale_requirements"}:
                if "client_status" in existing:
                    cur.execute(f"UPDATE {table} SET client_status='O' WHERE client_status IS NULL OR client_status=''")
                if "broker" in existing:
                    broker_sources = [column for column in ("preferred_broker", "client_broker") if column in existing]
                    if broker_sources:
                        fallback_values = [f"NULLIF({column}, '')" for column in broker_sources]
                        fallback = (
                            f"COALESCE({', '.join(fallback_values)})"
                            if len(fallback_values) > 1
                            else fallback_values[0]
                        )
                        cur.execute(
                            f"UPDATE {table} SET broker={fallback} "
                            "WHERE broker IS NULL OR broker=''"
                        )
        conn.commit()


class CRMServices:
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

    def table_columns(self, table: str) -> set[str]:
        repo_columns = getattr(self.repo, "table_columns", None)
        if callable(repo_columns):
            return set(repo_columns(table))
        rows = self.fetch_all(f"PRAGMA table_info({table})")
        return {row["name"] for row in rows if row.get("name")}

    def settings_get(self, key: str, default: str = "") -> str:
        row = self.fetch_one("SELECT value FROM app_settings WHERE key=?", (key,))
        return str(row["value"]) if row else default

    def settings_set(self, key: str, value: str) -> None:
        self.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, value))

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username: str, password: str) -> dict | None:
        row = self.fetch_one("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
        if row and row.get("password_hash") == self.hash_password(password):
            now = datetime.now()
            self.execute("UPDATE users SET last_login=? WHERE id=?", (now, row["id"]))
            self.execute(
                "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
                (row["id"], now, "Success"),
            )
            return row
        self.execute(
            "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
            (None, datetime.now(), "Failed"),
        )
        return None

    def create_user(self, username: str, password: str, full_name: str, email: str, role: str) -> tuple[bool, str]:
        if self.fetch_one("SELECT id FROM users WHERE username=?", (username,)):
            return False, "Username already exists."
        self.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at)
               VALUES (?,?,?,?,?,1,?)""",
            (username, self.hash_password(password), full_name, email, role, datetime.now()),
        )
        return True, "User created."

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        row = self.fetch_one("SELECT password_hash FROM users WHERE id=?", (user_id,))
        if not row:
            return False, "User not found."
        if row["password_hash"] != self.hash_password(old_password):
            return False, "Current password is incorrect."
        self.execute("UPDATE users SET password_hash=? WHERE id=?", (self.hash_password(new_password), user_id))
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

        title = QLabel("Real Estate CRM")
        title.setObjectName("LoginTitle")
        subtitle = QLabel("Sign in to open the Qt workspace")
        subtitle.setObjectName("MutedText")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.username.setPlaceholderText("Username")
        self.password.setPlaceholderText("Password")
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        hint = QLabel("Enter your assigned CRM username and password.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        self.login_button = buttons.addButton("Login", QDialogButtonBox.AcceptRole)
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password.returnPressed.connect(self.try_login)

    def try_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        user = self.services.login(username, password)
        if not user:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
            return
        self.current_user = user
        self.accept()


class StartupDialog(QDialog):
    def __init__(self, title: str = "Starting Real Estate CRM"):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowIcon(crm_app_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(480, 210)
        self.setObjectName("StartupDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        top = QHBoxLayout()
        logo = QLabel()
        pixmap = QPixmap(str(crm_logo_path()))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        top.addWidget(logo)
        heading_box = QVBoxLayout()
        title_label = QLabel("Real Estate CRM")
        title_label.setObjectName("StartupTitle")
        subtitle = QLabel("Preparing your workspace")
        subtitle.setObjectName("MutedText")
        heading_box.addWidget(title_label)
        heading_box.addWidget(subtitle)
        top.addLayout(heading_box, 1)
        layout.addLayout(top)

        self.message = QLabel("Starting...")
        self.message.setObjectName("MutedText")
        layout.addWidget(self.message)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

    def set_progress(self, value: int, message: str) -> None:
        self.message.setText(message)
        self.progress.setValue(max(0, min(100, value)))
        QApplication.processEvents()


class RecordDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list[FieldSpec],
        data: dict | None = None,
        parent: QWidget | None = None,
        *,
        allow_save_new: bool = False,
    ):
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
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)

        hint = QLabel("Required fields are marked with *. Use Tab to move quickly between fields.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        if self._has_property_fields():
            layout.addLayout(self._template_bar())

        buttons = QDialogButtonBox()
        primary_label = "Add" if title.startswith("Add ") else "Save"
        save = buttons.addButton(primary_label, QDialogButtonBox.AcceptRole)
        save.clicked.connect(self.accept)
        if allow_save_new:
            save_new_label = "Add && New" if title.startswith("Add ") else "Save && New"
            save_new = buttons.addButton(save_new_label, QDialogButtonBox.ActionRole)
            save_new.clicked.connect(self.accept_save_new)
        cancel = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 8, 0, 8)
        grid.setHorizontalSpacing(16)
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
            label.setObjectName("RequiredLabel" if spec.required else "FormLabel")
            if spec.kind in {"text", "facilities"}:
                if col_group:
                    row += 1
                    col_group = 0
                label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                grid.addWidget(label, row, 0)
                grid.addWidget(widget, row, 1, 1, 3)
                row += 1
                col_group = 0
                continue

            label_col = 0 if col_group == 0 else 2
            field_col = 1 if col_group == 0 else 3
            grid.addWidget(label, row, label_col)
            grid.addWidget(widget, row, field_col)
            col_group += 1
            if col_group >= 2:
                row += 1
                col_group = 0

        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

    def _has_property_fields(self) -> bool:
        keys = {field.key for field in self.fields}
        return bool({"property_requires", "property_availability", "size", "floor"} & keys)

    def _template_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Quick fill"))
        templates = [
            ("Flat", {"property_requires": "flat", "property_availability": "flat", "size": "double-bed", "floor": "3rd"}),
            ("Shop", {"property_requires": "shop", "property_availability": "shop", "size": "ground floor", "floor": "Ground"}),
            ("House", {"property_requires": "house", "property_availability": "house", "size": "single story", "floor": "Ground"}),
            ("Office", {"property_requires": "office", "property_availability": "office", "size": "any floor", "floor": "1st"}),
            ("Plot", {"property_requires": "plot", "property_availability": "plot", "size": "", "floor": "-"}),
            ("Villa", {"property_requires": "villa", "property_availability": "villa", "size": "double story", "floor": "Ground"}),
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
        if spec.kind == "text":
            widget = QTextEdit()
            widget.setMinimumHeight(82)
            widget.setMaximumHeight(120)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            widget.setPlainText("" if value is None else str(value))
            return widget
        if spec.kind == "facilities":
            return self._make_facilities_widget(spec, value)
        if spec.kind in {"combo", "combo_other", "autocomplete"}:
            widget = QComboBox()
            widget.addItems(spec.options)
            widget.setEditable(spec.kind != "combo")
            if value not in (None, ""):
                idx = widget.findText(str(value))
                if idx < 0:
                    widget.addItem(str(value))
                    idx = widget.findText(str(value))
                if spec.kind == "combo":
                    widget.setCurrentIndex(idx)
                elif idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setEditText(str(value))
            return widget
        if spec.kind == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
            if value:
                widget.setDate(parse_qdate(value))
            else:
                widget.setDate(QDate.currentDate())
            return widget
        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        if spec.numeric:
            widget.setPlaceholderText("0")
        elif is_date_key(spec.key):
            widget.setPlaceholderText("DD/MM/YYYY")
        elif spec.key in PHONE_FORM_KEYS:
            widget.setPlaceholderText("03000000000")
        elif spec.key in EMAIL_FORM_KEYS:
            widget.setPlaceholderText("name@example.com")
        return widget

    def _make_facilities_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("FacilitiesBox")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = spec.options or FACILITY_OPTIONS
        selected = parse_facilities(value, options)
        boxes: list[QRadioButton] = []
        for index, label in enumerate(options):
            checkbox = QRadioButton(label)
            checkbox.setObjectName("FacilityCheck")
            checkbox.setAutoExclusive(False)
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
        if spec.kind == "facilities":
            boxes = getattr(widget, "facility_boxes", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QDateEdit):
            return widget.date().toString(DATE_STORAGE_FORMAT)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def validate(self) -> tuple[bool, str]:
        try:
            for spec in self.fields:
                raw = self.raw_value(spec)
                # For non-editable combos, build the full allowed set from the
                # widget's actual items (which includes any value added from DB).
                widget = self.widgets[spec.key]
                effective_options: list[str] | None = spec.options if spec.options else None
                if spec.kind == "combo" and isinstance(widget, QComboBox):
                    effective_options = [widget.itemText(i) for i in range(widget.count())]
                validate_form_value(
                    spec.key,
                    spec.label,
                    raw,
                    required=spec.required,
                    numeric=spec.numeric,
                    options=effective_options,
                    strict_options=(spec.kind == "combo"),
                )
        except ValueError as exc:
            return False, str(exc)
        return True, ""

    def accept(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required", message)
            return
        self.save_and_new = False
        super().accept()

    def accept_save_new(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required", message)
            return
        self.save_and_new = True
        super().accept()

class MetricCard(QFrame):
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

    def __init__(self, key: str, label: str, abbreviation: str):
        super().__init__()
        self.key = key
        self._checked = False
        self.setObjectName("NavItem")
        self.setProperty("active", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 10, 0)
        layout.setSpacing(10)

        self.indicator = QFrame()
        self.indicator.setObjectName("NavIndicator")
        self.indicator.setProperty("active", False)
        self.indicator.setFixedSize(3, 22)
        layout.addWidget(self.indicator)

        self.icon = QLabel(abbreviation)
        self.icon.setObjectName("NavIcon")
        self.icon.setProperty("active", False)
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setFixedSize(26, 26)
        layout.addWidget(self.icon)

        self.text_label = QLabel(label)
        self.text_label.setObjectName("NavText")
        self.text_label.setProperty("active", False)
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
            widget.setProperty("active", checked)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def isChecked(self) -> bool:
        return self._checked


class DataTablePage(QWidget):
    def __init__(
        self,
        main: "ModernCRMWindow",
        spec: TableSpec,
        *,
        extra_buttons: list[tuple[str, Callable[[], None], str]] | None = None,
    ):
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
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        can_edit = self.main.can_edit(self.spec.permission) and bool(self.spec.form_fields)
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
        columns = [col.key for col in self.spec.columns]
        sql = f"SELECT {', '.join(columns)} FROM {self.spec.table} ORDER BY {self.spec.order_by}"
        self.rows = self.services.fetch_all(sql)
        self.table.setColumnCount(len(self.spec.columns))
        self.table.setHorizontalHeaderLabels([col.label for col in self.spec.columns])
        self.table.setRowCount(len(self.rows))
        has_long_text = any(col.key in LONG_TEXT_COLUMN_KEYS for col in self.spec.columns)
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(self.spec.columns):
                value = row.get(col.key)
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setForeground(QColor("#0f172a"))
                if col.key in LONG_TEXT_COLUMN_KEYS:
                    item.setToolTip(text)
                    item.setText(text.replace("\r\n", " ").replace("\n", " "))
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)
            if has_long_text:
                self.table.setRowHeight(row_idx, 42)
        for idx, col in enumerate(self.spec.columns):
            self.table.setColumnWidth(idx, col.width)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
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
            self.main.after_record_saved(self.spec.table, new_id)
            self.refresh()
            self.main.refresh_dashboard()
            self.main.update_status_bar(f"{self.spec.title} record saved")
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
        assignments = ", ".join(f"{col}=?" for col in cols)
        params = tuple(vals.get(col) for col in cols) + (row["id"],)
        self.services.execute(f"UPDATE {self.spec.table} SET {assignments} WHERE id=?", params)
        self.main.after_record_saved(self.spec.table, row["id"])
        self.refresh()
        self.main.refresh_dashboard()
        self.main.update_status_bar(f"{self.spec.title} record updated")

    def delete_record(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        if not has_permission(self.main.role, "delete"):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to delete records.")
            return
        ids = [row["id"] for row in rows]
        ask = QMessageBox.question(self, "Delete", f"Delete {len(ids)} selected record(s) from {self.spec.table}?")
        if ask != QMessageBox.Yes:
            return
        for row_id in ids:
            self.services.execute(f"DELETE FROM {self.spec.table} WHERE id=?", (row_id,))
        self.refresh()
        self.main.refresh_dashboard()
        self.main.update_status_bar(f"{len(ids)} {self.spec.title.lower()} record(s) deleted")

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
        self.main.update_status_bar(f"{self.spec.title} exported")

    def _apply_defaults(self, vals: dict[str, Any], *, is_new: bool) -> None:
        now = datetime.now()
        if is_new:
            if "created_at" in self.spec.insert_columns:
                vals["created_at"] = now
            if "created_by" in self.spec.insert_columns:
                vals["created_by"] = self.main.current_user.get("username", "")


class DealModule(QWidget):
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

        report_button = QPushButton(f"Generate {self.kind.title()} Report")
        report_button.setObjectName("AccentButton")
        report_button.clicked.connect(lambda: self.main.preview_report(self.kind))
        add_req = QPushButton("New Requirement")
        add_av = QPushButton("New Availability")
        add_req.clicked.connect(lambda: self.requirements.add_record())
        add_av.clicked.connect(lambda: self.availability.add_record())
        top.addWidget(add_req)
        top.addWidget(add_av)
        top.addWidget(report_button)
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
        tabs.addTab(self.requirements, "Requirements")
        tabs.addTab(self.availability, "Availability")
        layout.addWidget(tabs, 1)

    def _deal_buttons(self, page_getter: Callable[[], DataTablePage], table: str) -> list[tuple[str, Callable[[], None], str]]:
        buttons = [
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


class SummaryPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        refresh = QPushButton("Refresh Summary")
        refresh.setObjectName("AccentButton")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("Export")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Financial Summary"))
        controls.addStretch(1)
        controls.addWidget(refresh)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text, 1)
        self.refresh()

    def refresh(self) -> None:
        self.text.setPlainText(self.main.build_financial_text())

    def export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Financial Summary",
            str(OUTPUT_DIR / "financial_summary.txt"),
            "Text Files (*.txt)",
        )
        if path:
            Path(path).write_text(self.text.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")


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


class AttendancePage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat(DATE_DISPLAY_FORMAT)
        load = QPushButton("Load")
        load.clicked.connect(self.refresh)
        present = QPushButton("Mark Present")
        present.setObjectName("AccentButton")
        present.clicked.connect(lambda: self.mark("Present"))
        absent = QPushButton("Mark Absent")
        absent.setObjectName("DangerButton")
        absent.clicked.connect(lambda: self.mark("Absent"))
        leave = QPushButton("Mark Leave")
        leave.clicked.connect(lambda: self.mark("Leave"))
        controls.addWidget(QLabel("Date"))
        controls.addWidget(self.date)
        controls.addWidget(load)
        controls.addStretch(1)
        controls.addWidget(present)
        controls.addWidget(absent)
        controls.addWidget(leave)
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

    def refresh(self) -> None:
        date = self.date.date().toString(DATE_STORAGE_FORMAT)
        marked = self.main.services.fetch_all(
            """SELECT a.id, e.id AS employee_id, e.full_name, a.date, a.status, a.notes
               FROM attendance a JOIN employees e ON a.employee_id=e.id
               WHERE a.date=? ORDER BY e.full_name""",
            (date,),
        )
        if marked:
            self.rows = marked
        else:
            self.rows = [
                {"id": None, "employee_id": row["id"], "full_name": row["full_name"], "date": date, "status": "Not Marked", "notes": ""}
                for row in self.main.services.fetch_all("SELECT id, full_name FROM employees WHERE status='Active' ORDER BY full_name")
            ]
        headers = ["ID", "Employee", "Date", "Status", "Notes"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            values = [
                row.get("id") or "",
                row.get("full_name") or "",
                format_date_display(row.get("date")),
                row.get("status") or "",
                row.get("notes") or "",
            ]
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

    def mark(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more employee rows first.")
            return
        date = self.date.date().toString(DATE_STORAGE_FORMAT)
        for row in rows:
            existing = self.main.services.fetch_one(
                "SELECT id FROM attendance WHERE employee_id=? AND date=?",
                (row["employee_id"], date),
            )
            if existing:
                self.main.services.execute(
                    "UPDATE attendance SET status=? WHERE employee_id=? AND date=?",
                    (status, row["employee_id"], date),
                )
            else:
                self.main.services.execute(
                    "INSERT INTO attendance (employee_id, date, status) VALUES (?,?,?)",
                    (row["employee_id"], date, status),
                )
        self.refresh()


class SalaryPage(DataTablePage):
    def __init__(self, main: "ModernCRMWindow", spec: TableSpec):
        super().__init__(
            main,
            spec,
            extra_buttons=[("Pay Salary", self.pay_salary, "AccentButton")],
        )

    def refresh(self) -> None:
        self.rows = self.main.services.fetch_all(
            """SELECT sp.id, e.full_name, sp.month, sp.year, sp.base_salary, sp.bonus,
                      sp.deductions, sp.net_salary, sp.payment_method
               FROM salary_payments sp JOIN employees e ON sp.employee_id=e.id
               ORDER BY sp.id DESC"""
        )
        columns = self.spec.columns
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c.label for c in columns])
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            for c, col in enumerate(columns):
                value = row.get(col.key)
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.update_selection_label()

    def pay_salary(self) -> None:
        employees = self.main.services.fetch_all("SELECT id, full_name, base_salary FROM employees WHERE status='Active' ORDER BY full_name")
        if not employees:
            QMessageBox.information(self, "No Employees", "No active employees found.")
            return
        names = [f"{e['full_name']} (Base: {money(e['base_salary'], self.main.currency_symbol)})" for e in employees]
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
        employee = self.main.services.fetch_one("SELECT id FROM employees WHERE full_name=?", (employee_name,))
        if not employee:
            QMessageBox.warning(self, "Employee", "Employee not found.")
            return
        base = safe_float(vals["base_salary"])
        bonus = safe_float(vals["bonus"])
        deductions = safe_float(vals["deductions"])
        net = safe_float(vals["net_salary"]) or (base + bonus - deductions)
        self.main.services.execute(
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


class EmployeesModule(QWidget):
    def __init__(self, main: "ModernCRMWindow", employee_spec: TableSpec, salary_spec: TableSpec):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Employees")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        tabs = QTabWidget()
        self.employees = DataTablePage(main, employee_spec)
        self.attendance = AttendancePage(main)
        self.salary = SalaryPage(main, salary_spec)
        tabs.addTab(self.employees, "Employees")
        tabs.addTab(self.attendance, "Attendance")
        tabs.addTab(self.salary, "Salary History")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.employees.refresh()
        self.attendance.refresh()
        self.salary.refresh()


class ReportsModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.last_report: ReportResult | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Reports")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        quick = QHBoxLayout()
        rent_btn = QPushButton("Rent Report")
        sale_btn = QPushButton("Sale Report")
        both_btn = QPushButton("Combined Report")
        rent_btn.setObjectName("AccentButton")
        rent_btn.clicked.connect(lambda: self.generate("rent"))
        sale_btn.clicked.connect(lambda: self.generate("sale"))
        both_btn.clicked.connect(lambda: self.generate("rent + sale"))
        quick.addWidget(rent_btn)
        quick.addWidget(sale_btn)
        quick.addWidget(both_btn)
        quick.addStretch(1)
        layout.addLayout(quick)

        controls = QHBoxLayout()
        self.report_type = QComboBox()
        self.report_type.addItems(["Rent", "Sale", "Rent + Sale", "Financial", "Properties", "Clients", "Employees", "Attendance"])
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit(QDate.currentDate())
        for date_edit in (self.start_date, self.end_date):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(DATE_DISPLAY_FORMAT)
        generate = QPushButton("Generate")
        generate.setObjectName("AccentButton")
        generate.clicked.connect(self.generate)
        export = QPushButton("Export")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Report"))
        controls.addWidget(self.report_type)
        controls.addWidget(QLabel("From"))
        controls.addWidget(self.start_date)
        controls.addWidget(QLabel("To"))
        controls.addWidget(self.end_date)
        controls.addStretch(1)
        controls.addWidget(generate)
        controls.addWidget(export)
        layout.addLayout(controls)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        layout.addWidget(self.preview, 1)

    def generate(self, report_type: str | None = None) -> None:
        kind = (report_type or self.report_type.currentText()).lower()
        start = self.start_date.date().toString(DATE_STORAGE_FORMAT)
        end = self.end_date.date().toString(DATE_STORAGE_FORMAT)
        svc = self.main.report_service
        try:
            if kind == "rent":
                result = svc.rent_report(start, end)
            elif kind == "sale":
                result = svc.sale_report(start, end)
            elif kind == "rent + sale":
                result = svc.dealings_report(start, end)
            elif kind == "financial":
                result = ReportResult("Financial Summary", self.main.financial_text(start, end), filename_slug="financial_summary")
            elif kind == "properties":
                result = ReportResult("Property Report", self.main.generic_report("properties", "PROPERTY REPORT"), filename_slug="property_report")
            elif kind == "clients":
                result = ReportResult("Client Report", self.main.generic_report("clients", "CLIENT REPORT"), filename_slug="client_report")
            elif kind == "employees":
                result = ReportResult("Employee Report", self.main.generic_report("employees", "EMPLOYEE REPORT"), filename_slug="employee_report")
            else:
                result = ReportResult("Attendance Report", self.main.attendance_report(), filename_slug="attendance_report")
        except Exception as exc:
            QMessageBox.warning(self, "Report Error", f"Could not generate report:\n{exc}")
            self.main.update_status_bar("Report generation failed")
            return
        self.last_report = result
        self.main.last_report = result
        self.preview.setPlainText(result.text)
        self.main.update_status_bar(f"{result.title} generated")

    def export(self) -> None:
        if not self.last_report:
            QMessageBox.information(self, "Report", "Generate a report first.")
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            str(OUTPUT_DIR / f"{self.last_report.filename_slug}.pdf"),
            "PDF Files (*.pdf);;CSV Files (*.csv);;Text Files (*.txt)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        try:
            if suffix == ".csv" or "CSV" in selected_filter:
                path = str(Path(path).with_suffix(".csv"))
                export_report_csv(self.last_report, path)
            elif suffix == ".txt" or "Text" in selected_filter:
                path = str(Path(path).with_suffix(".txt"))
                export_report_text(self.last_report, path)
            else:
                path = str(Path(path).with_suffix(".pdf"))
                export_report_pdf(self.last_report, path)
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", f"Could not export report:\n{exc}")
            return
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")


class AIInsightsModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.last_text = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("AI Insights")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.status = QLabel(self._status_text())
        self.status.setObjectName("MutedText")
        refresh = QPushButton("Refresh AI")
        refresh.setObjectName("AccentButton")
        refresh.clicked.connect(self.refresh)
        copy = QPushButton("Copy")
        copy.clicked.connect(self.copy_report)
        export = QPushButton("Export TXT")
        export.clicked.connect(self.export_report)
        controls.addWidget(self.status)
        controls.addStretch(1)
        controls.addWidget(refresh)
        controls.addWidget(copy)
        controls.addWidget(export)
        layout.addLayout(controls)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        layout.addWidget(self.preview, 1)
        self.refresh()

    def _status_text(self) -> str:
        if AI_LIBS_AVAILABLE:
            return "Local AI: pandas + numpy, NLP matching, regression, MLP-style lead scoring"
        return "AI libraries missing: install pandas and numpy"

    def refresh(self) -> None:
        self.main.reload_settings()
        self.last_text = self.main.intelligence_service.generate_report()
        self.preview.setPlainText(self.last_text)
        self.status.setText(self._status_text())

    def copy_report(self) -> None:
        if not self.last_text:
            self.refresh()
        QApplication.clipboard().setText(self.last_text)
        QMessageBox.information(self, "Copied", "AI insights copied to clipboard.")

    def export_report(self) -> None:
        if not self.last_text:
            self.refresh()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export AI Insights",
            str(OUTPUT_DIR / f"ai_insights_{datetime.now().strftime('%Y%m%d')}.txt"),
            "Text Files (*.txt)",
        )
        if not path:
            return
        Path(path).write_text(self.last_text, encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")


class ReportPreviewDialog(QDialog):
    def __init__(self, result: ReportResult, parent: QWidget | None = None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle(result.title)
        self.resize(980, 680)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel(result.title)
        title.setObjectName("DialogTitle")
        header.addWidget(title)
        header.addStretch(1)
        pdf = QPushButton("Export PDF")
        csv_btn = QPushButton("Export CSV")
        txt = QPushButton("Export TXT")
        pdf.setObjectName("AccentButton")
        pdf.clicked.connect(lambda: self.export("pdf"))
        csv_btn.clicked.connect(lambda: self.export("csv"))
        txt.clicked.connect(lambda: self.export("txt"))
        header.addWidget(pdf)
        header.addWidget(csv_btn)
        header.addWidget(txt)
        layout.addLayout(header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 9))
        self.preview.setPlainText(result.text)
        layout.addWidget(self.preview, 1)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def export(self, kind: str) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filters = {
            "pdf": "PDF Files (*.pdf)",
            "csv": "CSV Files (*.csv)",
            "txt": "Text Files (*.txt)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            str(OUTPUT_DIR / f"{self.result.filename_slug}.{kind}"),
            filters[kind],
        )
        if not path:
            return
        path = str(Path(path).with_suffix(f".{kind}"))
        try:
            if kind == "pdf":
                export_report_pdf(self.result, path)
            elif kind == "csv":
                export_report_csv(self.result, path)
            else:
                export_report_text(self.result, path)
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", f"Could not export report:\n{exc}")
            return
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")


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
        if not vals.get("username") or not vals.get("full_name"):
            QMessageBox.warning(self, "User", "Username and full name are required.")
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


class SettingsModule(QWidget):
    KEYS = [
        ("Company Name", "company_name"),
        ("Company Address", "company_address"),
        ("Company Phone", "company_phone"),
        ("Company Email", "company_email"),
        ("Currency Symbol", "currency_symbol"),
        ("Default Commission %", "default_commission"),
        ("Tax Rate %", "tax_rate"),
        ("Bank Account", "bank_account"),
    ]

    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.inputs: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        form_frame = QFrame()
        form_frame.setObjectName("Panel")
        form = QFormLayout(form_frame)
        for label, key in self.KEYS:
            edit = QLineEdit(main.services.settings_get(key))
            self.inputs[key] = edit
            form.addRow(label, edit)
        layout.addWidget(form_frame)
        buttons = QHBoxLayout()
        save = QPushButton("Save Settings")
        save.setObjectName("AccentButton")
        save.clicked.connect(self.save)
        change = QPushButton("Change My Password")
        change.clicked.connect(self.change_password)
        buttons.addWidget(save)
        buttons.addWidget(change)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def save(self) -> None:
        for key, widget in self.inputs.items():
            self.main.services.settings_set(key, widget.text().strip())
        self.main.reload_settings()
        QMessageBox.information(self, "Settings", "Settings saved.")

    def change_password(self) -> None:
        fields = [
            FieldSpec("Current Password *", "old_password", required=True),
            FieldSpec("New Password *", "new_password", required=True),
        ]
        dialog = RecordDialog("Change Password", fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        vals = dialog.values()
        ok, message = self.main.services.change_password(self.main.current_user["id"], vals["old_password"], vals["new_password"])
        QMessageBox.information(self, "Password" if ok else "Password Error", message)


class SearchDialog(QDialog):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__(main)
        self.main = main
        self.rows: list[dict] = []
        self.display_columns: list[str] = []
        self.display_column_labels: dict[str, str] = {}
        self.table_column_cache: dict[str, list[str]] = {}
        self.available_sources = self.main.find_sources()
        self.setWindowTitle("Find")
        self.resize(1180, 640)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Sort"))
        self.source_filter = QComboBox()
        self.source_filter.addItem("All", "")
        for label, table in self.available_sources:
            self.source_filter.addItem(label, table)
        self.source_filter.currentIndexChanged.connect(lambda _index: self.search() if self.query.text().strip() else None)
        bar.addWidget(self.source_filter)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Find by name, contact, property, location, budget, facilities, or remarks...")
        button = QPushButton("Find")
        button.setObjectName("AccentButton")
        button.clicked.connect(self.search)
        bar.addWidget(self.query, 1)
        bar.addWidget(button)
        layout.addLayout(bar)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected")
        self.selection_label.setObjectName("SelectionCount")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        copy = QPushButton("Copy Selected")
        copy.clicked.connect(self.copy_selected_rows)
        print_voucher = QPushButton("Print Voucher")
        print_voucher.setObjectName("AccentButton")
        print_voucher.clicked.connect(self.print_voucher)
        save_pdf = QPushButton("Save Voucher PDF")
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
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.table, 1)
        self.query.returnPressed.connect(self.search)

    def search_sources(self) -> list[tuple[str, str]]:
        selected_table = self.source_filter.currentData()
        if selected_table:
            if any(table == selected_table for _label, table in self.available_sources):
                return [(self.source_label(selected_table), selected_table)]
            return []
        return list(self.available_sources)

    def table_columns(self, table: str) -> list[str]:
        if table not in self.table_column_cache:
            rows = self.main.services.fetch_all(f"PRAGMA table_info({table})")
            self.table_column_cache[table] = [
                row["name"]
                for row in rows
                if row.get("name") not in GLOBAL_SEARCH_HIDDEN_COLUMNS
            ]
        return self.table_column_cache[table]

    def source_label(self, table: str) -> str:
        return GLOBAL_SEARCH_SOURCE_LABELS.get(table, table.replace("_", " ").title())

    def field_label(self, key: str) -> str:
        if key in self.display_column_labels:
            return self.display_column_labels[key]
        if key == "_source":
            return "Type"
        if key == "_table":
            return "Table"
        return {
            "id": "Sr No.",
            "client_name": "Name",
            "contact": "Contact No.",
            "property_requires": "Property Requirement",
            "sq_ft": "Sq Ft",
            "sq_ft_yards": "Sq Ft / Yards",
            "cnic": "CNIC",
        }.get(key, key.replace("_", " ").title())

    def display_value(self, key: str, value: Any) -> str:
        if value in (None, ""):
            return ""
        if is_date_key(key):
            return format_date_display(value)
        if key in GLOBAL_SEARCH_MONEY_COLUMNS and is_valid_number_text(value):
            return money(value, self.main.currency_symbol)
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)

    def result_value(self, row: dict, aliases: tuple[str, ...], default: Any = "") -> Any:
        for key in aliases:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return default

    def normalize_search_row(self, source: str, table: str, row: dict) -> dict:
        normalized = {"_source": source, "_table": table, "_raw": row, "id": row.get("id")}
        columns = ["_source"]
        for key, _label, aliases, default in FIND_RESULT_COLUMNS.get(table, []):
            normalized[key] = self.result_value(row, aliases, default)
            if key not in columns:
                columns.append(key)
        normalized["_columns"] = columns
        return normalized

    def display_schema(self, rows: list[dict]) -> tuple[list[str], dict[str, str]]:
        selected_table = self.source_filter.currentData()
        if selected_table:
            specs = FIND_RESULT_COLUMNS.get(selected_table, [])
            return [key for key, _label, _aliases, _default in specs], {
                key: label for key, label, _aliases, _default in specs
            }

        present: set[str] = set()
        for row in rows:
            present.update(row.get("_columns", []))
        columns = [key for key in FIND_ALL_COLUMN_ORDER if key in present]
        labels = {key: FIND_ALL_COLUMN_LABELS.get(key, self.field_label(key)) for key in columns}
        return columns, labels

    def search(self) -> None:
        term = self.query.text().strip().lower()
        if not term:
            return
        results: list[dict] = []
        for source, table in self.search_sources():
            columns = self.table_columns(table)
            if not columns:
                continue
            source_text = f"{source} {table.replace('_', ' ')}".lower()
            if term in source_text:
                sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50"
                params: tuple[Any, ...] = ()
            else:
                where = " OR ".join(f"LOWER(CAST(COALESCE(\"{col}\", '') AS TEXT)) LIKE ?" for col in columns)
                sql = f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 50"
                params = tuple([f"%{term}%"] * len(columns))
            for row in self.main.services.fetch_all(sql, params):
                results.append(self.normalize_search_row(source, table, row))
        results.sort(
            key=lambda row: (
                FIND_SOURCE_ORDER.get(str(row.get("_table") or ""), 99),
                -safe_int(row.get("id")),
            )
        )
        self.rows = results
        self.display_columns, self.display_column_labels = self.display_schema(results)
        headers = [self.field_label(key) for key in self.display_columns]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(results))
        for r, row in enumerate(results):
            for c, key in enumerate(self.display_columns):
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
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected")

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more search results first.")
            return
        if self.display_columns:
            keys = self.display_columns
        else:
            keys, labels = self.display_schema(rows)
            self.display_column_labels.update(labels)
        lines = ["\t".join(self.field_label(key) for key in keys)]
        for row in rows:
            lines.append("\t".join(self.display_value(key, row.get(key)) for key in keys))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"{len(rows)} selected result(s) copied to clipboard.")

    def voucher_rows(self) -> list[dict]:
        rows = self.selected_rows()
        if rows:
            return rows
        if self.rows:
            return self.rows
        QMessageBox.information(self, "Find", "Find records first, then print or save the voucher.")
        return []

    def voucher_html(self, rows: list[dict]) -> str:
        query = html.escape(self.query.text().strip() or "All visible results")
        generated_at = datetime.now().strftime(PY_DATE_DISPLAY_FORMAT + " %I:%M %p")
        user_name = html.escape(self.main.current_user.get("full_name") or self.main.current_user.get("username") or "")
        company = html.escape(self.main.company_name)
        body_parts = [
            "<html><head><style>",
            """
            @page { size: legal landscape; margin: 7mm; }
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; color: #111827; margin: 0; font-size: 9.5pt; }
            .voucher { border: 2px solid #111827; padding: 12px; margin: 0 0 10px 0; page-break-inside: avoid; page-break-after: always; width: 100%; }
            .voucher:last-of-type { page-break-after: auto; }
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
            source = html.escape(str(row.get("_source") or self.source_label(str(row.get("_table") or ""))))
            record_id = html.escape(str(row.get("id") or ""))
            status = html.escape(str(row.get("approval_status") or row.get("status") or row.get("workflow_stage") or ""))
            body_parts.append("<div class='voucher'>")
            body_parts.append(
                f"<div class='top'><div class='brand'><h1>{company}</h1>"
                f"<p>Find Voucher</p></div>"
                f"<div class='stamp'><strong>{source}</strong>Voucher #{index:03d}<br>{generated_at}</div></div>"
            )
            body_parts.append("<table class='summary'>")
            body_parts.append(
                f"<tr><td class='label'>Search</td><td>{query}</td>"
                f"<td class='label'>Record ID</td><td>{record_id}</td></tr>"
                f"<tr><td class='label'>Printed By</td><td>{user_name}</td>"
                f"<td class='label'>Status</td><td>{status or '-'}</td></tr>"
            )
            body_parts.append("</table>")
            body_parts.append("<table class='fields'><tr><th>Field</th><th>Value</th><th>Field</th><th>Value</th></tr>")
            columns = [col for col in row.get("_columns", []) if col not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
            if "_source" not in columns:
                columns = ["_source"] + columns
            cells: list[tuple[str, str]] = []
            for key in columns:
                value = row.get(key)
                display = self.display_value(key, value) or "-"
                cells.append((self.field_label(key), display))
            for offset in range(0, len(cells), 2):
                left = cells[offset]
                right = cells[offset + 1] if offset + 1 < len(cells) else ("", "")
                body_parts.append(
                    "<tr>"
                    f"<td class='field-name'>{html.escape(left[0])}</td><td>{html.escape(left[1])}</td>"
                    f"<td class='field-name'>{html.escape(right[0])}</td><td>{html.escape(right[1])}</td>"
                    "</tr>"
                )
            body_parts.append("</table>")
            body_parts.append("<div class='footer'>Generated from Real Estate CRM find. Verify record before deal finalization.</div>")
            body_parts.append("</div>")
        body_parts.append("</body></html>")
        return "".join(body_parts)

    def print_voucher(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Find Voucher")
        if dialog.exec() == QDialog.Accepted:
            doc.print_(printer)

    def save_voucher_pdf(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        default_name = f"find_voucher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Find Voucher PDF",
            str(OUTPUT_DIR / default_name),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc.print_(printer)
        QMessageBox.information(self, "Saved", f"Voucher PDF saved:\n{path}")


class ModernCRMWindow(QMainWindow):
    def __init__(
        self,
        services: CRMServices,
        current_user: dict,
        startup_progress: Callable[[int, str], None] | None = None,
    ):
        super().__init__()
        self.services = services
        self.current_user = current_user
        self._startup_progress = startup_progress
        self.role = current_user.get("role", "Staff")
        self.pages: dict[str, QWidget] = {}
        self.last_report: ReportResult | None = None
        self._api_server: ThreadingHTTPServer | None = None
        self._lan_web_server: Any | None = None
        self._lan_web_thread: threading.Thread | None = None
        self._lan_web_owns_server = False
        self._lan_web_status = "Starting"
        self._lan_web_warning_shown = False
        self.local_ip = self.get_local_ip()
        self.local_service_url = f"http://{self.local_ip}:{LOCAL_SERVICE_PORT}"
        self.browser_service_url = f"http://{self.local_ip}:{LAN_WEB_PORT}"
        self._report_startup(55, "Reading company settings")
        self.reload_settings()
        self.setWindowTitle(f"Real Estate CRM - {current_user.get('full_name') or current_user.get('username')} ({self.role})")
        self.setWindowIcon(crm_app_icon())
        self.resize(1360, 840)
        self.setMinimumSize(1000, 660)
        self._report_startup(62, "Preparing CRM tables")
        self._build_specs()
        self._report_startup(68, "Building workspace")
        self._build_ui()
        self._report_startup(88, "Starting desktop API")
        self.start_local_service()
        self._report_startup(90, "Starting browser server")
        self.start_browser_server()
        self._report_startup(94, "Syncing clients")
        synced_contacts = self.sync_all_deal_contacts()
        self._report_startup(96, "Refreshing dashboard")
        self.refresh_dashboard()
        self.update_status_bar(f"CRM data refreshed; synced {synced_contacts} deal records")

    def _report_startup(self, value: int, message: str) -> None:
        if self._startup_progress:
            self._startup_progress(value, message)

    def reload_settings(self) -> None:
        self.company_name = self.services.settings_get("company_name", "Real Estate Management")
        self.currency_symbol = self.services.settings_get("currency_symbol", "Rs.")
        self.report_service = ReportService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)

    def _build_specs(self) -> None:
        m = lambda value, symbol: money(value, symbol)
        d = lambda value, _symbol: format_date_display(value)
        self.specs = {
            "rent_req": TableSpec(
                "Rent Requirements",
                "rent_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Requirement", width=160),
                    ColumnSpec("size", "Size", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget"),
                deal_insert_columns("client_name", "property_requires", "budget"),
                deal_update_columns("client_name", "property_requires", "budget"),
                permission="rent",
                deal_table=True,
            ),
            "rent_av": TableSpec(
                "Rent Availability",
                "rent_availability",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Availability", width=160),
                    ColumnSpec("size", "Size", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("monthly_rent", "Rent", m, 115), ColumnSpec("deposit", "Deposit", m, 115),
                    ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "monthly_rent"),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                owner_broker_availability_update_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                deal_table=True,
            ),
            "sale_req": TableSpec(
                "Sale Requirements",
                "sale_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Requirement", width=160),
                    ColumnSpec("size", "Size", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget"),
                deal_insert_columns("client_name", "property_requires", "budget"),
                deal_update_columns("client_name", "property_requires", "budget"),
                permission="sale",
                deal_table=True,
            ),
            "sale_av": TableSpec(
                "Sale Availability",
                "sale_availability",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Availability", width=160),
                    ColumnSpec("size", "Size", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("demand", "Demand", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "demand"),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "demand"),
                owner_broker_availability_update_columns("owner_name", "property_availability", "demand"),
                permission="sale",
                deal_table=True,
            ),
            "properties": property_spec(),
            "clients": client_spec(),
            "income": income_spec(),
            "expenses": expense_spec(),
            "employees": employee_spec(),
            "salary": salary_spec(),
        }

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(286)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 18, 18, 18)
        side.setSpacing(14)

        brand_card = QFrame()
        brand_card.setObjectName("BrandCard")
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(12, 12, 12, 12)
        brand_layout.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("LogoImage")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(58, 58)
        logo_pixmap = QPixmap(str(crm_logo_path()))
        if logo_pixmap.isNull():
            logo.setObjectName("LogoBadge")
            logo.setText("RE")
        else:
            logo.setPixmap(
                logo_pixmap.scaled(
                    58,
                    58,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        brand_layout.addWidget(logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand = QLabel("Real Estate CRM")
        brand.setObjectName("Brand")
        brand_subtitle = QLabel("Property operations")
        brand_subtitle.setObjectName("SidebarSubtle")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_subtitle)
        brand_layout.addLayout(brand_text, 1)
        side.addWidget(brand_card)

        user_card = QFrame()
        user_card.setObjectName("UserCard")
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(14, 12, 14, 12)
        user_layout.setSpacing(4)
        user_name = QLabel(str(self.current_user.get("full_name") or self.current_user.get("username") or "User"))
        user_name.setObjectName("SidebarUserName")
        user_role = QLabel(str(self.role))
        user_role.setObjectName("RolePill")
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_role, alignment=Qt.AlignLeft)
        side.addWidget(user_card)

        nav_shell = QFrame()
        nav_shell.setObjectName("NavShell")
        nav_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.nav_shell = nav_shell
        self.nav_layout = QVBoxLayout(nav_shell)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        self.nav_buttons: dict[str, NavItem] = {}
        self.nav_keys: list[str] = []
        self._nav_section_count = 0

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("SidebarNavScroll")
        self.nav_scroll = nav_scroll
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        nav_scroll.setWidget(nav_shell)
        side.addWidget(nav_scroll, 1)

        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 12, 12, 12)
        footer_layout.setSpacing(8)
        status_row = QHBoxLayout()
        dot = QLabel("")
        dot.setObjectName("StatusDot")
        status_row.addWidget(dot)
        api_status = QLabel("Browser server starting")
        api_status.setObjectName("SidebarStatusText")
        self.sidebar_server_status = api_status
        status_row.addWidget(api_status)
        status_row.addStretch(1)
        footer_layout.addLayout(status_row)
        api_label = QLabel(self.browser_service_url)
        api_label.setObjectName("SidebarSubtle")
        api_label.setWordWrap(True)
        self.sidebar_server_url_label = api_label
        footer_layout.addWidget(api_label)
        logout = QPushButton("Logout")
        logout.setObjectName("SidebarLogout")
        logout.clicked.connect(self.logout)
        footer_layout.addWidget(logout)
        side.addWidget(footer)
        outer.addWidget(sidebar)

        content = QFrame()
        content.setObjectName("Content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(14)

        top = QHBoxLayout()
        self.page_title = QLabel(self.company_name)
        self.page_title.setObjectName("TopTitle")
        search = QPushButton("Find")
        search.clicked.connect(self.open_search)
        refresh = QPushButton("Refresh")
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
        self._build_status_bar()
        self.setStyleSheet(APP_STYLE)
        self.update_status_bar("Ready")

    def _build_menu(self) -> None:
        self.menuBar().clear()
        self._menus: list[Any] = []

        def menu(label: str) -> Any:
            created = self.menuBar().addMenu(label)
            self._menus.append(created)
            return created

        def action(label: str, slot: Callable, shortcut: str | None = None, tip: str | None = None) -> QAction:
            act = QAction(label, self)
            if shortcut:
                act.setShortcut(shortcut)
            if tip:
                act.setStatusTip(tip)
            act.triggered.connect(lambda _checked=False, callback=slot: callback())
            return act

        def add_page_action(menu: Any, key: str, shortcut: str | None = None) -> None:
            button = self.nav_buttons.get(key)
            if not button:
                return
            label = button.text_label.text()
            menu.addAction(action(label, lambda page_key=key: self.switch_page(page_key), shortcut, f"Open {label}"))

        def add_deal_action(menu: Any, label: str, page_key: str, side: str, shortcut: str | None = None) -> None:
            module = self.pages.get(page_key)
            if not isinstance(module, DealModule):
                return
            spec = module.requirement_spec if side == "requirements" else module.availability_spec
            if self.can_edit(spec.permission):
                menu.addAction(
                    action(
                        label,
                        lambda key=page_key, tab=side: self.add_deal_record(key, tab),
                        shortcut,
                        f"Create {label.lower()}",
                    )
                )

        def add_record_action(menu: Any, label: str, page_key: str, shortcut: str | None = None) -> None:
            page = self.pages.get(page_key)
            if isinstance(page, DataTablePage) and self.can_edit(page.spec.permission):
                menu.addAction(
                    action(
                        label,
                        lambda key=page_key: self.add_table_record(key),
                        shortcut,
                        f"Create {label.lower()}",
                    )
                )

        file_menu = menu("File")
        new_menu = file_menu.addMenu("New")
        self._menus.append(new_menu)
        add_deal_action(new_menu, "Rent Requirement", "rent", "requirements", "Ctrl+N")
        add_deal_action(new_menu, "Rent Availability", "rent", "availability", "Ctrl+Shift+N")
        add_deal_action(new_menu, "Sale Requirement", "sale", "requirements", "Ctrl+Alt+N")
        add_deal_action(new_menu, "Sale Availability", "sale", "availability", "Ctrl+Alt+A")
        new_menu.addSeparator()
        add_record_action(new_menu, "Property", "properties", "Ctrl+Shift+P")
        add_record_action(new_menu, "Client", "clients", "Ctrl+Shift+C")
        file_menu.addSeparator()
        file_menu.addAction(action("Export All Tables", self.export_all_tables, "Ctrl+E", "Export every CRM table to CSV files"))
        file_menu.addAction(action("Backup Database", self.backup_database, "Ctrl+B", "Create a SQLite database backup"))
        file_menu.addSeparator()
        file_menu.addAction(action("Restart", self.restart_app, "Ctrl+Shift+R", "Restart the CRM"))
        file_menu.addAction(action("Logout", self.logout, "Ctrl+L", "Return to login"))
        file_menu.addAction(action("Exit", self.close, "Ctrl+Q", "Close the CRM"))

        view_menu = menu("View")
        for index, key in enumerate(self.nav_keys[:9], start=1):
            add_page_action(view_menu, key, f"Ctrl+{index}")
        if len(self.nav_keys) > 9:
            add_page_action(view_menu, self.nav_keys[9], "Ctrl+0")
        view_menu.addSeparator()
        view_menu.addAction(action("Full Screen", self.showFullScreen, "F11", "Switch to full screen"))
        view_menu.addAction(action("Exit Full Screen", self.showNormal, "Shift+F11", "Exit full screen"))

        dealings_menu = menu("Dealings")
        add_page_action(dealings_menu, "rent")
        add_page_action(dealings_menu, "sale")
        dealings_menu.addSeparator()
        add_deal_action(dealings_menu, "Rent Requirement", "rent", "requirements", "Alt+R")
        add_deal_action(dealings_menu, "Rent Availability", "rent", "availability", "Alt+A")
        add_deal_action(dealings_menu, "Sale Requirement", "sale", "requirements", "Alt+S")
        add_deal_action(dealings_menu, "Sale Availability", "sale", "availability", "Alt+Shift+S")

        records_menu = menu("Records")
        for key in ("properties", "clients", "financials", "employees", "users", "settings"):
            add_page_action(records_menu, key)

        reports_menu = menu("Reports")
        reports_menu.addAction(action("Rent Report", lambda: self.preview_named_report("rent"), "Ctrl+Shift+1", "Preview rent report"))
        reports_menu.addAction(action("Sale Report", lambda: self.preview_named_report("sale"), "Ctrl+Shift+2", "Preview sale report"))
        reports_menu.addAction(action("Combined Report", lambda: self.preview_named_report("both"), "Ctrl+Shift+3", "Preview combined report"))
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            reports_menu.addAction(action("Financial Summary", lambda: self.preview_named_report("financial"), "Ctrl+Shift+4", "Preview financial summary"))
        reports_menu.addSeparator()
        for report_key, label in (
            ("properties", "Property Report"),
            ("clients", "Client Report"),
        ):
            reports_menu.addAction(action(label, lambda key=report_key: self.preview_named_report(key), None, f"Preview {label.lower()}"))
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            reports_menu.addAction(action("Employee Report", lambda: self.preview_named_report("employees"), None, "Preview employee report"))
            reports_menu.addAction(action("Attendance Report", lambda: self.preview_named_report("attendance"), None, "Preview attendance report"))

        tools_menu = menu("Tools")
        tools_menu.addAction(action("Find", self.open_search, "Ctrl+F", "Find records across rent and sale dealings"))
        tools_menu.addAction(action("Refresh", self.refresh_all_pages, "F5", "Reload CRM data"))
        tools_menu.addAction(action("Server Health", self.show_api_health, "Ctrl+H", "Show LAN browser server details"))

        help_menu = menu("Help")
        help_menu.addAction(action("User Guide", self.show_user_guide, "F1", "Open the user guide"))
        help_menu.addAction(action("Roles && Permissions", self.show_roles_info, None, "Show role permissions"))
        help_menu.addAction(action("Developer Info", self.show_developer_info, None, "Show developer information"))
        help_menu.addAction(action("About", self.show_about, None, "About this CRM"))

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setObjectName("AppStatusBar")
        bar.setSizeGripEnabled(True)
        self.status_page_label = QLabel()
        self.status_user_label = QLabel()
        self.status_counts_label = QLabel()
        self.status_db_label = QLabel()
        self.status_api_label = QLabel()
        for label in (
            self.status_page_label,
            self.status_user_label,
            self.status_counts_label,
            self.status_db_label,
            self.status_api_label,
        ):
            label.setObjectName("StatusBarLabel")
        bar.addPermanentWidget(self.status_page_label)
        bar.addPermanentWidget(self.status_user_label)
        bar.addPermanentWidget(self.status_counts_label, 1)
        bar.addPermanentWidget(self.status_db_label)
        bar.addPermanentWidget(self.status_api_label)

    def update_status_bar(self, message: str | None = None) -> None:
        if message:
            self.statusBar().showMessage(message, 4500)
        if not hasattr(self, "status_page_label"):
            return
        current = self.stack.currentWidget() if hasattr(self, "stack") else None
        current_key = next((key for key, widget in self.pages.items() if widget is current), "")
        current_label = self.nav_buttons[current_key].text_label.text() if current_key in self.nav_buttons else "Ready"
        self.status_page_label.setText(f"Page: {current_label}")
        username = self.current_user.get("full_name") or self.current_user.get("username") or "User"
        self.status_user_label.setText(f"User: {username} ({self.role})")
        try:
            counts = [
                f"Rent Req: {self.count('rent_requirements')}",
                f"Rent Av: {self.count('rent_availability')}",
                f"Sale Req: {self.count('sale_requirements')}",
                f"Sale Av: {self.count('sale_availability')}",
            ]
            self.status_counts_label.setText(" | ".join(counts))
        except Exception:
            self.status_counts_label.setText("Counts unavailable")
        try:
            size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
            self.status_db_label.setText(f"DB: {size_mb:.1f} MB")
        except Exception:
            self.status_db_label.setText("DB: -")
        self.status_api_label.setText(f"Web: {self.local_ip}:{LAN_WEB_PORT}")

    def add_deal_record(self, page_key: str, side: str) -> None:
        module = self.pages.get(page_key)
        if not isinstance(module, DealModule):
            QMessageBox.information(self, "Unavailable", "That dealings page is not available for this user.")
            return
        self.switch_page(page_key)
        table_page = module.requirements if side == "requirements" else module.availability
        if not self.can_edit(table_page.spec.permission):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to add this record.")
            return
        table_page.add_record()
        self.update_status_bar(f"{table_page.spec.title} ready")

    def add_table_record(self, page_key: str) -> None:
        page = self.pages.get(page_key)
        if not isinstance(page, DataTablePage):
            QMessageBox.information(self, "Unavailable", "That record page is not available.")
            return
        if not self.can_edit(page.spec.permission):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to add this record.")
            return
        self.switch_page(page_key)
        page.add_record()
        self.update_status_bar(f"{page.spec.title} ready")

    def get_local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def is_staff_restricted(self) -> bool:
        username = str(self.current_user.get("username", "")).strip().lower()
        role = str(self.role or "").strip().lower()
        return role == "staff" or username in {"staff", "staf"}

    def find_sources(self) -> list[tuple[str, str]]:
        return allowed_find_sources(self.role, staff_restricted=self.is_staff_restricted())

    def api_allowed_tables(self) -> set[str]:
        staff_tables = set(DEAL_TABLES)
        all_tables = {
            "rent_requirements", "rent_availability",
            "sale_requirements", "sale_availability",
            "income_transactions", "expense_transactions",
            "clients", "properties", "employees",
        }
        return staff_tables if self.is_staff_restricted() else all_tables

    def _is_port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.35):
                return True
        except OSError:
            return False

    def _set_browser_server_status(self, status: str, *, url: str | None = None) -> None:
        self._lan_web_status = status
        if hasattr(self, "sidebar_server_status"):
            self.sidebar_server_status.setText(status)
        if url is not None and hasattr(self, "sidebar_server_url_label"):
            self.sidebar_server_url_label.setText(url)

    def start_browser_server(self) -> None:
        """Start the LAN browser portal used by client computers."""
        if not LAN_WEB_ENABLED:
            self._set_browser_server_status("Browser server disabled", url="Set CRM_LAN_WEB_ENABLED=1 to enable")
            return
        if self._is_port_open("127.0.0.1", LAN_WEB_PORT):
            self._lan_web_owns_server = False
            self._set_browser_server_status("Browser server already running", url=self.browser_service_url)
            return
        try:
            import uvicorn
            from backend.main import app as fastapi_app
        except Exception as exc:
            self._set_browser_server_status("Browser server unavailable", url=str(exc))
            print(f"LAN web server import error: {exc}")
            if not self._lan_web_warning_shown:
                self._lan_web_warning_shown = True
                QMessageBox.warning(
                    self,
                    "LAN Browser Server",
                    "The LAN browser server could not start.\n\n"
                    f"{exc}\n\n"
                    "Client computers will not be able to connect until this is fixed.",
                )
            return

        try:
            config = uvicorn.Config(
                fastapi_app,
                host=LAN_WEB_HOST,
                port=LAN_WEB_PORT,
                reload=False,
                access_log=False,
                log_level="warning",
                log_config=None,
            )
            server = uvicorn.Server(config)
        except Exception as exc:
            self._set_browser_server_status("Browser server unavailable", url=str(exc))
            print(f"LAN web server startup error: {exc}")
            if not self._lan_web_warning_shown:
                self._lan_web_warning_shown = True
                QMessageBox.warning(
                    self,
                    "LAN Browser Server",
                    "The LAN browser server could not start.\n\n"
                    f"{exc}\n\n"
                    "The desktop CRM is still available.",
                )
            return
        self._lan_web_server = server
        self._lan_web_owns_server = True

        def serve() -> None:
            try:
                server.run()
            except BaseException as exc:
                self._lan_web_status = f"Browser server stopped: {exc}"
                print(f"LAN web server error: {exc}")

        self._lan_web_thread = threading.Thread(target=serve, name="CRM-LAN-Web-Server", daemon=True)
        self._lan_web_thread.start()
        self._set_browser_server_status("Browser login online", url=self.browser_service_url)

    def stop_browser_server(self) -> None:
        if not self._lan_web_owns_server:
            self._lan_web_server = None
            self._lan_web_thread = None
            return
        try:
            if self._lan_web_server:
                self._lan_web_server.should_exit = True
            if self._lan_web_thread and self._lan_web_thread.is_alive():
                self._lan_web_thread.join(timeout=2)
        except Exception:
            pass
        self._lan_web_server = None
        self._lan_web_thread = None
        self._lan_web_owns_server = False

    def start_local_service(self) -> None:
        app = self

        class CRMApiHandler(BaseHTTPRequestHandler):
            _rate_limit: dict[str, tuple[datetime, int]] = {}
            _rate_limit_lock = threading.Lock()

            def log_message(self, _format: str, *args: Any) -> None:
                return

            def _send(self, payload: dict, status: int = 200) -> None:
                body = json.dumps(payload, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _check_rate_limit(self) -> bool:
                client = self.client_address[0]
                now = datetime.now()
                with self._rate_limit_lock:
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
                return app.services.table_columns(table)

            def _clean_payload(self, table: str, data: dict, *, add_create_meta: bool = False) -> tuple[dict, list[str]]:
                columns = self._table_columns(table)
                # "id" is always stripped silently (from URL on PUT, auto-assigned on POST).
                # It must NOT appear in `unknown` or the request would be rejected with a
                # misleading 400 "unknown fields" error.
                cleaned = {key: value for key, value in data.items() if key in columns and key != "id"}
                unknown = sorted(key for key in data if key not in columns and key != "id")
                if add_create_meta:
                    if "created_by" in columns and "created_by" not in cleaned:
                        cleaned["created_by"] = app.current_user.get("username", "api")
                    if "created_at" in columns and "created_at" not in cleaned:
                        cleaned["created_at"] = str(datetime.now())
                return cleaned, unknown

            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
                self.end_headers()

            def do_GET(self) -> None:
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                from urllib.parse import parse_qs

                path, _, query = self.path.partition("?")
                params = {key: values[-1] for key, values in parse_qs(query).items()}
                if path in ("/", "/index"):
                    self._send({
                        "ok": True,
                        "service": "realestate-crm-api",
                        "version": "qt-1.0",
                        "message": "Qt CRM API is running",
                        "routes": ["/health", "/meta", "/users", "/stats", "/pipeline", "/search?q=term", "/records/<table>"],
                    })
                    return
                if path in ("/health", "/healthz"):
                    self._send({"ok": True, "service": "realestate-crm-api", "port": LOCAL_SERVICE_PORT})
                    return
                if path == "/meta":
                    self._send({
                        "ok": True,
                        "company": app.company_name,
                        "user": app.current_user.get("full_name"),
                        "role": app.role,
                        "url": app.local_service_url,
                        "db_size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
                    })
                    return
                if path == "/users":
                    if not has_permission(app.role, "users"):
                        self._send({"ok": False, "error": "access denied"}, 403)
                        return
                    rows = app.services.fetch_all("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id")
                    self._send({"ok": True, "users": rows})
                    return
                if path == "/stats":
                    stats = {}
                    for table in sorted(app.api_allowed_tables()):
                        row = app.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                        stats[table] = row["count"] if row else 0
                    self._send({"ok": True, "stats": stats})
                    return
                if path == "/pipeline":
                    stage = params.get("stage") or None
                    if stage and stage not in DEAL_STAGES:
                        self._send({"ok": False, "error": f"invalid stage. allowed: {DEAL_STAGES}"}, 400)
                        return
                    rows = app.pipeline_rows(stage)
                    self._send({"ok": True, "stage": stage or "All", "count": len(rows), "totals": app.pipeline_counts(), "rows": rows})
                    return
                if path.startswith("/records/"):
                    table = path.replace("/records/", "", 1).strip().lower()
                    if table not in app.api_allowed_tables():
                        self._send({"ok": False, "error": f"invalid table. allowed: {sorted(app.api_allowed_tables())}"}, 400)
                        return
                    try:
                        limit = min(int(params.get("limit", 500)), 2000)
                        offset = int(params.get("offset", 0))
                    except ValueError:
                        self._send({"ok": False, "error": "limit and offset must be integers"}, 400)
                        return
                    total_row = app.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                    rows = app.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
                    self._send({"ok": True, "table": table, "count": len(rows), "total": total_row["count"] if total_row else 0, "rows": rows})
                    return
                if path == "/search":
                    q = params.get("q", "").strip().lower()
                    if not q:
                        self._send({"ok": False, "error": "query param 'q' is required"}, 400)
                        return
                    results = []
                    pattern = f"%{q}%"
                    for source, table in app.find_sources():
                        columns = [
                            column
                            for column in sorted(app.services.table_columns(table))
                            if column not in GLOBAL_SEARCH_HIDDEN_COLUMNS
                        ]
                        if not columns:
                            continue
                        source_text = f"{source} {table.replace('_', ' ')}".lower()
                        if q in source_text:
                            rows = app.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 20")
                        else:
                            where = " OR ".join(f"LOWER(CAST(COALESCE(\"{col}\", '') AS TEXT)) LIKE ?" for col in columns)
                            rows = app.services.fetch_all(f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 20", tuple([pattern] * len(columns)))
                        for row in rows:
                            fields = {column: row.get(column) for column in columns}
                            label = (
                                fields.get("client_name")
                                or fields.get("owner_name")
                                or fields.get("full_name")
                                or fields.get("title")
                                or fields.get("property_code")
                                or fields.get("id")
                            )
                            detail = (
                                fields.get("contact")
                                or fields.get("contact_phone")
                                or fields.get("phone")
                                or fields.get("owner_contact")
                                or fields.get("email")
                                or fields.get("location")
                                or ""
                            )
                            results.append({
                                "table": table,
                                "source": source,
                                "id": row.get("id"),
                                "label": str(label or ""),
                                "detail": str(detail or ""),
                                "fields": fields,
                            })
                    self._send({"ok": True, "query": q, "count": len(results), "results": results})
                    return
                self._send({"ok": False, "error": "not found"}, 404)

            def do_POST(self) -> None:
                self._write_record("POST")

            def do_PUT(self) -> None:
                self._write_record("PUT")

            def _write_record(self, method: str) -> None:
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                path = self.path.split("?", 1)[0]
                parts = path.strip("/").split("/")
                if method == "POST":
                    if len(parts) != 2 or parts[0] != "records":
                        self._send({"ok": False, "error": "POST requires /records/<table>"}, 400)
                        return
                    table = parts[1].lower()
                    row_id = None
                else:
                    if len(parts) != 3 or parts[0] != "records":
                        self._send({"ok": False, "error": "PUT requires /records/<table>/<id>"}, 400)
                        return
                    table = parts[1].lower()
                    try:
                        row_id = int(parts[2])
                    except ValueError:
                        self._send({"ok": False, "error": "invalid id"}, 400)
                        return
                if table not in app.api_allowed_tables():
                    self._send({"ok": False, "error": "invalid table"}, 400)
                    return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8") if length else "{}"
                    data = json.loads(body)
                except Exception:
                    self._send({"ok": False, "error": "invalid JSON body"}, 400)
                    return
                if not isinstance(data, dict) or not data:
                    self._send({"ok": False, "error": "empty body"}, 400)
                    return
                cleaned, unknown = self._clean_payload(table, data, add_create_meta=(method == "POST"))
                if unknown:
                    self._send({"ok": False, "error": f"unknown fields: {unknown}"}, 400)
                    return
                if not cleaned:
                    self._send({"ok": False, "error": "no valid fields to save"}, 400)
                    return
                try:
                    if method == "POST":
                        cols = ", ".join(cleaned)
                        placeholders = ", ".join("?" for _ in cleaned)
                        new_id = app.services.insert(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(cleaned.values()))
                        app.after_record_saved(table, new_id)
                        self._send({"ok": True, "table": table, "id": new_id, "message": "record created"}, 201)
                    else:
                        set_clause = ", ".join(f"{key}=?" for key in cleaned)
                        app.services.execute(f"UPDATE {table} SET {set_clause} WHERE id=?", tuple(cleaned.values()) + (row_id,))
                        app.after_record_saved(table, row_id)
                        self._send({"ok": True, "table": table, "id": row_id, "message": "record updated"})
                except Exception as exc:
                    self._send({"ok": False, "error": str(exc)}, 500)

            def do_DELETE(self) -> None:
                if not self._check_rate_limit():
                    self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                    return
                parts = self.path.split("?", 1)[0].strip("/").split("/")
                if len(parts) != 3 or parts[0] != "records":
                    self._send({"ok": False, "error": "DELETE requires /records/<table>/<id>"}, 400)
                    return
                table = parts[1].lower()
                if table not in app.api_allowed_tables():
                    self._send({"ok": False, "error": "invalid table"}, 400)
                    return
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok": False, "error": "invalid id"}, 400)
                    return
                try:
                    app.services.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
                    self._send({"ok": True, "table": table, "id": row_id, "message": "record deleted"})
                except Exception as exc:
                    self._send({"ok": False, "error": str(exc)}, 500)

        def serve() -> None:
            try:
                self._api_server = ThreadingHTTPServer(("0.0.0.0", LOCAL_SERVICE_PORT), CRMApiHandler)
                self._api_server.serve_forever()
            except Exception as exc:
                print(f"Local API Error: {exc}")

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
        abbreviations = {
            "dashboard": "DB",
            "rent": "RN",
            "sale": "SL",
            "properties": "PR",
            "clients": "CL",
            "financials": "FI",
            "employees": "EM",
            "reports": "RP",
            "ai": "AI",
            "users": "US",
            "settings": "ST",
        }
        return abbreviations.get(key, label[:2].upper())

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
            separator.setObjectName("NavSeparator")
            separator.setFixedHeight(1)
            self.nav_layout.addWidget(separator)
        section = QLabel(label.upper())
        section.setObjectName("NavSection")
        section.setFixedHeight(24)
        section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.nav_layout.addWidget(section)
        self._nav_section_count += 1

    def _build_pages(self) -> None:
        if not self.is_staff_restricted():
            self._add_nav_section("Overview")
            self._report_startup(70, "Loading dashboard")
            self._add_page("dashboard", "Dashboard", self._dashboard_page())
        deal_pages = []
        if has_permission(self.role, "rent") or has_permission(self.role, "rent_view"):
            deal_pages.append("rent")
        if has_permission(self.role, "sale") or has_permission(self.role, "sale_view"):
            deal_pages.append("sale")
        if deal_pages:
            self._add_nav_section("Deal desk")
            if "rent" in deal_pages:
                self._report_startup(74, "Loading rent dealings")
                self._add_page("rent", "Rent Dealings", DealModule(self, "Rent Dealings", self.specs["rent_req"], self.specs["rent_av"]))
            if "sale" in deal_pages:
                self._report_startup(78, "Loading sale dealings")
                self._add_page("sale", "Sale Dealings", DealModule(self, "Sale Dealings", self.specs["sale_req"], self.specs["sale_av"]))
        record_pages = []
        if has_permission(self.role, "properties"):
            record_pages.append("properties")
        if has_permission(self.role, "clients"):
            record_pages.append("clients")
        if record_pages:
            self._add_nav_section("Records")
            if "properties" in record_pages:
                self._report_startup(82, "Loading property records")
                self._add_page("properties", "Properties", DataTablePage(self, self.specs["properties"]))
            if "clients" in record_pages:
                self._report_startup(84, "Loading client records")
                self._add_page("clients", "Clients", DataTablePage(self, self.specs["clients"]))
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            self._report_startup(86, "Loading financials")
            self._add_page("financials", "Financials", FinancialModule(self, self.specs["income"], self.specs["expenses"]))
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            self._report_startup(87, "Loading employees")
            self._add_page("employees", "Employees", EmployeesModule(self, self.specs["employees"], self.specs["salary"]))
        if has_permission(self.role, "reports"):
            self._report_startup(88, "Loading reports")
            self._add_page("reports", "Reports", ReportsModule(self))
        if has_permission(self.role, "ai"):
            self._add_nav_section("Intelligence")
            self._report_startup(89, "Loading AI insights")
            self._add_page("ai", "AI Insights", AIInsightsModule(self))
        if self.role in ("Super Admin", "Admin"):
            self._add_nav_section("Admin")
            self._report_startup(89, "Loading user administration")
            self._add_page("users", "Users", UsersModule(self))
        if has_permission(self.role, "settings"):
            self._report_startup(89, "Loading settings")
            self._add_page("settings", "Settings", SettingsModule(self))
        self.nav_layout.addStretch(1)
        self.nav_shell.setMinimumHeight(self.nav_layout.sizeHint().height())
        if self.nav_keys:
            self.switch_page(self.nav_keys[0])

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.dashboard_grid = QGridLayout()
        self.dashboard_grid.setSpacing(14)
        layout.addLayout(self.dashboard_grid)
        self.pipeline_text = QTextEdit()
        self.pipeline_text.setReadOnly(True)
        self.pipeline_text.setFont(QFont("Consolas", 9))
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
            button.setChecked(nav_key == key)
        self.update_status_bar()

    def can_edit(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    def _owner_broker_type(self, value: Any, default: str) -> str:
        text = str(value or "").strip().lower()
        if text in {"b", "broker"}:
            return "Broker"
        if text in {"o", "owner"}:
            return "Owner"
        return default

    def _deal_client_contacts(self, table: str, row: dict) -> list[dict[str, str]]:
        contacts: list[dict[str, str]] = []
        if table in {"rent_requirements", "sale_requirements"}:
            default_type = "Tenant" if table.startswith("rent") else "Buyer"
            contacts.append({
                "name": str(row.get("client_name") or "").strip(),
                "phone": str(row.get("contact") or row.get("contact_phone") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_status"), default_type),
            })
        elif table in {"rent_availability", "sale_availability"}:
            contacts.append({
                "name": str(row.get("owner_name") or "").strip(),
                "phone": str(row.get("contact") or row.get("contact_phone") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_broker"), "Owner"),
            })
        for key in ("broker", "preferred_broker", "posted_by_broker", "posted_by", "client_broker"):
            broker = str(row.get(key) or "").strip()
            if broker and broker.lower() not in {"o", "b", "owner", "broker", "direct", "client"}:
                contacts.append({"name": broker, "phone": "", "email": "", "type": "Broker"})
        return contacts

    def upsert_client_from_deal(self, table: str, row: dict) -> None:
        if table not in DEAL_TABLES:
            return
        for contact in self._deal_client_contacts(table, row):
            name = contact["name"]
            if not name:
                continue
            phone = contact["phone"]
            email = contact["email"]
            client_type = contact["type"] or "Other"
            notes = f"Auto-synced from {GLOBAL_SEARCH_SOURCE_LABELS.get(table, table)} #{row.get('id') or ''}".strip()
            existing = None
            if phone:
                existing = self.services.fetch_one("SELECT id FROM clients WHERE phone=? LIMIT 1", (phone,))
            if not existing:
                existing = self.services.fetch_one("SELECT id FROM clients WHERE LOWER(client_name)=LOWER(?) LIMIT 1", (name,))
            if existing:
                self.services.execute(
                    """UPDATE clients
                       SET client_name=COALESCE(NULLIF(client_name,''), ?),
                           phone=COALESCE(NULLIF(phone,''), ?),
                           email=COALESCE(NULLIF(email,''), ?),
                           client_type=COALESCE(NULLIF(client_type,''), ?),
                           status=COALESCE(NULLIF(status,''), 'Active'),
                           notes=COALESCE(NULLIF(notes,''), ?)
                       WHERE id=?""",
                    (name, phone, email, client_type, notes, existing["id"]),
                )
            else:
                self.services.insert(
                    """INSERT INTO clients (client_name, phone, email, client_type, status, notes, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (name, phone, email, client_type, "Active", notes, datetime.now()),
                )

    def _property_match(self, row: dict, title: str, property_type: str) -> dict | None:
        location = str(row.get("location") or "").strip()
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("contact") or row.get("contact_phone") or "").strip()
        if owner_contact:
            found = self.services.fetch_one("SELECT id FROM properties WHERE owner_contact=? LIMIT 1", (owner_contact,))
            if found:
                return found
        if owner_name and location:
            found = self.services.fetch_one(
                """SELECT id FROM properties
                   WHERE LOWER(COALESCE(owner_name,''))=LOWER(?)
                     AND LOWER(COALESCE(location,''))=LOWER(?)
                   LIMIT 1""",
                (owner_name, location),
            )
            if found:
                return found
        if title and location:
            return self.services.fetch_one(
                """SELECT id FROM properties
                   WHERE LOWER(COALESCE(title,''))=LOWER(?)
                     AND LOWER(COALESCE(location,''))=LOWER(?)
                     AND LOWER(COALESCE(property_type,''))=LOWER(?)
                   LIMIT 1""",
                (title, location, property_type),
            )
        return None

    def sync_property_from_availability(self, table: str, row: dict, status: str) -> int | None:
        if table not in {"rent_availability", "sale_availability"}:
            return None
        property_type = str(row.get("property_availability") or row.get("property_type") or "").strip()
        location = str(row.get("location") or "").strip()
        if not property_type and not location:
            return None
        title = f"{property_type or 'Property'} - {location or 'Location'}"
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("contact") or row.get("contact_phone") or "").strip()
        area = " ".join(str(row.get(key) or "").strip() for key in ("size", "measurement") if row.get(key)).strip()
        monthly_rent = safe_float(row.get("monthly_rent")) if table.startswith("rent") else 0
        sale_price = safe_float(row.get("demand") or row.get("asking_price")) if table.startswith("sale") else 0
        maintenance = safe_float(row.get("maintenance_charge"))
        description = str(row.get("remarks") or row.get("description") or "").strip()
        fields = {
            "title": title,
            "property_type": property_type,
            "status": status,
            "owner_name": owner_name,
            "owner_contact": owner_contact,
            "location": location,
            "area": area,
            "floor": row.get("floor") or row.get("floor_no") or "",
            "monthly_rent": monthly_rent,
            "sale_price": sale_price,
            "maintenance_charge": maintenance,
            "facilities": row.get("facilities") or "",
            "description": description,
        }
        existing = self._property_match(row, title, property_type)
        if existing:
            assignments = ", ".join(f"{key}=?" for key in fields)
            self.services.execute(
                f"UPDATE properties SET {assignments} WHERE id=?",
                tuple(fields.values()) + (existing["id"],),
            )
            return int(existing["id"])
        fields["property_code"] = gen_id("PROP")
        fields["created_at"] = datetime.now()
        columns = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description", "created_at"]
        return self.services.insert(
            f"INSERT INTO properties ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(fields.get(column) for column in columns),
        )

    def after_record_saved(self, table: str, row_id: int | None) -> None:
        if table not in DEAL_TABLES or not row_id:
            return
        row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not row:
            return
        self.upsert_client_from_deal(table, row)
        status = str(row.get("status") or "").strip().lower()
        if table == "rent_availability" and status == "rented":
            self.sync_property_from_availability(table, row, "Rented")
        elif table == "sale_availability" and status == "sold":
            self.sync_property_from_availability(table, row, "Sold")

    def sync_all_deal_contacts(self) -> int:
        synced = 0
        for table in DEAL_TABLES:
            for row in self.services.fetch_all(f"SELECT * FROM {table} ORDER BY id"):
                self.upsert_client_from_deal(table, row)
                status = str(row.get("status") or "").strip().lower()
                if table == "rent_availability" and status == "rented":
                    self.sync_property_from_availability(table, row, "Rented")
                elif table == "sale_availability" and status == "sold":
                    self.sync_property_from_availability(table, row, "Sold")
                synced += 1
        return synced

    def mark_availability_closed(self, page: DataTablePage, table: str, status: str) -> None:
        if self.role not in {"Super Admin", "Admin"}:
            QMessageBox.warning(self, "Access Denied", "Only Super Admin/Admin can mark a property as rented or sold.")
            return
        if table not in {"rent_availability", "sale_availability"}:
            return
        row = page.require_single_row(f"marking as {status.lower()}")
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row["id"],)) or row
        ask = QMessageBox.question(self, status, f"Mark {table.replace('_', ' ')} #{row['id']} as {status}?")
        if ask != QMessageBox.Yes:
            return
        now = datetime.now()
        self.services.execute(
            f"""UPDATE {table}
                SET status=?, workflow_stage='Closed', deal_probability=100,
                    closed_at=COALESCE(closed_at, ?), last_contacted=?
                WHERE id=?""",
            (status, now, now.strftime(PY_DATE_STORAGE_FORMAT), row["id"]),
        )
        full.update({"status": status, "workflow_stage": "Closed", "deal_probability": 100, "closed_at": now})
        property_id = self.sync_property_from_availability(table, full, status)
        self.upsert_client_from_deal(table, full)
        page.refresh()
        self.refresh_dashboard()
        message = f"Record #{row['id']} marked {status}"
        if property_id:
            message += f" and synced to property #{property_id}"
        QMessageBox.information(self, status, message)
        self.update_status_bar(message)

    def refresh_all_pages(self) -> None:
        if "dashboard" in self.pages:
            self.refresh_dashboard()
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        errors: list[str] = []
        for widget in self.pages.values():
            if hasattr(widget, "refresh"):
                try:
                    widget.refresh()
                except Exception as exc:
                    errors.append(f"{widget.__class__.__name__}: {exc}")
        if errors:
            QMessageBox.warning(
                self,
                "Refresh Issues",
                "Some CRM pages could not refresh:\n\n" + "\n".join(errors[:6]),
            )
            self.update_status_bar("Refresh completed with issues")
        else:
            self.update_status_bar("CRM data refreshed")

    def refresh_dashboard(self) -> None:
        if "dashboard" not in self.pages or not hasattr(self, "dashboard_grid"):
            return
        while self.dashboard_grid.count():
            item = self.dashboard_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        metrics = [
            ("Rent Requirements", self.count("rent_requirements"), "Client demand"),
            ("Rent Availability", self.count("rent_availability"), "Listed for rent"),
            ("Sale Requirements", self.count("sale_requirements"), "Buyer demand"),
            ("Sale Availability", self.count("sale_availability"), "Listed for sale"),
            ("Clients", self.count("clients"), "Contact records"),
            ("Employees", self.count("employees"), "Team records"),
            ("Income", money(self.sum_value("income_transactions", "amount"), self.currency_symbol), "Total income"),
            ("Expenses", money(self.sum_value("expense_transactions", "amount"), self.currency_symbol), "Total expenses"),
        ]
        for idx, (title, value, note) in enumerate(metrics):
            self.dashboard_grid.addWidget(MetricCard(title, str(value), note), idx // 4, idx % 4)
        lines = ["DEAL RECORDS", "-" * 78]
        lines.append(f"Rent Requirements : {self.count('rent_requirements')}")
        lines.append(f"Rent Availability : {self.count('rent_availability')}")
        lines.append(f"Sale Requirements : {self.count('sale_requirements')}")
        lines.append(f"Sale Availability : {self.count('sale_availability')}")
        self.pipeline_text.setPlainText("\n".join(lines))

    def count(self, table: str) -> int:
        row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
        return int(row["count"]) if row else 0

    def sum_value(self, table: str, column: str) -> float:
        row = self.services.fetch_one(f"SELECT SUM({column}) AS total FROM {table}")
        return safe_float(row["total"]) if row else 0

    def ai_match(self, page: DataTablePage, table: str) -> None:
        row = page.require_single_row("AI matching")
        if not row:
            return
        text = self.ai_match_text(table, row["id"])
        dialog = QDialog(self)
        dialog.setWindowTitle("AI Smart Match")
        dialog.resize(760, 460)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setFont(QFont("Consolas", 10))
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def ai_match_text(self, table: str, row_id: int) -> str:
        fallback_header = ""
        try:
            report = self.intelligence_service.match_report(table, row_id)
            if report:
                return report
            fallback_header = "Local AI match returned no result.\nUsing basic matching fallback.\n\n"
        except Exception as exc:
            fallback_header = f"Local AI match unavailable: {exc}\nUsing basic matching fallback.\n\n"
        target = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not target:
            return "No record found."
        if table == "rent_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, monthly_rent AS amount, property_availability AS type
                   FROM rent_availability
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
                   ORDER BY ABS(COALESCE(monthly_rent,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_requires") or "", target.get("budget") or 0),
            )
        elif table == "sale_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, demand AS amount, property_availability AS type
                   FROM sale_availability
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?)
                   ORDER BY ABS(COALESCE(demand,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_requires") or "", target.get("budget") or 0),
            )
        elif table == "rent_availability":
            rows = self.services.fetch_all(
                """SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
                   FROM rent_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_availability") or "", target.get("monthly_rent") or 0),
            )
        else:
            rows = self.services.fetch_all(
                """SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
                   FROM sale_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_availability") or "", target.get("demand") or 0),
            )
        lines = [f"Smart matches for {table} #{row_id}", "-" * 72]
        for item in rows:
            lines.append(
                f"#{item['id']:<4} {str(item.get('name') or '-')[:24]:<24} "
                f"{str(item.get('location') or '-')[:18]:<18} {str(item.get('type') or '-')[:15]:<15} "
                f"{money(item.get('amount'), self.currency_symbol):>12}"
            )
        result = "\n".join(lines) if rows else "No close matches found."
        return fallback_header + result

    def pipeline_counts(self) -> dict[str, int]:
        counts = {stage: 0 for stage in DEAL_STAGES}
        for table in DEAL_TABLES:
            rows = self.services.fetch_all(
                f"""SELECT COALESCE(NULLIF(workflow_stage,''), 'Lead') AS stage, COUNT(*) AS count
                    FROM {table}
                    GROUP BY COALESCE(NULLIF(workflow_stage,''), 'Lead')"""
            )
            for row in rows:
                stage = row.get("stage") if row.get("stage") in DEAL_STAGES else "Lead"
                counts[stage] = counts.get(stage, 0) + int(row.get("count") or 0)
        return counts

    def pipeline_rows(self, stage: str | None = None) -> list[dict]:
        datasets = [
            ("Rent Req", "rent_requirements", "client_name", "property_requires", "budget"),
            ("Rent Av", "rent_availability", "owner_name", "property_availability", "monthly_rent"),
            ("Sale Req", "sale_requirements", "client_name", "property_requires", "budget"),
            ("Sale Av", "sale_availability", "owner_name", "property_availability", "demand"),
        ]
        rows: list[dict] = []
        for source, table, name_col, type_col, amount_col in datasets:
            where = ""
            params: tuple[Any, ...] = ()
            if stage:
                where = "WHERE COALESCE(NULLIF(workflow_stage,''), 'Lead')=?"
                params = (stage,)
            for row in self.services.fetch_all(
                f"""SELECT id, {name_col} AS name, location, {type_col} AS property_type,
                           {amount_col} AS amount, workflow_stage, priority, expected_close_value
                    FROM {table}
                    {where}
                    ORDER BY id DESC LIMIT 20"""
                ,
                params,
            ):
                rows.append({
                    "source": source,
                    "id": row["id"],
                    "name": row.get("name") or "",
                    "location": row.get("location") or "",
                    "stage": row.get("workflow_stage") or "Lead",
                    "priority": row.get("priority") or "Medium",
                    "amount": row.get("expected_close_value") or row.get("amount") or 0,
                })
        return rows[:40]

    def open_report(self, kind: str) -> None:
        reports = self.pages.get("reports")
        if isinstance(reports, ReportsModule):
            self.switch_page("reports")
            reports.report_type.setCurrentText("Rent" if kind == "rent" else "Sale")
            reports.generate(kind)
        else:
            self.preview_report(kind)

    def preview_report(self, kind: str) -> None:
        try:
            if kind == "sale":
                result = self.report_service.sale_report()
            elif kind == "both":
                result = self.report_service.dealings_report()
            else:
                result = self.report_service.rent_report()
        except Exception as exc:
            QMessageBox.warning(self, "Report Error", f"Could not generate report:\n{exc}")
            self.update_status_bar("Report generation failed")
            return
        self.last_report = result
        self.update_status_bar(f"{result.title} generated")
        ReportPreviewDialog(result, self).exec()

    def preview_named_report(self, kind: str) -> None:
        normalized = kind.strip().lower()
        if normalized in {"rent", "sale", "both", "rent + sale"}:
            self.preview_report("both" if normalized in {"both", "rent + sale"} else normalized)
            return
        try:
            if normalized == "financial":
                result = ReportResult("Financial Summary", self.financial_text(), filename_slug="financial_summary")
            elif normalized == "properties":
                result = ReportResult("Property Report", self.generic_report("properties", "PROPERTY REPORT"), filename_slug="property_report")
            elif normalized == "clients":
                result = ReportResult("Client Report", self.generic_report("clients", "CLIENT REPORT"), filename_slug="client_report")
            elif normalized == "employees":
                result = ReportResult("Employee Report", self.generic_report("employees", "EMPLOYEE REPORT"), filename_slug="employee_report")
            else:
                result = ReportResult("Attendance Report", self.attendance_report(), filename_slug="attendance_report")
        except Exception as exc:
            QMessageBox.warning(self, "Report Error", f"Could not generate report:\n{exc}")
            self.update_status_bar("Report generation failed")
            return
        self.last_report = result
        self.update_status_bar(f"{result.title} generated")
        ReportPreviewDialog(result, self).exec()

    def open_search(self) -> None:
        self.update_status_bar("Find opened")
        SearchDialog(self).exec()
        self.update_status_bar("Find closed")

    def _rows_in_date_range(
        self,
        table: str,
        date_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        rows = self.services.fetch_all(f"SELECT * FROM {table} ORDER BY {date_key} DESC, id DESC")
        start = parse_py_date(start_date)
        end = parse_py_date(end_date)
        if not start and not end:
            return rows
        filtered: list[dict] = []
        for row in rows:
            row_date = parse_py_date(row.get(date_key))
            if not row_date:
                continue
            if start and row_date.date() < start.date():
                continue
            if end and row_date.date() > end.date():
                continue
            filtered.append(row)
        return filtered

    def _period_label(self, start_date: str | None = None, end_date: str | None = None) -> str:
        start = format_date_display(start_date) if parse_py_date(start_date) else "Beginning"
        end = format_date_display(end_date) if parse_py_date(end_date) else "Today"
        if start == "Beginning" and end == "Today":
            return "All records"
        return f"{start} to {end}"

    def build_financial_text(self, start_date: str | None = None, end_date: str | None = None) -> str:
        income_rows = self._rows_in_date_range("income_transactions", "transaction_date", start_date, end_date)
        expense_rows = self._rows_in_date_range("expense_transactions", "transaction_date", start_date, end_date)
        income = sum(safe_float(row.get("amount")) for row in income_rows)
        expenses = sum(safe_float(row.get("amount")) for row in expense_rows)
        profit = income - expenses
        income_by_type: dict[str, dict[str, float]] = {}
        for row in income_rows:
            key = str(row.get("income_type") or "Other")
            bucket = income_by_type.setdefault(key, {"qty": 0, "total": 0.0})
            bucket["qty"] += 1
            bucket["total"] += safe_float(row.get("amount"))
        expense_by_category: dict[str, dict[str, float]] = {}
        for row in expense_rows:
            key = str(row.get("expense_category") or "Other")
            bucket = expense_by_category.setdefault(key, {"qty": 0, "total": 0.0})
            bucket["qty"] += 1
            bucket["total"] += safe_float(row.get("amount"))
        lines = [
            "=" * 72,
            f"FINANCIAL SUMMARY - {datetime.now().strftime(PY_DATE_DISPLAY_FORMAT)}",
            f"Company: {self.company_name}",
            f"Period: {self._period_label(start_date, end_date)}",
            "=" * 72,
            "",
            "INCOME BY TYPE",
            "-" * 72,
        ]
        if income_by_type:
            for key, bucket in sorted(income_by_type.items()):
                lines.append(f"{key:<35} Qty:{int(bucket['qty']):>4} {money(bucket['total'], self.currency_symbol):>18}")
        else:
            lines.append("No income records found for this period.")
        lines += ["", f"TOTAL INCOME:   {money(income, self.currency_symbol)}", "", "EXPENSES BY CATEGORY", "-" * 72]
        if expense_by_category:
            for key, bucket in sorted(expense_by_category.items()):
                lines.append(f"{key:<35} Qty:{int(bucket['qty']):>4} {money(bucket['total'], self.currency_symbol):>18}")
        else:
            lines.append("No expense records found for this period.")
        margin = (profit / income * 100) if income else 0
        lines += [
            "",
            f"TOTAL EXPENSES: {money(expenses, self.currency_symbol)}",
            "=" * 72,
            f"NET PROFIT:     {money(profit, self.currency_symbol)}",
            f"PROFIT MARGIN:  {margin:.1f}%",
            "=" * 72,
        ]
        return "\n".join(lines)

    def financial_text(self, start_date: str | None = None, end_date: str | None = None) -> str:
        if start_date or end_date:
            return self.build_financial_text(start_date, end_date)
        page = self.pages.get("financials")
        if isinstance(page, FinancialModule):
            page.summary.refresh()
            return page.summary.text.toPlainText()
        return self.build_financial_text()

    def generic_report(self, table: str, title: str) -> str:
        rows = self.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC")
        lines = ["=" * 78, title, f"Generated: {datetime.now().strftime(PY_DATE_DISPLAY_FORMAT + ' %H:%M')}", "=" * 78, ""]
        for row in rows:
            important = []
            for key in ("id", "client_name", "owner_name", "full_name", "title", "phone", "contact", "location", "status", "role"):
                if key in row and row[key] not in (None, ""):
                    important.append(f"{key}: {row[key]}")
            lines.append(" | ".join(important) if important else str(row))
        lines.append("")
        lines.append(f"Total: {len(rows)}")
        return "\n".join(lines)

    def attendance_report(self) -> str:
        rows = self.services.fetch_all(
            """SELECT a.date, e.full_name, a.status, a.notes
               FROM attendance a JOIN employees e ON a.employee_id=e.id
               ORDER BY a.date DESC, e.full_name"""
        )
        lines = ["=" * 78, "ATTENDANCE REPORT", f"Generated: {datetime.now().strftime(PY_DATE_DISPLAY_FORMAT + ' %H:%M')}", "=" * 78, ""]
        for row in rows:
            lines.append(f"{row['date']:<12} {row['full_name'][:28]:<28} {row['status'] or '-':<10} {row['notes'] or ''}")
        lines.append("")
        lines.append(f"Total rows: {len(rows)}")
        return "\n".join(lines)

    def export_all_tables(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        base, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Tables",
            str(OUTPUT_DIR / f"crm_export_{datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV Files (*.csv)",
        )
        if not base:
            return
        stem, ext = os.path.splitext(base)
        tables = [
            "rent_requirements", "rent_availability", "sale_requirements", "sale_availability",
            "income_transactions", "expense_transactions", "employees", "clients", "properties",
            "attendance", "salary_payments", "users",
        ]
        for table in tables:
            rows = self.services.fetch_all(f"SELECT * FROM {table}")
            if not rows:
                continue
            with open(f"{stem}_{table}{ext}", "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        QMessageBox.information(self, "Exported", f"Tables exported with prefix:\n{stem}")
        self.update_status_bar("All tables exported")

    def backup_database(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            str(OUTPUT_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"),
            "SQLite DB (*.db)",
        )
        if not path:
            return
        shutil.copy2(DB_PATH, path)
        QMessageBox.information(self, "Backup", f"Database backed up to:\n{path}")
        self.update_status_bar("Database backup saved")

    def show_api_health(self) -> None:
        QMessageBox.information(
            self,
            "Server Health",
            f"Browser login for client computers:\n{self.browser_service_url}\n\n"
            f"Status: {self._lan_web_status}\n"
            f"Host binding: {LAN_WEB_HOST}:{LAN_WEB_PORT}\n\n"
            f"Desktop internal API:\n{self.local_service_url}\n\n"
            "Client users should open the browser login URL on the office network.",
        )

    def show_text_dialog(self, title: str, text: str, *, width: int = 760, height: int = 560) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setWordWrapMode(preview.wordWrapMode())
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_user_guide(self) -> None:
        self.show_text_dialog(
            "User Guide",
            """PROFESSIONAL REAL ESTATE CRM - QT USER GUIDE
===============================================

DASHBOARD
  - View key totals and income/expense totals.

RENT AND SALE DEALINGS
  - Add requirements and available properties.
  - Edit records, run smart matching, and generate reports.

PROPERTIES AND CLIENTS
  - Maintain portfolio and contact records.
  - Use Details or Copy Row for quick review/sharing.

FINANCIALS
  - Record income and expense transactions.
  - Review and export profit/loss summary.

EMPLOYEES
  - Maintain employee records.
  - Mark attendance and process salary payments.

REPORTS
  - Generate rent, sale, combined, financial, property, client, employee, and attendance reports.
  - Export TXT, CSV, or PDF.

MENUS AND SHORTCUTS
  - File > New creates the main rent/sale records without hunting through tabs.
  - Ctrl+F opens Find, F5 refreshes, Ctrl+E exports all tables, Ctrl+B backs up the database.
  - Ctrl+1 through Ctrl+9 jump between visible CRM sections.
  - F11 opens full screen; Shift+F11 returns to normal view.

REQUIRED FIELDS
  - Deal forms require date, name, client/broker, contact, property, size, amount, and location.
  - Required labels are marked with * and checked before saving.

AI INSIGHTS
  - Run local pandas/numpy analysis for lead scoring, NLP keywords, matching, price guidance, and forecasts.
  - AI features stay offline on the local SQLite database.

LAN SERVER
  - Keep this main/server computer running while other users work.
  - Client computers open the browser login URL shown in Tools > Server Health.
  - The browser portal listens on port 6090 by default.

SECURITY
  - Role-based access controls remain active.
  - Admin roles can manage users, settings, backup, and delete records.
""",
        )

    def show_roles_info(self) -> None:
        lines = [
            "ROLE-BASED ACCESS CONTROL",
            "=" * 72,
            "Feature            Super Admin  Admin   Manager   Staff   Viewer",
            "-" * 72,
            "Dashboard          Yes          Yes     Yes       No      Yes",
            "Rent/Sale Deals    Full         Full    Full      Add/Edit View",
            "Find Rent/Sale     Yes          Yes     Yes       Yes     Yes",
            "Properties         Full         Full    Full      No      No",
            "Clients            Full         Full    Full      No      No",
            "Financials         Full         Full    View      No      No",
            "Employees          Full         Full    Full      View    View",
            "Reports            Yes          Yes     Yes       No      Yes",
            "AI Insights         Yes          Yes     Yes       No      No",
            "Settings           Yes          Yes     No        No      No",
            "User Management    Yes          Yes     No        No      No",
            "Delete Records     Yes          Yes     No        No      No",
            "Backup/Export      Yes          Yes     No        No      No",
            "",
            "Permissions configured in qt_crm_app.py:",
        ]
        for role, permissions in ROLE_PERMISSIONS.items():
            lines.append(f"{role:<12}: {', '.join(permissions)}")
        self.show_text_dialog("Roles & Permissions", "\n".join(lines), width=780, height=560)

    def show_developer_info(self) -> None:
        QMessageBox.information(
            self,
            "Developer Info",
            "Developer: Muhammad Siddique\n"
            "Email: info@msxhan.online\n\n"
            "Application: Professional Real Estate CRM\n"
            "UI Framework: Python + PySide6/Qt",
        )

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"Professional Real Estate CRM\n"
            f"Version: Qt Migration\n\n"
            f"Built with Python and PySide6\n"
            f"Database: SQLite\n"
            f"DB File: {DB_PATH}\n"
            f"Browser Login: {self.browser_service_url}\n"
            f"Desktop API: {self.local_service_url}\n\n"
            f"Developer: Muhammad Siddique\n"
            f"Email: info@msxhan.online\n\n"
            f"Company: {self.company_name}\n"
            f"User: {self.current_user.get('full_name')} ({self.role})\n"
            f"Year: {datetime.now().year}",
        )

    def restart_app(self) -> None:
        self.stop_browser_server()
        self.stop_local_service()
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent))
        QApplication.quit()

    def logout(self) -> None:
        if QMessageBox.question(self, "Logout", "Logout and return to the login screen?") != QMessageBox.Yes:
            return
        self.restart_app()

    def closeEvent(self, event: Any) -> None:
        self.stop_browser_server()
        self.stop_local_service()
        super().closeEvent(event)


def deal_common_fields(
    name_key: str,
    property_key: str,
    amount_key: str,
    *,
    name_label: str | None = None,
) -> list[FieldSpec]:
    name_label = name_label or ("Name *" if name_key == "client_name" else "Owner Name *")
    property_label = "Property Requires" if "requires" in property_key else "Property Availability"
    amount_label = "Budget" if amount_key == "budget" else ("Rent" if amount_key == "monthly_rent" else "Demand")
    return [
        FieldSpec("Date *", "date", "date", required=True),
        FieldSpec(name_label, name_key, required=True),
        FieldSpec("Contact *", "contact", required=True),
        FieldSpec(f"{property_label} *", property_key, "combo_other", options=["flat", "banglow", "shop", "godam", "plot", "building", "villa", "house"], required=True),
        FieldSpec("Size *", "size", "combo_other", options=["single-bed", "double-bed", "any floor", "ground floor", "single story", "double story", "mezzanine", "basement"], required=True),
        FieldSpec("Measurement", "measurement"),
        FieldSpec(f"{amount_label} (Rs.) *", amount_key, numeric=True, required=True),
        FieldSpec("Floor", "floor", "combo_other", options=["Ground", "1st", "2nd", "3rd", "4th", "5th", "Top", "Any"]),
        FieldSpec("Location *", "location", "autocomplete", options=COMMON_AREAS, required=True),
        FieldSpec("Facilities", "facilities", "facilities", options=FACILITY_OPTIONS),
        FieldSpec("Bachelor / Family", "bachelor_family", "combo_other", options=["Bachelor", "Family", "Both", "Any"]),
        FieldSpec("Remarks", "remarks", "text"),
    ]


def deal_fields(name_key: str, property_key: str, amount_key: str) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key)
    fields.insert(2, FieldSpec("Owner/Broker *", "client_status", "combo", "O", OWNER_BROKER_OPTIONS, required=True))
    return fields


def owner_broker_availability_fields(name_key: str, property_key: str, amount_key: str) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, name_label="Name *")
    fields.insert(2, FieldSpec("Owner/Broker *", "client_broker", "combo", "O", OWNER_BROKER_OPTIONS, required=True))
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields


def deal_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def deal_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks",
    ]


def owner_broker_availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", amount_key,
        "floor", "location", "facilities", "client_broker",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def owner_broker_availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", amount_key,
        "floor", "location", "facilities", "client_broker",
        "bachelor_family", "remarks",
    ]


def property_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Property Code", "property_code", "entry", lambda: gen_id("PROP")),
        FieldSpec("Title *", "title", required=True),
        FieldSpec("Type", "property_type", "combo", options=["Apartment", "House", "Villa", "Studio", "Shop", "Office", "Warehouse", "Plot"]),
        FieldSpec("Status", "status", "combo", "Available", ["Available", "Rented", "Sold", "Reserved"]),
        FieldSpec("Owner Name", "owner_name"),
        FieldSpec("Owner Contact", "owner_contact"),
        FieldSpec("Location *", "location", "autocomplete", options=COMMON_AREAS, required=True),
        FieldSpec("Area", "area"),
        FieldSpec("Floor", "floor", "combo_other", options=["Ground", "1st", "2nd", "3rd", "4th", "5th", "Top"]),
        FieldSpec("Monthly Rent", "monthly_rent", numeric=True),
        FieldSpec("Sale Price", "sale_price", numeric=True),
        FieldSpec("Maintenance", "maintenance_charge", numeric=True),
        FieldSpec("Facilities", "facilities", "facilities", options=FACILITY_OPTIONS),
        FieldSpec("Description", "description", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("property_code", "Code", width=110),
        ColumnSpec("title", "Title", width=180), ColumnSpec("property_type", "Type", width=110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("owner_name", "Owner", width=150),
        ColumnSpec("location", "Location", width=160), ColumnSpec("monthly_rent", "Rent", m, 110),
        ColumnSpec("sale_price", "Sale Price", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
        ColumnSpec("facilities", "Facilities", width=220), ColumnSpec("description", "Description", width=240),
    ]
    insert = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description", "created_at"]
    update = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description"]
    return TableSpec("Properties", "properties", cols, fields, insert, update, permission="properties")


def client_spec() -> TableSpec:
    fields = [
        FieldSpec("Client Name *", "client_name", required=True),
        FieldSpec("Phone", "phone"),
        FieldSpec("Email", "email"),
        FieldSpec("Address", "address", "text"),
        FieldSpec("Client Type", "client_type", "combo", "Tenant", ["Tenant", "Buyer", "Seller", "Investor", "Other"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Inactive"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("client_name", "Name", width=180),
        ColumnSpec("phone", "Phone", width=130),
        ColumnSpec("email", "Email", width=180), ColumnSpec("client_type", "Type", width=110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("address", "Address", width=220),
        ColumnSpec("notes", "Notes", width=240),
    ]
    insert = ["client_name", "phone", "email", "address", "client_type", "status", "notes", "created_at"]
    update = ["client_name", "phone", "email", "address", "client_type", "status", "notes"]
    return TableSpec("Clients", "clients", cols, fields, insert, update, permission="clients")


def income_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Date *", "transaction_date", "date", required=True),
        FieldSpec("Income Type *", "income_type", "combo", options=["Rent", "Deposit", "Maintenance", "Commission", "Utility", "Advance", "Other"], required=True),
        FieldSpec("Amount *", "amount", numeric=True, required=True),
        FieldSpec("Client Name", "tenant_name"),
        FieldSpec("Description", "description"),
        FieldSpec("Receipt No", "receipt_no", "entry", lambda: gen_id("RCP")),
        FieldSpec("Payment Method", "payment_method", "combo", "Cash", ["Cash", "Cheque", "Bank Transfer", "Online"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("transaction_date", "Date", format_date_display, 100),
        ColumnSpec("income_type", "Type", width=130), ColumnSpec("amount", "Amount", m, 120),
        ColumnSpec("tenant_name", "Client", width=150), ColumnSpec("description", "Description", width=220),
        ColumnSpec("receipt_no", "Receipt No", width=120), ColumnSpec("payment_method", "Method", width=120),
    ]
    insert = ["transaction_date", "income_type", "amount", "tenant_name", "description", "receipt_no", "payment_method", "created_by", "created_at"]
    update = ["transaction_date", "income_type", "amount", "tenant_name", "description", "receipt_no", "payment_method"]
    return TableSpec("Income", "income_transactions", cols, fields, insert, update, permission="financial")


def expense_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Date *", "transaction_date", "date", required=True),
        FieldSpec("Category *", "expense_category", "combo", options=["Maintenance", "Utilities", "Repair", "Salary", "Commission", "Tax", "Legal", "Marketing", "Other"], required=True),
        FieldSpec("Amount *", "amount", numeric=True, required=True),
        FieldSpec("Vendor Name", "vendor_name"),
        FieldSpec("Description", "description"),
        FieldSpec("Invoice No", "invoice_no", "entry", lambda: gen_id("INV")),
        FieldSpec("Payment Method", "payment_method", "combo", "Cash", ["Cash", "Cheque", "Bank Transfer", "Online"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("transaction_date", "Date", format_date_display, 100),
        ColumnSpec("expense_category", "Category", width=130), ColumnSpec("amount", "Amount", m, 120),
        ColumnSpec("vendor_name", "Vendor", width=150), ColumnSpec("description", "Description", width=220),
        ColumnSpec("invoice_no", "Invoice No", width=120), ColumnSpec("payment_method", "Method", width=120),
    ]
    insert = ["transaction_date", "expense_category", "amount", "vendor_name", "description", "invoice_no", "payment_method", "created_by", "created_at"]
    update = ["transaction_date", "expense_category", "amount", "vendor_name", "description", "invoice_no", "payment_method"]
    return TableSpec("Expenses", "expense_transactions", cols, fields, insert, update, permission="financial")


def employee_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    pct = lambda value, _symbol: f"{safe_float(value):.1f}%"
    fields = [
        FieldSpec("Employee ID", "employee_id", "entry", lambda: gen_id("EMP")),
        FieldSpec("Full Name *", "full_name", required=True),
        FieldSpec("Phone", "phone"),
        FieldSpec("Email", "email"),
        FieldSpec("Position *", "position", "combo_other", options=["Agent", "Manager", "Broker", "Admin", "Staff", "Driver", "Security", "Cleaner"], required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Rentals", "Administration", "Finance", "Operations"]),
        FieldSpec("Hire Date", "hire_date", "date"),
        FieldSpec("Base Salary *", "base_salary", numeric=True, required=True),
        FieldSpec("Commission %", "commission_rate", "entry", "5.0", numeric=True),
        FieldSpec("Address", "address", "text"),
        FieldSpec("Notes", "notes", "text"),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Inactive", "On Leave", "Terminated"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("employee_id", "Emp ID", width=110),
        ColumnSpec("full_name", "Name", width=170), ColumnSpec("position", "Position", width=130),
        ColumnSpec("department", "Department", width=130), ColumnSpec("phone", "Phone", width=130),
        ColumnSpec("base_salary", "Salary", m, 120), ColumnSpec("commission_rate", "Commission", pct, 110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("notes", "Notes", width=220),
    ]
    insert = ["employee_id", "full_name", "phone", "email", "position", "department", "hire_date", "base_salary", "commission_rate", "address", "notes", "status", "created_at"]
    update = ["employee_id", "full_name", "phone", "email", "position", "department", "hire_date", "base_salary", "commission_rate", "address", "notes", "status"]
    return TableSpec("Employees", "employees", cols, fields, insert, update, permission="employees")


def salary_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("full_name", "Employee", width=170),
        ColumnSpec("month", "Month", width=110), ColumnSpec("year", "Year", width=80),
        ColumnSpec("base_salary", "Base Salary", m, 120), ColumnSpec("bonus", "Bonus", m, 110),
        ColumnSpec("deductions", "Deductions", m, 120), ColumnSpec("net_salary", "Net Salary", m, 120),
        ColumnSpec("payment_method", "Method", width=120),
    ]
    return TableSpec("Salary History", "salary_payments", cols, [], [], [], permission="employees")


APP_STYLE = """
QMainWindow { background: #eef2f7; }
QStatusBar#AppStatusBar {
    background: #f8fafc;
    color: #475569;
    border-top: 1px solid #cbd5e1;
}
QLabel#StatusBarLabel {
    color: #334155;
    padding: 0 8px;
    font-size: 11px;
}
#Sidebar {
    background: #101827;
    border: none;
}
#BrandCard {
    background: #172338;
    border: 1px solid #263650;
    border-radius: 10px;
}
#LogoBadge {
    background: #2563eb;
    color: #ffffff;
    border-radius: 8px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    font-size: 15px;
    font-weight: 900;
}
#LogoImage {
    background: transparent;
    border: none;
}
#Brand {
    color: #ffffff;
    font-size: 19px;
    font-weight: 900;
}
#SidebarSubtle {
    color: #91a4c0;
    font-size: 12px;
}
#SidebarStatusText {
    color: #dbeafe;
    font-size: 12px;
    font-weight: 800;
}
#UserCard {
    background: #0f172a;
    border: 1px solid #263650;
    border-radius: 10px;
}
#SidebarUserName {
    color: #ffffff;
    font-size: 14px;
    font-weight: 800;
}
#RolePill {
    background: #e0f2fe;
    color: #075985;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 800;
}
#NavShell {
    background: transparent;
    border: none;
}
QScrollArea#SidebarNavScroll {
    background: transparent;
    border: none;
}
QScrollArea#SidebarNavScroll QScrollBar:vertical {
    background: #0f172a;
    border: none;
    border-radius: 4px;
    width: 8px;
    margin: 4px 0 4px 0;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 34px;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollArea#SidebarNavScroll QScrollBar::add-line:vertical,
QScrollArea#SidebarNavScroll QScrollBar::sub-line:vertical {
    height: 0;
}
#NavSeparator {
    background: #22324c;
    border: none;
    min-height: 1px;
    max-height: 1px;
    margin: 8px 8px 5px 8px;
}
#NavSection {
    color: #7f93b2;
    font-size: 10px;
    font-weight: 900;
    padding: 8px 8px 2px 8px;
}
QFrame#NavItem {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
}
QFrame#NavItem:hover {
    background: #18243a;
    border-color: #2b3d5a;
}
QFrame#NavItem[active="true"] {
    background: #2563eb;
    border-color: #3b82f6;
}
QFrame#NavItem:hover QLabel#NavText {
    color: #ffffff;
}
QFrame#NavItem:hover QLabel#NavIcon {
    background: #263956;
}
#NavIndicator {
    background: transparent;
    border-radius: 2px;
}
#NavIndicator[active="true"] {
    background: #bfdbfe;
}
QLabel#NavIcon {
    background: #1e2b42;
    color: #dbeafe;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 900;
}
QLabel#NavIcon[active="true"] {
    background: #dbeafe;
    color: #1d4ed8;
}
QLabel#NavText {
    color: #dbeafe;
    font-size: 13px;
    font-weight: 800;
}
QLabel#NavText[active="true"] {
    color: #ffffff;
}
#SidebarFooter {
    background: #0f172a;
    border: 1px solid #263650;
    border-radius: 10px;
}
#StatusDot {
    background: #22c55e;
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}
#SidebarLogout {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 9px 12px;
    font-weight: 800;
}
#SidebarLogout:hover {
    background: #eff6ff;
    border-color: #93c5fd;
}
#Content { background: #eef2f7; }
#TopTitle { color: #0f172a; font-size: 18px; font-weight: 800; }
#PageTitle { color: #0f172a; font-size: 24px; font-weight: 800; }
#SectionTitle { color: #0f172a; font-size: 17px; font-weight: 800; }
#MetricCard, #Panel {
    background: white;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#MetricTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
}
#MetricValue { color: #0f172a; font-size: 27px; font-weight: 900; }
#MetricNote { color: #64748b; font-size: 12px; }
#LoginTitle { color: #0f172a; font-size: 28px; font-weight: 900; }
#StartupDialog {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
}
#StartupTitle {
    color: #0f172a;
    font-size: 22px;
    font-weight: 900;
}
QProgressBar {
    background: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    font-weight: 800;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 5px;
}
#MutedText { color: #64748b; }
#SelectionCount {
    color: #64748b;
    font-size: 12px;
    font-weight: 800;
}
QTableWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #dbeafe;
}
QTableWidget { padding: 0; gridline-color: #e2e8f0; }
QTableWidget::item {
    color: #0f172a;
    padding: 5px;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #334155;
    border: none;
    border-bottom: 1px solid #d9e2ef;
    padding: 8px;
    font-weight: 800;
}
QPushButton {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover { background: #f8fafc; }
#AccentButton {
    background: #2563eb;
    color: white;
    border: 1px solid #2563eb;
}
#AccentButton:hover { background: #1d4ed8; }
#DangerButton {
    background: #dc2626;
    color: white;
    border: 1px solid #dc2626;
}
#DangerButton:hover { background: #b91c1c; }
#FacilitiesBox {
    background: #f8fafc;
    border: 1px solid #d9e2ef;
    border-radius: 6px;
}
QRadioButton#FacilityCheck {
    background: #e5e7eb;
    color: #0f172a;
    border-radius: 2px;
    padding: 4px 7px;
    font-weight: 700;
    spacing: 6px;
}
QRadioButton#FacilityCheck:hover {
    background: #dbeafe;
}
QRadioButton#FacilityCheck::indicator {
    width: 14px;
    height: 14px;
}
QTabWidget::pane {
    border: 1px solid #d9e2ef;
    background: #ffffff;
    border-radius: 8px;
}
QTabBar::tab {
    background: #f8fafc;
    padding: 9px 14px;
    border: 1px solid #d9e2ef;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #2563eb;
    font-weight: 800;
}
"""


def main() -> int:
    if not PYSIDE_AVAILABLE:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        return 1
    app = QApplication(sys.argv)
    app.setWindowIcon(crm_app_icon())
    app.setStyleSheet(APP_STYLE)
    splash: StartupDialog | None = None
    try:
        splash = StartupDialog()
        splash.show()
        splash.set_progress(8, "Starting application")
        splash.set_progress(18, "Preparing database")
        ensure_database()
        splash.set_progress(38, "Loading services")
        services = CRMServices()
        splash.set_progress(48, "Opening login")
        splash.close()

        login = LoginDialog(services)
        if login.exec() != QDialog.Accepted or not login.current_user:
            return 0

        splash = StartupDialog("Loading Real Estate CRM")
        splash.show()
        splash.set_progress(52, "Signing in")
        window = ModernCRMWindow(services, login.current_user, startup_progress=splash.set_progress)
        splash.set_progress(100, "Ready")
        window.show()
        splash.close()
        return app.exec()
    except Exception as exc:
        if splash:
            splash.close()
        QMessageBox.critical(None, "Startup Error", f"Real Estate CRM could not start:\n\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
