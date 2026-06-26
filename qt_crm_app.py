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
from crm_core.attendance import ATTENDANCE_STATUSES, LEAVE_TYPES, calculate_attendance, format_minutes, summarize_attendance
from crm_core.constants import (
    EXPENSE_CATEGORIES,
    normalize_availability_status,
    normalize_contact_role,
    DEAL_STAGES,
    DEAL_TABLES,
    PHASE1_TABLES,
    COMMON_AREAS,
    FACILITY_OPTIONS,
    FACILITY_ALIASES,
    FLOOR_OPTIONS,
    PROPERTY_TYPE_OPTIONS,
    MEASUREMENT_UNIT_OPTIONS,
    OWNER_BROKER_OPTIONS,
    FAMILY_OPTIONS,
    CLOSED_AVAILABILITY_ARCHIVES,
    ROLE_PERMISSIONS,
    has_permission,
    is_admin_role,
)
from crm_core.date_utils import DateUtils
from crm_core.db import SQLiteRepository
from crm_core.ecosystem import collect_ecosystem_health, format_ecosystem_report
from crm_core.formatters import format_currency, parse_currency
from crm_core.reports import (
    ReportResult,
    ReportService,
    export_report_csv,
    export_report_pdf,
    export_report_text,
)
from crm_core.validators import PhoneValidator

try:
    # FIX: Removed any whitespace inside QMarginsF
    from PySide6.QtCore import QDate, QEvent, QMarginsF, QPointF, QRectF, Qt, Signal
    from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QPageLayout, QPageSize, QPainter, QPen, QPixmap, QTextDocument
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
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
        QListWidget,
        QListWidgetItem,
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


# NOTE: Common constants are now imported from crm_core.constants
SF_TABLES = {
    "sf_employees", "sf_positions", "sf_performance_goals", "sf_must_win_battles",
    "sf_kpis", "sf_learning", "sf_recruiting", "sf_compensation", "sf_onboarding",
}
WF_TABLES = {
    "wf_workflows", "wf_workflow_steps", "wf_instances", "wf_tasks",
    "wf_approvals", "wf_notifications", "wf_sla_log", "wf_audit_log",
}
READ_ONLY_API_TABLES = {"wf_instances", "wf_approvals", "wf_sla_log", "wf_audit_log"}
PARENT_CHILD_TABLES = {
    "employees": (("attendance", "employee_id"), ("salary_payments", "employee_id")),
    "sf_employees": (
        ("sf_performance_goals", "employee_id"),
        ("sf_learning", "employee_id"),
        ("sf_compensation", "employee_id"),
        ("sf_onboarding", "employee_id"),
    ),
    "wf_workflows": (("wf_workflow_steps", "workflow_id"), ("wf_instances", "workflow_id")),
    "wf_instances": (("wf_tasks", "instance_id"), ("wf_sla_log", "instance_id")),
    "wf_tasks": (("wf_approvals", "task_id"), ("wf_sla_log", "task_id")),
}
BACKUP_DIR = APP_ROOT / "backups"
LONG_TEXT_COLUMN_KEYS = {"facilities", "remarks", "description", "notes", "address", "office_address", "home_address"}
GLOBAL_SEARCH_HIDDEN_COLUMNS = {"password_hash"}
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
# NOTE: STAGE_PROBABILITY and DEAL_TABLES are now imported from crm_core.constants
GLOBAL_SEARCH_SOURCES = [
    ("Rent Requirement", "rent_requirements"),
    ("Rent Availability", "rent_availability"),
    ("Rented Property", "rented_properties"),
    ("Sale Requirement", "sale_requirements"),
    ("Sale Availability", "sale_availability"),
    ("Sold Property", "sold_properties"),
    ("Client", "clients"),
    ("Broker Contact", "broker_contacts"),
    ("Property", "properties"),
    ("Employee", "employees"),
    ("Income", "income_transactions"),
    ("Expense", "expense_transactions"),
    ("Attendance", "attendance"),
    ("Salary Payment", "salary_payments"),
    ("SF Employee", "sf_employees"),
    ("SF Recruiting", "sf_recruiting"),
    ("SF Performance Goal", "sf_performance_goals"),
    ("SF Must Win Battle", "sf_must_win_battles"),
    ("SF KPI", "sf_kpis"),
    ("SF Learning", "sf_learning"),
    ("SF Onboarding", "sf_onboarding"),
    ("Workflow Instance", "wf_instances"),
    ("Workflow Task", "wf_tasks"),
    ("Workflow Approval", "wf_approvals"),
]
GLOBAL_SEARCH_SOURCE_LABELS = dict(GLOBAL_SEARCH_SOURCES)
FIND_SOURCE_ORDER = {table: index for index, (_label, table) in enumerate(GLOBAL_SEARCH_SOURCES)}
FIND_SOURCE_PERMISSIONS = {
    "rent_requirements": ("rent", "rent_view"),
    "rent_availability": ("rent", "rent_view"),
    "rented_properties": ("rent", "rent_view"),
    "sale_requirements": ("sale", "sale_view"),
    "sale_availability": ("sale", "sale_view"),
    "sold_properties": ("sale", "sale_view"),
    "clients": ("clients", "clients_view"),
    "broker_contacts": ("clients", "clients_view"),
    "properties": ("properties", "properties_view"),
    "employees": ("employees", "employees_view"),
    "income_transactions": ("financial", "financial_view"),
    "expense_transactions": ("financial", "financial_view"),
    "attendance": ("employees", "employees_view"),
    "salary_payments": ("employees", "employees_view"),
    "sf_employees": ("successfactors", "sf_view"),
    "sf_recruiting": ("successfactors", "sf_view"),
    "sf_performance_goals": ("successfactors", "sf_view"),
    "sf_must_win_battles": ("successfactors", "sf_view"),
    "sf_kpis": ("successfactors", "sf_view"),
    "sf_learning": ("successfactors", "sf_view"),
    "sf_onboarding": ("successfactors", "sf_view"),
    "wf_instances": ("workflow", "wf_view"),
    "wf_tasks": ("workflow", "wf_view"),
    "wf_approvals": ("workflow", "wf_view"),
}
FIND_RESULT_COLUMNS = {
    "rent_requirements": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_created", "created_at"), ""),
        ("client_name", "Name", ("client_name",), ""),
        ("client_status", "Status", ("client_status", "client_broker", "broker", "preferred_broker"), "Client"),
        ("contact", "Contact No.", ("contact_phone", "contact"), ""),
        ("property_requires", "Property Required / Needed", ("property_requires", "property_type"), ""),
        ("size", "Rooms", ("size", "size_beds"), ""),
        ("measurement", "Measurement", ("measurement", "sq_ft", "sq_ft_yards"), ""),
        ("measurement_unit", "Size", ("measurement_unit", "area_unit", "size_unit"), ""),
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
        ("broker", "Status", ("client_broker", "broker", "posted_by_broker", "posted_by"), "Owner"),
        ("contact", "Contact No.", ("owner_phone", "contact_phone", "contact"), ""),
        ("property_availability", "Property Available", ("property_availability", "property_type"), ""),
        ("size", "Rooms", ("size", "size_beds"), ""),
        ("measurement", "Measurement", ("measurement", "sq_ft", "sq_ft_yards"), ""),
        ("measurement_unit", "Size", ("measurement_unit", "area_unit", "size_unit"), ""),
        ("monthly_rent", "Rent", ("monthly_rent",), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
    "broker_contacts": [
        ("id", "Sr. No", ("id",), ""),
        ("name", "Name", ("name",), ""),
        ("contact", "Contact", ("contact", "phone", "contact_phone"), ""),
        ("area", "Area", ("area", "location"), ""),
        ("office_address", "Office Address", ("office_address",), ""),
        ("home_address", "Home Address", ("home_address",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
    "sale_requirements": [
        ("id", "Sr No.", ("id",), ""),
        ("date", "Date", ("date", "date_created", "created_at"), ""),
        ("client_name", "Name", ("client_name",), ""),
        ("client_status", "Status", ("client_status", "client_broker", "broker", "preferred_broker"), "Client"),
        ("contact", "Contact No.", ("contact_phone", "contact"), ""),
        ("property_requires", "Property Required / Needed", ("property_requires", "property_type"), ""),
        ("size", "Rooms", ("size", "size_beds"), ""),
        ("measurement", "Measurement", ("measurement", "sq_ft", "sq_ft_yards"), ""),
        ("measurement_unit", "Size", ("measurement_unit", "area_unit", "size_unit"), ""),
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
        ("broker", "Status", ("client_broker", "broker", "posted_by_broker", "posted_by"), "Owner"),
        ("contact", "Contact No.", ("owner_phone", "contact_phone", "contact"), ""),
        ("property_availability", "Property Available", ("property_availability", "property_type"), ""),
        ("size", "Rooms", ("size", "size_beds"), ""),
        ("measurement", "Measurement", ("measurement", "sq_ft", "sq_ft_yards"), ""),
        ("measurement_unit", "Size", ("measurement_unit", "area_unit", "size_unit"), ""),
        ("demand", "Demand", ("demand", "asking_price"), ""),
        ("floor", "Floor", ("floor", "floor_no"), ""),
        ("location", "Location", ("location",), ""),
        ("facilities", "Facilities", ("facilities",), ""),
        ("remarks", "Remarks", ("remarks", "description", "notes"), ""),
    ],
}
FIND_ALL_COLUMN_ORDER = [
    "_source", "id", "date", "client_name", "owner_name", "name", "client_status", "broker",
    "contact", "property_requires", "property_availability", "size", "measurement",
    "measurement_unit", "budget", "monthly_rent", "demand", "floor", "location", "area",
    "facilities", "office_address", "home_address", "remarks",
]
FIND_ALL_COLUMN_LABELS = {
    "_source": "Type",
    "id": "Sr No.",
    "date": "Date",
    "client_name": "Name",
    "owner_name": "Name",
    "name": "Name",
    "client_status": "Status",
    "broker": "Status",
    "contact": "Contact No.",
    "property_requires": "Property Required / Needed",
    "property_availability": "Property Available",
    "size": "Rooms",
    "measurement": "Measurement",
    "measurement_unit": "Size",
    "budget": "Budget",
    "monthly_rent": "Rent",
    "demand": "Demand",
    "floor": "Floor",
    "location": "Location",
    "area": "Area",
    "facilities": "Facilities",
    "office_address": "Office Address",
    "home_address": "Home Address",
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
PHONE_FORM_KEYS = {"contact", "contact_phone", "owner_phone", "phone", "owner_contact", "company_phone"}
CNIC_FORM_KEYS = {"cnic"}
PERCENT_FORM_KEYS = {"commission_rate", "deal_probability", "default_commission", "tax_rate"}

# NOTE: ROLE_PERMISSIONS, has_permission(), is_admin_role() are now imported from crm_core.constants


def normalize_setting_lines(value: object, defaults: list[str]) -> list[str]:
    raw = str(value or "").strip()
    lines = [line.strip() for line in raw.replace(",", "\n").splitlines()]
    values = [line for line in lines if line]
    if len(values) == 1 and defaults:
        packed = re.sub(r"\s+", " ", values[0].strip().lower())
        unpacked = [
            option
            for option in defaults
            if re.sub(r"\s+", " ", option.strip().lower()) in packed
        ]
        if len(unpacked) > 1:
            return unpacked
    return values or list(defaults)


def setting_lines(services: "CRMServices", key: str, defaults: list[str]) -> list[str]:
    return normalize_setting_lines(services.settings_get(key, "\n".join(defaults)), defaults)


def setting_lines_text(value: object, defaults: list[str]) -> str:
    return "\n".join(normalize_setting_lines(value, defaults))


def allowed_find_sources(role: str, *, staff_restricted: bool = False) -> list[tuple[str, str]]:
    if staff_restricted:
        return [
            (label, table)
            for label, table in GLOBAL_SEARCH_SOURCES
            if table in PHASE1_TABLES
            or any(has_permission(role, permission) for permission in FIND_SOURCE_PERMISSIONS.get(table, ()))
        ]
    return [
        (label, table)
        for label, table in GLOBAL_SEARCH_SOURCES
        if any(has_permission(role, permission) for permission in FIND_SOURCE_PERMISSIONS.get(table, ()))
    ]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        parsed = parse_currency(value)
        if parsed is None:
            return default
        return float(parsed)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


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
    parsed = DateUtils.parse_date(text)
    if parsed:
        return datetime(parsed.year, parsed.month, parsed.day)
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


def quote_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


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
    try:
        PhoneValidator.validate_phone(text)
        return True
    except ValueError:
        return False


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
        raise ValueError(f"{clean_label} must be 03001234567 or +923001234567.")
    if key in CNIC_FORM_KEYS and text and not is_valid_cnic_text(text):
        raise ValueError(f"{clean_label} must contain exactly 13 digits.")
    if key in PERCENT_FORM_KEYS and text and is_valid_number_text(text):
        number = safe_float(text)
        if number < 0 or number > 100:
            raise ValueError(f"{clean_label} must be between 0 and 100.")
    if strict_options and text and options and text not in options:
        raise ValueError(f"Please select a valid option for {clean_label}.")


def money(value: Any, symbol: str = "Rs.") -> str:
    return format_currency(value, symbol)


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


def parse_multi_options(value: Any, options: list[str] | None = None) -> list[str]:
    option_list = options or []
    lookup = {normalize_text(option): option for option in option_list}
    selected: list[str] = []
    seen: set[str] = set()
    if isinstance(value, (list, tuple, set)):
        tokens = [str(item) for item in value]
    else:
        tokens = re.split(r"[,;|\n]+", str(value or ""))
    for token in tokens:
        clean = str(token or "").strip()
        if not clean:
            continue
        label = lookup.get(normalize_text(clean), clean)
        key = normalize_text(label)
        if key and key not in seen:
            selected.append(label)
            seen.add(key)
    return selected


def multi_option_overlap(left: Any, right: Any, options: list[str] | None = None) -> set[str]:
    left_values = {normalize_text(label) for label in parse_multi_options(left, options)}
    right_values = {normalize_text(label) for label in parse_multi_options(right, options)}
    return {label for label in left_values & right_values if label}


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
    import professional_crm

    professional_crm.DB_PATH = str(DB_PATH)
    professional_crm.Database.init_all()
    ensure_qt_schema()


def ensure_qt_schema() -> None:
    """Add Qt-screen columns that older deployed databases may be missing."""
    additions = {
        "rent_requirements": [
            ("client_status", "TEXT DEFAULT 'Client'"),
            ("broker", "TEXT"),
            ("contact_person", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_requires", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "rent_availability": [
            ("client_broker", "TEXT"),
            ("owner_phone", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_availability", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "sale_requirements": [
            ("client_status", "TEXT DEFAULT 'Client'"),
            ("broker", "TEXT"),
            ("contact_person", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_requires", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("maintenance_charge", "REAL DEFAULT 0"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "sale_availability": [
            ("client_broker", "TEXT"),
            ("owner_phone", "TEXT"),
            ("contact_phone", "TEXT"),
            ("property_availability", "TEXT"),
            ("size", "TEXT"),
            ("measurement", "TEXT"),
            ("measurement_unit", "TEXT"),
            ("status", "TEXT DEFAULT 'Available'"),
            ("persons", "TEXT"),
            ("building_name", "TEXT"),
            ("maintenance_charge", "REAL DEFAULT 0"),
            ("is_deleted", "INTEGER DEFAULT 0"),
            ("deleted_by", "TEXT"),
            ("deleted_at", "TEXT"),
            ("last_edited_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
        "attendance": [
            ("shift_name", "TEXT DEFAULT 'Office'"),
            ("scheduled_start", "TEXT DEFAULT '09:30'"),
            ("scheduled_end", "TEXT DEFAULT '18:00'"),
            ("leave_type", "TEXT"),
            ("worked_minutes", "INTEGER DEFAULT 0"),
            ("late_minutes", "INTEGER DEFAULT 0"),
            ("early_leave_minutes", "INTEGER DEFAULT 0"),
            ("overtime_minutes", "INTEGER DEFAULT 0"),
            ("approved_by", "TEXT"),
            ("last_edited_at", "TEXT"),
        ],
    }
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA wal_autocheckpoint=1000")
        cur.execute("PRAGMA synchronous=FULL")
        cur.execute("PRAGMA cache_size=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        for table, columns in additions.items():
            existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
            for column, column_type in columns:
                if column not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                    existing.add(column)
            if "is_deleted" in existing:
                cur.execute(f"UPDATE {table} SET is_deleted=0 WHERE is_deleted IS NULL")
            if table in {"rent_requirements", "sale_requirements"}:
                if "client_status" in existing:
                    cur.execute(
                        f"""UPDATE {table}
                            SET client_status=CASE
                                WHEN LOWER(client_status) IN ('o', 'owner') THEN 'Owner'
                                WHEN LOWER(client_status) IN ('b', 'broker') THEN 'Broker'
                                WHEN client_status IS NULL OR client_status='' THEN 'Client'
                            ELSE client_status
                            END"""
                    )
                if {"client_name", "contact_person"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_person=client_name "
                        "WHERE (contact_person IS NULL OR contact_person='') AND client_name IS NOT NULL"
                    )
                if {"contact", "contact_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_phone=contact "
                        "WHERE (contact_phone IS NULL OR contact_phone='') AND contact IS NOT NULL AND contact<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET contact=contact_phone "
                        "WHERE (contact IS NULL OR contact='') AND contact_phone IS NOT NULL AND contact_phone<>''"
                    )
                if {"budget", "budget_max"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET budget=budget_max "
                        "WHERE (budget IS NULL OR budget=0) AND budget_max IS NOT NULL AND budget_max<>0"
                    )
                if {"budget", "budget_min"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET budget=budget_min "
                        "WHERE (budget IS NULL OR budget=0) AND budget_min IS NOT NULL AND budget_min<>0"
                    )
                if {"property_requires", "property_type"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_requires=property_type "
                        "WHERE (property_requires IS NULL OR property_requires='') AND property_type IS NOT NULL AND property_type<>''"
                    )
                if {"property_requires", "property_requirement"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_requires=property_requirement "
                        "WHERE (property_requires IS NULL OR property_requires='') AND property_requirement IS NOT NULL AND property_requirement<>''"
                    )
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
            if table in {"rent_availability", "sale_availability"} and "client_broker" in existing:
                cur.execute(
                    f"""UPDATE {table}
                        SET client_broker=CASE
                            WHEN LOWER(client_broker) IN ('o', 'owner') THEN 'Owner'
                            WHEN LOWER(client_broker) IN ('b', 'broker') THEN 'Broker'
                            WHEN client_broker IS NULL OR client_broker='' THEN 'Owner'
                            ELSE client_broker
                        END"""
                )
                if {"contact", "owner_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET owner_phone=contact "
                        "WHERE (owner_phone IS NULL OR owner_phone='') AND contact IS NOT NULL AND contact<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET contact=owner_phone "
                        "WHERE (contact IS NULL OR contact='') AND owner_phone IS NOT NULL AND owner_phone<>''"
                    )
                if {"contact_phone", "owner_phone"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET contact_phone=owner_phone "
                        "WHERE (contact_phone IS NULL OR contact_phone='') AND owner_phone IS NOT NULL AND owner_phone<>''"
                    )
                    cur.execute(
                        f"UPDATE {table} SET owner_phone=contact_phone "
                        "WHERE (owner_phone IS NULL OR owner_phone='') AND contact_phone IS NOT NULL AND contact_phone<>''"
                    )
                if "status" in existing:
                    cur.execute(
                        f"""UPDATE {table}
                            SET status=CASE
                                WHEN status IS NULL OR status='' THEN 'Available'
                                WHEN LOWER(status)='available' THEN 'Available'
                                WHEN LOWER(status)='reserved' THEN 'Reserved'
                                WHEN LOWER(status)='hold' THEN 'Reserved'
                                WHEN LOWER(status)='withdrawn' THEN 'Withdrawn'
                                WHEN LOWER(status)='inactive' THEN 'Inactive'
                                WHEN LOWER(status) IN ('sold', 'sale') THEN 'Sold'
                                WHEN LOWER(status) IN ('rented', 'rent') THEN 'Rented'
                                ELSE status
                            END"""
                    )
                    if table == "rent_availability":
                        cur.execute(f"UPDATE {table} SET status='Available' WHERE status='Sold'")
                    elif table == "sale_availability":
                        cur.execute(f"UPDATE {table} SET status='Available' WHERE status='Rented'")
                if {"property_availability", "property_type"} <= existing:
                    cur.execute(
                        f"UPDATE {table} SET property_availability=property_type "
                        "WHERE (property_availability IS NULL OR property_availability='') AND property_type IS NOT NULL AND property_type<>''"
                    )
            if {"size", "size_beds"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET size=size_beds "
                    "WHERE (size IS NULL OR size='') AND size_beds IS NOT NULL AND size_beds<>''"
                )
            if {"measurement", "sq_ft"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement=sq_ft "
                    "WHERE (measurement IS NULL OR measurement='') AND sq_ft IS NOT NULL AND sq_ft<>''"
                )
            if {"measurement", "sq_ft_yards"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement=sq_ft_yards "
                    "WHERE (measurement IS NULL OR measurement='') AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"
                )
            if {"measurement_unit", "sq_ft_yards"} <= existing:
                cur.execute(
                    f"""UPDATE {table}
                        SET measurement_unit=CASE
                            WHEN LOWER(sq_ft_yards) LIKE '%yard%' OR LOWER(sq_ft_yards) LIKE '%yd%' THEN 'Yards'
                            ELSE 'Sq Ft'
                        END
                        WHERE (measurement_unit IS NULL OR measurement_unit='')
                          AND sq_ft_yards IS NOT NULL AND sq_ft_yards<>''"""
                )
            if {"measurement_unit", "sq_ft"} <= existing:
                cur.execute(
                    f"UPDATE {table} SET measurement_unit='Sq Ft' "
                    "WHERE (measurement_unit IS NULL OR measurement_unit='') AND sq_ft IS NOT NULL AND sq_ft<>''"
                )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS broker_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                contact TEXT,
                area TEXT,
                office_address TEXT,
                home_address TEXT,
                remarks TEXT,
                created_at TEXT
            )
            """
        )
        broker_existing = {row[1] for row in cur.execute("PRAGMA table_info(broker_contacts)")}
        for column, column_type in (
            ("name", "TEXT"),
            ("contact", "TEXT"),
            ("area", "TEXT"),
            ("office_address", "TEXT"),
            ("home_address", "TEXT"),
            ("remarks", "TEXT"),
            ("created_at", "TEXT"),
        ):
            if column not in broker_existing:
                cur.execute(f"ALTER TABLE broker_contacts ADD COLUMN {column} {column_type}")
                broker_existing.add(column)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_area ON broker_contacts(area)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_office_address ON broker_contacts(office_address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_broker_contacts_home_address ON broker_contacts(home_address)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER,
                payload TEXT,
                requested_by TEXT,
                requested_at TEXT,
                status TEXT DEFAULT 'Pending',
                reviewed_by TEXT,
                reviewed_at TEXT,
                review_comment TEXT
            )
            """
        )
        archive_table_sql = """
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_table TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                deal_type TEXT,
                closed_status TEXT,
                closed_at TEXT,
                archived_at TEXT,
                archived_by TEXT,
                date TEXT,
                owner_name TEXT,
                owner_phone TEXT,
                contact_phone TEXT,
                contact TEXT,
                property_availability TEXT,
                size TEXT,
                measurement TEXT,
                measurement_unit TEXT,
                monthly_rent REAL DEFAULT 0,
                demand REAL DEFAULT 0,
                deposit REAL DEFAULT 0,
                maintenance_charge REAL DEFAULT 0,
                floor TEXT,
                location TEXT,
                bedrooms TEXT,
                bathrooms TEXT,
                furnishing TEXT,
                parking TEXT,
                nearby_landmarks TEXT,
                area_notes TEXT,
                verification_status TEXT,
                photo_paths TEXT,
                facilities TEXT,
                client_broker TEXT,
                bachelor_family TEXT,
                remarks TEXT,
                persons TEXT,
                building_name TEXT,
                workflow_stage TEXT DEFAULT 'Deal Done',
                priority TEXT DEFAULT 'Medium',
                assigned_to TEXT,
                deal_probability REAL DEFAULT 100,
                expected_close_value REAL DEFAULT 0,
                approval_status TEXT,
                created_by TEXT,
                created_at TEXT,
                original_payload TEXT,
                UNIQUE(source_table, source_id)
            )
        """
        for archive_table in ("rented_properties", "sold_properties"):
            cur.execute(archive_table_sql.format(table_name=archive_table))
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{archive_table}_closed_at "
                f"ON {archive_table}(closed_at)"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{archive_table}_location "
                f"ON {archive_table}(location)"
            )
        for source_table, (closed_status, archive_table, deal_type) in CLOSED_AVAILABILITY_ARCHIVES.items():
            source_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({source_table})")}
            archive_columns = {row[1] for row in cur.execute(f"PRAGMA table_info({archive_table})")}
            if not source_columns or not archive_columns:
                continue
            copy_columns = [
                column for column in (
                    "date", "owner_name", "owner_phone", "contact_phone", "contact",
                    "property_availability", "size", "measurement", "measurement_unit",
                    "monthly_rent", "demand", "deposit", "maintenance_charge", "floor",
                    "location", "bedrooms", "bathrooms", "furnishing", "parking",
                    "nearby_landmarks", "area_notes", "verification_status", "photo_paths",
                    "facilities", "client_broker", "bachelor_family", "remarks", "persons",
                    "building_name", "workflow_stage", "priority", "assigned_to",
                    "deal_probability", "expected_close_value", "approval_status",
                    "created_by", "created_at",
                )
                if column in source_columns and column in archive_columns
            ]
            insert_columns = [
                "source_table", "source_id", "deal_type", "closed_status",
                "closed_at", "archived_at", "archived_by",
                *copy_columns,
            ]
            select_values = [
                "?",
                "id",
                "?",
                "?",
                "COALESCE(CAST(closed_at AS TEXT), datetime('now'))" if "closed_at" in source_columns else "datetime('now')",
                "datetime('now')",
                "'migration'",
                *[quote_identifier(column) for column in copy_columns],
            ]
            cur.execute(
                f"""INSERT OR IGNORE INTO {archive_table}
                    ({', '.join(quote_identifier(column) for column in insert_columns)})
                    SELECT {', '.join(select_values)}
                    FROM {source_table}
                    WHERE LOWER(COALESCE(status,''))=LOWER(?)
                      AND COALESCE(is_deleted,0)=0""",
                (source_table, deal_type, closed_status, closed_status),
            )
            updates = ["is_deleted=1"]
            params: list[Any] = []
            if "deleted_by" in source_columns:
                updates.append("deleted_by=COALESCE(NULLIF(deleted_by,''), ?)")
                params.append("deal_archive")
            if "deleted_at" in source_columns:
                updates.append("deleted_at=COALESCE(deleted_at, ?)")
                params.append(datetime.now().isoformat(timespec="seconds"))
            if "workflow_stage" in source_columns:
                updates.append("workflow_stage='Deal Done'")
            if "deal_probability" in source_columns:
                updates.append("deal_probability=100")
            if "closed_at" in source_columns:
                updates.append("closed_at=COALESCE(closed_at, ?)")
                params.append(datetime.now().isoformat(timespec="seconds"))
            params.append(closed_status)
            cur.execute(
                f"""UPDATE {source_table}
                    SET {', '.join(updates)}
                    WHERE LOWER(COALESCE(status,''))=LOWER(?)
                      AND COALESCE(is_deleted,0)=0""",
                tuple(params),
            )
        # SuccessFactors tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_employee_id TEXT UNIQUE,
                full_name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                job_title TEXT,
                manager_name TEXT,
                hire_date TEXT,
                employment_status TEXT DEFAULT 'Active',
                location TEXT,
                cost_center TEXT,
                notes TEXT,
                synced_at TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_code TEXT UNIQUE,
                position_title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                headcount_max INTEGER DEFAULT 1,
                headcount_current INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Open',
                reports_to TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_performance_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                goal_title TEXT NOT NULL,
                goal_description TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'In Progress',
                progress_pct REAL DEFAULT 0,
                rating TEXT,
                review_period TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT,
                FOREIGN KEY (employee_id) REFERENCES sf_employees(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_must_win_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_code TEXT UNIQUE,
                battle_title TEXT NOT NULL,
                owner_name TEXT,
                department TEXT,
                objective TEXT,
                start_date TEXT,
                end_date TEXT,
                priority TEXT DEFAULT 'High',
                status TEXT DEFAULT 'Active',
                target_value REAL DEFAULT 0,
                current_value REAL DEFAULT 0,
                progress_pct REAL DEFAULT 0,
                business_impact TEXT,
                risks TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_kpis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kpi_code TEXT UNIQUE,
                kpi_name TEXT NOT NULL,
                employee_name TEXT,
                department TEXT,
                category TEXT,
                period TEXT,
                start_date TEXT,
                end_date TEXT,
                target_value REAL DEFAULT 0,
                actual_value REAL DEFAULT 0,
                unit TEXT,
                weight_pct REAL DEFAULT 0,
                achievement_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'On Track',
                owner_name TEXT,
                review_date TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_learning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                course_title TEXT NOT NULL,
                course_code TEXT,
                category TEXT,
                assigned_date TEXT,
                due_date TEXT,
                completion_date TEXT,
                status TEXT DEFAULT 'Assigned',
                score REAL,
                instructor TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_recruiting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_requisition_id TEXT,
                job_title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                hiring_manager TEXT,
                recruiter TEXT,
                open_date TEXT,
                close_date TEXT,
                status TEXT DEFAULT 'Open',
                applications_count INTEGER DEFAULT 0,
                shortlisted_count INTEGER DEFAULT 0,
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_compensation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                base_salary REAL DEFAULT 0,
                bonus REAL DEFAULT 0,
                allowances REAL DEFAULT 0,
                total_compensation REAL DEFAULT 0,
                currency TEXT DEFAULT 'PKR',
                effective_date TEXT,
                review_cycle TEXT,
                approved_by TEXT,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sf_onboarding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                employee_name TEXT,
                task_title TEXT NOT NULL,
                task_category TEXT,
                assigned_to TEXT,
                due_date TEXT,
                completion_date TEXT,
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Medium',
                notes TEXT,
                created_by TEXT,
                created_at TEXT
            )
            """
        )

        # Workflow Engine tables
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                workflow_type TEXT,
                description TEXT,
                trigger_event TEXT,
                status TEXT DEFAULT 'Active',
                version INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                step_order INTEGER DEFAULT 1,
                step_name TEXT NOT NULL,
                step_type TEXT,
                assignee_role TEXT,
                assignee_name TEXT,
                sla_hours INTEGER DEFAULT 24,
                action_on_approve TEXT,
                action_on_reject TEXT,
                is_conditional INTEGER DEFAULT 0,
                condition_field TEXT,
                condition_value TEXT,
                created_by TEXT,
                created_at TEXT,
                FOREIGN KEY (workflow_id) REFERENCES wf_workflows(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER,
                workflow_name TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                initiated_by TEXT,
                initiated_at TEXT,
                current_step INTEGER DEFAULT 1,
                current_assignee TEXT,
                status TEXT DEFAULT 'Running',
                due_at TEXT,
                completed_at TEXT,
                priority TEXT DEFAULT 'Normal',
                notes TEXT,
                FOREIGN KEY (workflow_id) REFERENCES wf_workflows(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER,
                workflow_name TEXT,
                step_name TEXT,
                assigned_to TEXT,
                assigned_at TEXT,
                due_at TEXT,
                completed_at TEXT,
                action_taken TEXT,
                comments TEXT,
                status TEXT DEFAULT 'Pending',
                priority TEXT DEFAULT 'Normal',
                reference_table TEXT,
                reference_id INTEGER,
                FOREIGN KEY (instance_id) REFERENCES wf_instances(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                workflow_name TEXT,
                approval_type TEXT,
                requested_by TEXT,
                requested_at TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                decision TEXT,
                comments TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                status TEXT DEFAULT 'Pending'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                channel TEXT DEFAULT 'In-App',
                sent_at TEXT,
                read_at TEXT,
                status TEXT DEFAULT 'Unread',
                reference_table TEXT,
                reference_id INTEGER,
                created_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_sla_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER,
                task_id INTEGER,
                sla_target_hours INTEGER,
                actual_hours REAL,
                breached INTEGER DEFAULT 0,
                logged_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wf_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                performed_by TEXT,
                performed_at TEXT,
                reference_table TEXT,
                reference_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                session_id TEXT
            )
            """
        )
        default_settings = {
            "phase1_areas": "\n".join(COMMON_AREAS),
            "phase1_facilities": "\n".join(FACILITY_OPTIONS),
            "phase1_floors": "\n".join(FLOOR_OPTIONS),
            "phase1_property_types": "\n".join(PROPERTY_TYPE_OPTIONS),
            "phase1_measurement_units": "\n".join(MEASUREMENT_UNIT_OPTIONS),
            "expense_categories": "\n".join(EXPENSE_CATEGORIES),
            "phase1_theme": "Light",
        }
        for key, value in default_settings.items():
            cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
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

    def settings_get(self, key: str, default: str = "") -> str:
        row = self.fetch_one("SELECT value FROM app_settings WHERE key=?", (key,))
        return str(row["value"]) if row else default

    def settings_set(self, key: str, value: str) -> None:
        self.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, value))

    def expense_categories(self) -> list[str]:
        return setting_lines(self, "expense_categories", list(EXPENSE_CATEGORIES))

    def table_columns(self, table: str) -> set[str]:
        return self.repo.table_columns(table)

    def submit_approval(
        self,
        action: str,
        table_name: str,
        record_id: int | None,
        payload: dict[str, Any],
        requested_by: str,
    ) -> int:
        return self.insert(
            """INSERT INTO pending_approvals
               (action, table_name, record_id, payload, requested_by, requested_at, status)
               VALUES (?,?,?,?,?,?, 'Pending')""",
            (action, table_name, record_id, json.dumps(payload, default=str), requested_by, datetime.now().isoformat(timespec="seconds")),
        )

    def pending_approvals(self) -> list[dict]:
        return self.fetch_all(
            """SELECT id, action, table_name, record_id, requested_by, requested_at, status
               FROM pending_approvals
               WHERE status='Pending'
               ORDER BY id DESC"""
        )

    def review_approval(self, approval_id: int, approved: bool, reviewed_by: str, comment: str = "") -> None:
        status = "Approved" if approved else "Rejected"
        self.execute(
            """UPDATE pending_approvals
               SET status=?, reviewed_by=?, reviewed_at=?, review_comment=?
               WHERE id=?""",
            (status, reviewed_by, datetime.now().isoformat(timespec="seconds"), comment, approval_id),
        )

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username: str, password: str) -> dict | None:
        username = str(username or "").strip()
        row = self.fetch_one(
            "SELECT * FROM users WHERE LOWER(TRIM(username))=LOWER(?) AND is_active=1",
            (username,),
        )
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
        username = str(username or "").strip()
        if not username:
            return False, "Username is required."
        if self.fetch_one("SELECT id FROM users WHERE LOWER(TRIM(username))=LOWER(?)", (username,)):
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
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.ExtendedSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(36)


RESPONSIVE_TABLE_COLUMN_KEYS: dict[str, tuple[str, ...]] = {
    "rent_requirements": (
        "id",
        "date",
        "client_name",
        "client_status",
        "contact",
        "property_requires",
        "size",
        "floor",
        "location",
        "budget",
    ),
    "rent_availability": (
        "id",
        "date",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "monthly_rent",
        "status",
    ),
    "rented_properties": (
        "id",
        "closed_at",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "monthly_rent",
        "closed_status",
    ),
    "sale_requirements": (
        "id",
        "date",
        "client_name",
        "client_status",
        "contact",
        "property_requires",
        "size",
        "floor",
        "location",
        "budget",
    ),
    "sale_availability": (
        "id",
        "date",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "demand",
        "status",
    ),
    "sold_properties": (
        "id",
        "closed_at",
        "owner_name",
        "client_broker",
        "contact",
        "property_availability",
        "size",
        "floor",
        "demand",
        "closed_status",
    ),
    "broker_contacts": ("id", "name", "contact", "area", "office_address", "remarks"),
}

LOW_PRIORITY_TABLE_COLUMN_KEYS = {
    "measurement",
    "measurement_unit",
    "deposit",
    "maintenance_charge",
    "building_name",
    "bachelor_family",
    "persons",
    "workflow_stage",
    "facilities",
    "remarks",
    "notes",
    "description",
    "created_by",
    "created_at",
    "last_edited_by",
    "last_edited_at",
    "approval_status",
    "approval_comment",
    "deleted_by",
    "deleted_at",
    "source_id",
    "archived_by",
}


def responsive_table_columns(table: str, columns: list[ColumnSpec]) -> list[ColumnSpec]:
    by_key = {column.key: column for column in columns}
    preferred = RESPONSIVE_TABLE_COLUMN_KEYS.get(table)
    if preferred:
        visible = [by_key[key] for key in preferred if key in by_key]
        if visible:
            return visible
    compact = [column for column in columns if column.key not in LOW_PRIORITY_TABLE_COLUMN_KEYS]
    return (compact or columns)[:10]


def apply_responsive_table_layout(table: QTableWidget) -> None:
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(68)
    header.setSectionResizeMode(QHeaderView.Stretch)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setWordWrap(True)
    table.verticalHeader().setDefaultSectionSize(40)


STATUS_COLUMN_KEYS = {"client_status", "client_broker", "status", "workflow_stage", "approval_status", "verification_status"}
PROPERTY_COLUMN_KEYS = {"property_requires", "property_availability", "property_type", "property_requirement"}


def style_workflow_table_item(item: QTableWidgetItem, key: str, text: str) -> None:
    item.setForeground(QColor("#0f172a"))
    normalized = (text or "").strip().lower()
    if key in PROPERTY_COLUMN_KEYS:
        item.setTextAlignment(Qt.AlignCenter)
        if "plot" in normalized:
            item.setBackground(QColor("#fef3c7"))
            item.setForeground(QColor("#92400e"))
        elif "shop" in normalized or "commercial" in normalized:
            item.setBackground(QColor("#e0f2fe"))
            item.setForeground(QColor("#075985"))
        else:
            item.setBackground(QColor("#dcfce7"))
            item.setForeground(QColor("#166534"))
    elif key in STATUS_COLUMN_KEYS:
        item.setTextAlignment(Qt.AlignCenter)
        if any(word in normalized for word in ("pending", "broker")):
            item.setBackground(QColor("#fef3c7"))
            item.setForeground(QColor("#92400e"))
        elif any(word in normalized for word in ("rented", "sold", "available", "approved", "owner")):
            item.setBackground(QColor("#dcfce7"))
            item.setForeground(QColor("#166534"))
        elif any(word in normalized for word in ("reject", "withdraw", "deleted")):
            item.setBackground(QColor("#fee2e2"))
            item.setForeground(QColor("#b91c1c"))
        else:
            item.setBackground(QColor("#dbeafe"))
            item.setForeground(QColor("#1d4ed8"))


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
        self.username.setText("admin")
        self.username.selectAll()
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        hint = QLabel("Default first-run account is admin / admin.")
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
            if spec.kind in {"text", "facilities", "multiselect"}:
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
            elif hasattr(widget, "multi_boxes"):
                self._set_multiselect_widget_values(widget, value)
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
        if spec.kind == "multiselect":
            return self._make_multiselect_widget(spec, value)
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

    def _make_multiselect_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("MultiSelectBox")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = list(spec.options or [])
        selected = parse_multi_options(value, options)
        for label in selected:
            if normalize_text(label) not in {normalize_text(option) for option in options}:
                options.append(label)
        boxes: list[QCheckBox] = []
        columns = 4
        selected_keys = {normalize_text(label) for label in selected}
        for index, label in enumerate(options):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("MultiSelectCheck")
            checkbox.setChecked(normalize_text(label) in selected_keys)
            checkbox.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            grid.addWidget(checkbox, index // columns, index % columns)
            boxes.append(checkbox)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        frame.multi_boxes = boxes
        return frame

    def _set_multiselect_widget_values(self, widget: QWidget, value: Any) -> None:
        selected = {normalize_text(label) for label in parse_multi_options(value)}
        for box in getattr(widget, "multi_boxes", []):
            box.setChecked(normalize_text(box.text()) in selected)

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
        if spec.kind == "multiselect":
            boxes = getattr(widget, "multi_boxes", [])
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


class CommentDialog(QDialog):
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


class DashboardBarChart(QWidget):
    def __init__(self, rows: list[dict[str, Any]]):
        super().__init__()
        self.rows = rows[:6] or [{"location": "No Data", "rent_requirements": 0, "rent_availability": 0}]
        self.setMinimumHeight(190)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(18, 8, -18, -28)
        left = rect.left()
        right = rect.right()
        top = rect.top() + 4
        bottom = rect.bottom() - 22
        grid_pen = QPen(QColor("#b9cce2"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for index in range(4):
            y = top + ((bottom - top) / 3) * index
            painter.drawLine(QPointF(left, y), QPointF(right, y))
        max_value = max(
            1,
            *[
                max(safe_float(row.get("rent_requirements")), safe_float(row.get("rent_availability")))
                for row in self.rows
            ],
        )
        group_width = max(70, int((right - left) / max(len(self.rows), 1)))
        bar_width = 18
        for index, row in enumerate(self.rows):
            center = left + group_width * index + group_width / 2
            req_height = ((bottom - top) * safe_float(row.get("rent_requirements"))) / max_value
            av_height = ((bottom - top) * safe_float(row.get("rent_availability"))) / max_value
            req_rect = QRectF(center - bar_width - 3, bottom - req_height, bar_width, req_height)
            av_rect = QRectF(center + 3, bottom - av_height, bar_width, av_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#1976d2")))
            painter.drawRoundedRect(req_rect, 3, 3)
            painter.setBrush(QBrush(QColor("#21964b")))
            painter.drawRoundedRect(av_rect, 3, 3)
            painter.setPen(QPen(QColor("#163f79")))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            label_rect = QRectF(center - group_width / 2 + 3, bottom + 8, group_width - 6, 20)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, str(row.get("location") or "Area"))


class DashboardDonut(QWidget):
    def __init__(self, total: int, segments: list[dict[str, Any]]):
        super().__init__()
        self.total = total
        self.segments = segments[:3]
        self.setMinimumSize(210, 210)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 24
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        if not self.segments or sum(safe_float(row.get("percent")) for row in self.segments) <= 0:
            painter.setBrush(QBrush(QColor("#cbd5e1")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        else:
            start = 90 * 16
            for row in self.segments:
                span = int(-safe_float(row.get("percent")) * 3.6 * 16)
                painter.setBrush(QBrush(QColor(str(row.get("color") or "#1976d2"))))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPie(rect, start, span)
                start += span
        inner = rect.adjusted(side * 0.24, side * 0.24, -side * 0.24, -side * 0.24)
        painter.setBrush(QBrush(QColor("#eef7ff")))
        painter.setPen(QPen(QColor("#d6e6f7"), 1))
        painter.drawEllipse(inner)
        painter.setPen(QPen(QColor("#17345c")))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Black))
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, f"{self.total:,}")


class DashboardLineChart(QWidget):
    SERIES = (
        ("response_time", QColor("#1976d2")),
        ("approvals_cleared", QColor("#ef7d00")),
        ("conversion", QColor("#3b9629")),
    )

    def __init__(self, rows: list[dict[str, Any]]):
        super().__init__()
        self.rows = rows[:3] or [
            {"period": "30 Days", "response_time": 35, "approvals_cleared": 20, "conversion": 12},
            {"period": "90 Days", "response_time": 65, "approvals_cleared": 60, "conversion": 35},
            {"period": "180 Days", "response_time": 72, "approvals_cleared": 82, "conversion": 50},
        ]
        self.setMinimumHeight(210)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(22, 10, -22, -38)
        top = rect.top() + 8
        bottom = rect.bottom() - 4
        left = rect.left()
        right = rect.right()
        painter.setPen(QPen(QColor("#b9cce2"), 1))
        for index in range(4):
            y = top + ((bottom - top) / 3) * index
            painter.drawLine(QPointF(left, y), QPointF(right, y))
        x_positions = [
            left + ((right - left) / max(len(self.rows) - 1, 1)) * index
            for index in range(len(self.rows))
        ]
        for key, color in self.SERIES:
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            points = []
            for index, row in enumerate(self.rows):
                value = max(0, min(100, safe_float(row.get(key))))
                y = bottom - ((bottom - top) * value / 100)
                points.append(QPointF(x_positions[index], y))
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)
            painter.setBrush(QBrush(color))
            for point in points:
                painter.drawEllipse(point, 6, 6)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#173f75")))
        for index, row in enumerate(self.rows):
            label = str(row.get("period") or "")
            painter.drawText(QRectF(x_positions[index] - 45, bottom + 12, 90, 24), Qt.AlignmentFlag.AlignCenter, label)


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
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
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
            self.main.after_record_saved(self.spec.table, new_id)
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
        if self.spec.table in PHASE1_TABLES and not is_admin_role(self.main.role):
            approval_id = self.services.submit_approval(
                "edit",
                self.spec.table,
                int(row["id"]),
                {col: vals.get(col) for col in cols},
                str(self.main.current_user.get("username") or ""),
            )
            QMessageBox.information(self, "Pending Approval", f"Edit request #{approval_id} was sent for admin approval.")
            self.main.update_status_bar(f"{self.spec.title} edit sent for approval")
            return
        assignments = ", ".join(f"{col}=?" for col in cols)
        if self.spec.table in PHASE1_TABLES:
            extra_cols = []
            if "last_edited_by" in self.services.table_columns(self.spec.table):
                extra_cols.append("last_edited_by")
                vals["last_edited_by"] = self.main.current_user.get("username", "")
            if "last_edited_at" in self.services.table_columns(self.spec.table):
                extra_cols.append("last_edited_at")
                vals["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            cols = cols + extra_cols
            assignments = ", ".join(f"{col}=?" for col in cols)
        params = tuple(vals.get(col) for col in cols) + (row["id"],)
        self.services.execute(f"UPDATE {self.spec.table} SET {assignments} WHERE id=?", params)
        self.refresh()
        self.main.after_record_saved(self.spec.table, row["id"])
        self.main.refresh_dashboard()
        self.main.update_status_bar(f"{self.spec.title} record updated")

    def delete_record(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        if not has_permission(self.main.role, "delete") and self.spec.table not in PHASE1_TABLES:
            QMessageBox.warning(self, "Access Denied", "You do not have permission to delete records.")
            return
        ids = [row["id"] for row in rows]
        ask = QMessageBox.question(self, "Recycle", f"Move {len(ids)} selected record(s) from {self.spec.title} to recycle?")
        if ask != QMessageBox.Yes:
            return
        if self.spec.table in PHASE1_TABLES and not is_admin_role(self.main.role):
            for row_id in ids:
                self.services.submit_approval(
                    "delete",
                    self.spec.table,
                    int(row_id),
                    {},
                    str(self.main.current_user.get("username") or ""),
                )
            QMessageBox.information(self, "Pending Approval", f"{len(ids)} delete request(s) were sent for admin approval.")
            self.main.update_status_bar(f"{len(ids)} delete request(s) sent for approval")
            return
        for row_id in ids:
            ok, message = self.main.can_delete_record(self.spec.table, int(row_id))
            if not ok:
                QMessageBox.warning(self, "Related Records", message)
                return
        if "is_deleted" in self.services.table_columns(self.spec.table):
            for row_id in ids:
                self.services.execute(
                    f"UPDATE {self.spec.table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                    (self.main.current_user.get("username", ""), datetime.now().isoformat(timespec="seconds"), row_id),
                )
                self.main.log_audit("delete", self.spec.table, int(row_id))
            self.refresh()
            self.main.refresh_dashboard()
            self.main.update_status_bar(f"{len(ids)} {self.spec.title.lower()} record(s) recycled")
            return
        for row_id in ids:
            self.services.execute(f"DELETE FROM {self.spec.table} WHERE id=?", (row_id,))
            self.main.log_audit("delete", self.spec.table, int(row_id))
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


@dataclass
class PhaseOneSectionSpec:
    key: str
    title: str
    table: str
    name_key: str
    amount_key: str | None
    fields: list[FieldSpec]
    columns: list[ColumnSpec]
    match_target: str | None = None


def phase1_section_specs(main: "ModernCRMWindow") -> dict[str, PhaseOneSectionSpec]:
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    areas = setting_lines(main.services, "phase1_areas", COMMON_AREAS)
    facilities = setting_lines(main.services, "phase1_facilities", FACILITY_OPTIONS)
    floors = setting_lines(main.services, "phase1_floors", FLOOR_OPTIONS)
    property_types = setting_lines(main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS)
    measurement_units = setting_lines(main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS)
    meta = [
        ColumnSpec("created_by", "Created By", width=120),
        ColumnSpec("created_at", "Created At", d, 120),
        ColumnSpec("last_edited_by", "Last Edited By", width=130),
        ColumnSpec("last_edited_at", "Last Edited At", d, 130),
    ]
    common_req_tail = [
        FieldSpec("Rooms *", "size", required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
        FieldSpec("Persons", "persons"),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
    ]
    availability_tail = [
        FieldSpec("Rooms *", "size", required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Building Name", "building_name"),
        FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
        FieldSpec("Persons", "persons"),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
    ]
    return {
        "rent_req": PhaseOneSectionSpec(
            "rent_req",
            "Rent Requirement",
            "rent_requirements",
            "client_name",
            "budget",
            [
                FieldSpec("Name *", "client_name", required=True),
                FieldSpec("Status", "client_status", "combo", "Client", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Required / Needed *", "property_requires", "combo", options=property_types, required=True),
                *common_req_tail,
                FieldSpec("Budget", "budget", numeric=True),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("client_name", "Name", width=160), ColumnSpec("client_status", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("property_requires", "Property Required/Needed", width=180),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("location", "Location", width=160), ColumnSpec("budget", "Budget", m, 120),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170),
                ColumnSpec("persons", "Persons", width=90), ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
            "rent_av",
        ),
        "rent_av": PhaseOneSectionSpec(
            "rent_av",
            "Rent Availability",
            "rent_availability",
            "owner_name",
            "monthly_rent",
            [
                FieldSpec("Name *", "owner_name", required=True),
                FieldSpec("Status", "client_broker", "combo", "Owner", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Available *", "property_availability", "combo", options=property_types, required=True),
                *availability_tail,
                FieldSpec("Rent *", "monthly_rent", numeric=True, required=True),
                FieldSpec("Advance", "deposit", numeric=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("owner_name", "Name", width=160), ColumnSpec("client_broker", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("status", "Availability", width=120),
                ColumnSpec("property_availability", "Property Available", width=170),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("monthly_rent", "Rent", m, 120), ColumnSpec("deposit", "Advance", m, 120),
                ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("location", "Location", width=150),
                ColumnSpec("building_name", "Building Name", width=160),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170),
                ColumnSpec("persons", "Persons", width=90), ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
        ),
        "sale_req": PhaseOneSectionSpec(
            "sale_req",
            "Sale Requirement",
            "sale_requirements",
            "client_name",
            "budget",
            [
                FieldSpec("Name *", "client_name", required=True),
                FieldSpec("Status", "client_status", "combo", "Client", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Required / Needed *", "property_requires", "combo", options=property_types, required=True),
                FieldSpec("Rooms *", "size", required=True),
                FieldSpec("Measurement", "measurement", numeric=True),
                FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
                FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
                FieldSpec("Budget *", "budget", numeric=True, required=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
                FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
                FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
                FieldSpec("Facilities", "facilities", "facilities", options=facilities),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("client_name", "Name", width=160), ColumnSpec("client_status", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("property_requires", "Property Required/Needed", width=180),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("budget", "Budget", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                ColumnSpec("location", "Location", width=160),
                ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170), ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
            "sale_av",
        ),
        "sale_av": PhaseOneSectionSpec(
            "sale_av",
            "Sale Availability",
            "sale_availability",
            "owner_name",
            "demand",
            [
                FieldSpec("Name *", "owner_name", required=True),
                FieldSpec("Status", "client_broker", "combo", "Owner", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Available *", "property_availability", "combo", options=property_types, required=True),
                FieldSpec("Rooms *", "size", required=True),
                FieldSpec("Measurement", "measurement", numeric=True),
                FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
                FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
                FieldSpec("Demand *", "demand", numeric=True, required=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
                FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
                FieldSpec("Building Name", "building_name"),
                FieldSpec("Facilities", "facilities", "facilities", options=facilities),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("owner_name", "Name", width=160), ColumnSpec("client_broker", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("status", "Availability", width=120),
                ColumnSpec("property_availability", "Property Available", width=170),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("demand", "Demand", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                ColumnSpec("location", "Location", width=160), ColumnSpec("building_name", "Building Name", width=170),
                ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240), *meta,
            ],
        ),
    }


def phase_one_form_group_title(key: str) -> str:
    if key in {"client_name", "owner_name", "client_status", "client_broker", "contact", "contact_phone", "owner_phone", "date"}:
        return "Contact"
    if key in {"budget", "monthly_rent", "deposit", "demand", "maintenance_charge", "maintenance"}:
        return "Price"
    if key in {"measurement", "measurement_unit"}:
        return "Property"
    if key in {"facilities", "remarks", "notes"}:
        return "Facilities"
    return "Property"


class PhaseOneForm(QWidget):
    saved = Signal(dict)
    cancelled = Signal()

    def __init__(self, spec: PhaseOneSectionSpec, *, mode: str = "add", data: dict | None = None):
        super().__init__()
        self.spec = spec
        self.mode = mode
        self.data = data or {}
        self.widgets: dict[str, QWidget] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel(f"{'Add New' if self.mode == 'add' else 'Edit'} {self.spec.title}")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        back = QPushButton("Exit")
        back.clicked.connect(self.cancelled.emit)
        header.addWidget(back)
        layout.addLayout(header)

        hint = QLabel("Save keeps this form open for fast next entry. Required fields are marked with *.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 14, 0, 14)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        row = 0
        col_group = 0
        current_group = ""
        for field_spec in self.spec.fields:
            group_title = phase_one_form_group_title(field_spec.key)
            if group_title != current_group:
                if col_group:
                    row += 1
                    col_group = 0
                group = QLabel(group_title)
                group.setObjectName("FormGroupTitle")
                grid.addWidget(group, row, 0, 1, 4)
                row += 1
                current_group = group_title
            value = self.data.get(field_spec.key, field_spec.default() if callable(field_spec.default) else field_spec.default)
            widget = self._make_widget(field_spec, value)
            self.widgets[field_spec.key] = widget
            label = QLabel(field_spec.label)
            label.setObjectName("RequiredLabel" if field_spec.required else "FormLabel")
            if field_spec.kind in {"facilities", "multiselect"}:
                if col_group:
                    row += 1
                    col_group = 0
                grid.addWidget(label, row, 0)
                grid.addWidget(widget, row, 1, 1, 3)
                row += 1
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

        footer = QHBoxLayout()
        footer.addStretch(1)
        save = QPushButton("Save")
        save.setObjectName("AccentButton")
        save.clicked.connect(self._save)
        footer.addWidget(save)
        layout.addLayout(footer)

    def _make_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        if spec.kind == "facilities":
            frame = QFrame()
            frame.setObjectName("FacilitiesBox")
            grid = QGridLayout(frame)
            grid.setContentsMargins(8, 8, 8, 8)
            options = spec.options or FACILITY_OPTIONS
            selected = parse_facilities(value, options)
            boxes: list[QRadioButton] = []
            for index, label in enumerate(options):
                checkbox = QRadioButton(label)
                checkbox.setObjectName("FacilityCheck")
                checkbox.setAutoExclusive(False)
                checkbox.setChecked(label in selected)
                grid.addWidget(checkbox, index // 3, index % 3)
                boxes.append(checkbox)
            frame.facility_boxes = boxes
            return frame
        if spec.kind == "multiselect":
            return self._make_multiselect_widget(spec, value)
        if spec.kind in {"combo", "combo_other", "autocomplete"}:
            widget = QComboBox()
            widget.addItems(spec.options)
            widget.setEditable(spec.kind != "combo")
            if value not in (None, ""):
                idx = widget.findText(str(value))
                if idx < 0 and spec.kind != "combo":
                    widget.addItem(str(value))
                    idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setEditText(str(value))
            return widget
        if spec.kind == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
            widget.setDate(parse_qdate(value) if value else QDate.currentDate())
            return widget
        if spec.kind == "text":
            widget = QTextEdit()
            widget.setPlainText("" if value is None else str(value))
            return widget
        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        if spec.numeric:
            widget.setPlaceholderText("0")
        return widget

    def _make_multiselect_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("MultiSelectBox")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = list(spec.options or [])
        selected = parse_multi_options(value, options)
        option_keys = {normalize_text(option) for option in options}
        for label in selected:
            key = normalize_text(label)
            if key and key not in option_keys:
                options.append(label)
                option_keys.add(key)
        boxes: list[QCheckBox] = []
        selected_keys = {normalize_text(label) for label in selected}
        columns = 4
        for index, label in enumerate(options):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("MultiSelectCheck")
            checkbox.setChecked(normalize_text(label) in selected_keys)
            grid.addWidget(checkbox, index // columns, index % columns)
            boxes.append(checkbox)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        frame.multi_boxes = boxes
        return frame

    def raw_value(self, field_spec: FieldSpec) -> str:
        widget = self.widgets[field_spec.key]
        if field_spec.kind == "facilities":
            boxes = getattr(widget, "facility_boxes", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if field_spec.kind == "multiselect":
            boxes = getattr(widget, "multi_boxes", [])
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

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_spec in self.spec.fields:
            value: Any = self.raw_value(field_spec)
            if field_spec.numeric:
                value = safe_float(value)
            values[field_spec.key] = value
        return values

    def validate(self) -> tuple[bool, str]:
        try:
            for field_spec in self.spec.fields:
                validate_form_value(
                    field_spec.key,
                    field_spec.label,
                    self.raw_value(field_spec),
                    required=field_spec.required,
                    numeric=field_spec.numeric,
                    options=field_spec.options,
                    strict_options=(field_spec.kind == "combo"),
                )
        except ValueError as exc:
            return False, str(exc)
        return True, ""

    def clear_for_next(self) -> None:
        self.data = {}
        for field_spec in self.spec.fields:
            widget = self.widgets[field_spec.key]
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0 if widget.count() else -1)
            elif field_spec.kind == "facilities":
                for box in getattr(widget, "facility_boxes", []):
                    box.setChecked(False)
            elif field_spec.kind == "multiselect":
                for box in getattr(widget, "multi_boxes", []):
                    box.setChecked(False)

    def _save(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Check Fields", message)
            return
        self.saved.emit(self.values())


class MatchResultsDialog(QDialog):
    def __init__(self, main: "ModernCRMWindow", requirement: dict, matches: list[dict], title: str):
        super().__init__(main)
        self.main = main
        self.requirement = requirement
        self.matches = matches
        self.setWindowTitle(title)
        self.resize(1040, 620)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["Score", "Reasons", "Serial", "Name", "Contact", "Rooms", "Floor", "Amount", "Location"])
        self.table.setRowCount(len(matches))
        for row_idx, item in enumerate(matches):
            row = item["row"]
            values = [
                f"{item['score']:.0f}%",
                "; ".join(item["reasons"]),
                str(row.get("id") or ""),
                str(row.get("owner_name") or row.get("client_name") or ""),
                str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or ""),
                str(row.get("size") or ""),
                str(row.get("floor") or ""),
                money(row.get("monthly_rent") or row.get("demand") or 0, main.currency_symbol),
                str(row.get("location") or ""),
            ]
            for col_idx, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, table_item)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        print_btn = QPushButton("Print")
        print_btn.setObjectName("AccentButton")
        print_btn.clicked.connect(self.print_results)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(print_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _html(self) -> str:
        company = html.escape(self.main.company_name)
        user = html.escape(str(self.main.current_user.get("full_name") or self.main.current_user.get("username") or ""))
        logo_path = self.main.services.settings_get("company_logo", str(crm_logo_path()))
        logo_html = f"<img src='{html.escape(logo_path)}' style='height:54px'>" if logo_path and Path(logo_path).exists() else ""
        req_lines = "".join(
            f"<tr><td><b>{html.escape(str(key).replace('_', ' ').title())}</b></td><td>{html.escape(str(value or ''))}</td></tr>"
            for key, value in self.requirement.items()
            if key in {"id", "date", "client_name", "contact", "size", "floor", "location", "budget", "facilities"}
        )
        rows = "".join(
            "<tr>"
            f"<td>{item['score']:.0f}%</td>"
            f"<td>{html.escape('; '.join(item['reasons']))}</td>"
            f"<td>{html.escape(str(item['row'].get('id') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('owner_name') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('owner_phone') or item['row'].get('contact_phone') or item['row'].get('contact') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('size') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('floor') or ''))}</td>"
            f"<td>{html.escape(money(item['row'].get('monthly_rent') or item['row'].get('demand') or 0, self.main.currency_symbol))}</td>"
            f"<td>{html.escape(str(item['row'].get('location') or ''))}</td>"
            "</tr>"
            for item in self.matches
        )
        return f"""
        <html><body>
        <table width='100%'><tr><td>{logo_html}</td><td><h2>QT_CRM - {company}</h2>
        <p>Match Sheet | {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Staff: {user}</p></td></tr></table>
        <h3>Client Requirement</h3><table border='1' cellspacing='0' cellpadding='5'>{req_lines}</table>
        <h3>Matched Properties</h3>
        <table border='1' cellspacing='0' cellpadding='5' width='100%'>
        <tr><th>Score</th><th>Reasons</th><th>Serial</th><th>Name</th><th>Contact</th><th>Rooms</th><th>Floor</th><th>Amount</th><th>Location</th></tr>
        {rows}
        </table>
        </body></html>
        """

    def print_results(self) -> None:
        printer = QPrinter(QPrinter.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        doc = QTextDocument()
        doc.setHtml(self._html())
        doc.print_(printer)


class ImportPreviewDialog(QDialog):
    def __init__(self, spec: PhaseOneSectionSpec, rows: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.spec = spec
        self.rows = rows
        self.setWindowTitle(f"Import Preview - {spec.title}")
        self.resize(980, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Preview {len(rows)} row(s). Confirm to import."))
        self.table = QTableWidget()
        self.table.setColumnCount(len(spec.fields))
        self.table.setHorizontalHeaderLabels([f.label.replace(" *", "") for f in spec.fields])
        self.table.setRowCount(min(len(rows), 200))
        for row_idx, row in enumerate(rows[:200]):
            for col_idx, field_spec in enumerate(spec.fields):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(field_spec.key, "") or "")))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class PhaseOneSectionPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk", spec: PhaseOneSectionSpec):
        super().__init__()
        self.main = main
        self.desk = desk
        self.services = main.services
        self.spec = spec
        self.rows: list[dict] = []
        self.showing_recycle = False
        self.stack = QStackedWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack, 1)
        self.table_page = QWidget()
        self.stack.addWidget(self.table_page)
        self.form_page: PhaseOneForm | None = None
        self._build_table_page()
        self.refresh()

    def _build_table_page(self) -> None:
        layout = QVBoxLayout(self.table_page)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel(self.spec.title)
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        back = QPushButton("Home")
        back.clicked.connect(self.desk.show_home)
        header.addWidget(back)
        if self.can_change():
            add = QPushButton("Add New")
            add.setObjectName("AccentButton")
            add.clicked.connect(self.show_add_form)
            header.addWidget(add)
            edit = QPushButton("Edit")
            edit.clicked.connect(self.show_edit_form)
            header.addWidget(edit)
            delete = QPushButton("Delete")
            delete.setObjectName("DangerButton")
            delete.clicked.connect(self.delete_selected)
            header.addWidget(delete)
            pending = QPushButton("Mark Pending")
            pending.setObjectName("WarningButton")
            pending.clicked.connect(lambda: self.mark_selected_workflow("Pending"))
            header.addWidget(pending)
            if self.spec.table == "rent_availability":
                rented = QPushButton("Mark Rented")
                rented.setObjectName("AccentButton")
                rented.clicked.connect(lambda: self.mark_selected_workflow("Rented"))
                header.addWidget(rented)
            elif self.spec.table == "sale_availability":
                sold = QPushButton("Mark Sold")
                sold.setObjectName("AccentButton")
                sold.clicked.connect(lambda: self.mark_selected_workflow("Sold"))
                header.addWidget(sold)
        if self.spec.match_target:
            match = QPushButton("Match Selected")
            match.clicked.connect(self.match_selected)
            header.addWidget(match)
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_rows)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_rows)
        template_btn = QPushButton("Template")
        template_btn.clicked.connect(self.save_template)
        header.addWidget(import_btn)
        header.addWidget(export_btn)
        header.addWidget(template_btn)
        if is_admin_role(self.main.role):
            recycle = QPushButton("Recycle Bin")
            recycle.clicked.connect(self.toggle_recycle)
            header.addWidget(recycle)
        layout.addLayout(header)

        selection = QHBoxLayout()
        self.status = QLabel("0 of 0 selected")
        self.status.setObjectName("SelectionCount")
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
        selection.addWidget(self.status)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        selection.addWidget(details)
        selection.addWidget(copy)
        selection.addWidget(refresh)
        layout.addLayout(selection)

        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_status)
        self.table.doubleClicked.connect(self.show_edit_form)
        layout.addWidget(self.table, 1)

    def can_change(self) -> bool:
        return self.main.role != "Viewer"

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in selected_table_row_indexes(self.table, len(self.rows))]

    def selected_row(self) -> dict | None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select a row first.")
            return None
        if len(rows) > 1:
            QMessageBox.information(self, "Select One", "Select only one row.")
            return None
        return rows[0]

    def update_status(self) -> None:
        self.status.setText(f"{len(self.selected_rows())} of {len(self.rows)} selected")

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_status()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_status()

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
                display = "-" if value in (None, "") else format_date_display(value) if is_date_key(key) else value
                details.append(f"{key}: {display}")
            details.append("")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.spec.title} Details")
        dialog.resize(720, 520)
        body = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 10))
        text.setPlainText("\n".join(details))
        body.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        body.addWidget(buttons)
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

    def mark_selected_workflow(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select at least one row first.")
            return
        if status in {"Rented", "Sold"} and self.spec.table not in {"rent_availability", "sale_availability"}:
            return
        ask = QMessageBox.question(
            self,
            status,
            f"Mark {len(rows)} {self.spec.title.lower()} record(s) as {status}?",
        )
        if ask != QMessageBox.Yes:
            return
        updated = 0
        for row in rows:
            self.main.update_deal_workflow_status(self.spec.table, int(row["id"]), status)
            updated += 1
        self.refresh()
        self.main.refresh_dashboard()
        message = f"{updated} record(s) marked {status}"
        self.status.setText(message)
        self.main.update_status_bar(message)

    def refresh(self) -> None:
        cols = [col.key for col in self.spec.columns]
        deleted = 1 if self.showing_recycle else 0
        where = ["COALESCE(is_deleted,0)=?"]
        params: list[Any] = [deleted]
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(self.spec.table)
        if closed_rule and not self.showing_recycle and "status" in cols:
            where.append("LOWER(COALESCE(status,''))<>LOWER(?)")
            params.append(closed_rule[0])
        self.rows = self.services.fetch_all(
            f"SELECT {', '.join(cols)} FROM {self.spec.table} WHERE {' AND '.join(where)} ORDER BY id DESC",
            tuple(params),
        )
        display_columns = responsive_table_columns(self.spec.table, self.spec.columns)
        self.table.setColumnCount(len(display_columns))
        self.table.setHorizontalHeaderLabels([col.label for col in display_columns])
        self.table.setRowCount(len(self.rows))
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(display_columns):
                value = row.get(col.key)
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text.replace("\n", " "))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                style_workflow_table_item(item, col.key, text)
                if len(text) > 28:
                    item.setToolTip(text)
                self.table.setItem(row_idx, col_idx, item)
        apply_responsive_table_layout(self.table)
        self.update_status()

    def show_add_form(self) -> None:
        self._show_form("add", {})

    def show_edit_form(self) -> None:
        if not self.can_change():
            return
        row = self.selected_row()
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
        self._show_form("edit", full)

    def _show_form(self, mode: str, data: dict) -> None:
        if self.form_page:
            self.stack.removeWidget(self.form_page)
            self.form_page.deleteLater()
        self.form_page = PhaseOneForm(self.spec, mode=mode, data=data)
        self.form_page.saved.connect(lambda values, mode=mode, data=data: self.save_form(mode, data, values))
        self.form_page.cancelled.connect(self.show_table)
        self.stack.addWidget(self.form_page)
        self.stack.setCurrentWidget(self.form_page)

    def show_table(self) -> None:
        self.refresh()
        self.stack.setCurrentWidget(self.table_page)

    def _insert_columns(self) -> list[str]:
        cols = [field.key for field in self.spec.fields]
        for extra in ("contact_person", "contact_phone", "owner_phone"):
            if extra in self.services.table_columns(self.spec.table) and extra not in cols:
                cols.append(extra)
        for extra in ("created_by", "created_at"):
            if extra in self.services.table_columns(self.spec.table):
                cols.append(extra)
        return cols

    def _normalize_values(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(values)
        columns = self.services.table_columns(self.spec.table)
        if "date" in normalized and normalized.get("date") not in (None, ""):
            normalized["date"] = DateUtils.store_date(normalized.get("date"))
        if self.spec.table in {"rent_requirements", "sale_requirements"}:
            if "client_status" in normalized:
                normalized["client_status"] = normalize_contact_role(normalized.get("client_status"), "Client")
            phone = PhoneValidator.validate_phone(normalized.get("contact") or normalized.get("contact_phone"), required=True)
            if "contact" in columns:
                normalized["contact"] = phone
            if "contact_phone" in columns:
                normalized["contact_phone"] = phone
            if "contact_person" in columns:
                normalized["contact_person"] = normalized.get(self.spec.name_key) or ""
        elif self.spec.table in {"rent_availability", "sale_availability"}:
            if "client_broker" in normalized:
                normalized["client_broker"] = normalize_contact_role(normalized.get("client_broker"), "Owner")
            if "status" in normalized:
                normalized["status"] = normalize_availability_status(normalized.get("status"), "Available")
            phone = PhoneValidator.validate_phone(
                normalized.get("contact") or normalized.get("owner_phone") or normalized.get("contact_phone"),
                required=True,
            )
            if "contact" in columns:
                normalized["contact"] = phone
            if "owner_phone" in columns:
                normalized["owner_phone"] = phone
            if "contact_phone" in columns:
                normalized["contact_phone"] = phone
        return normalized

    def save_form(self, mode: str, data: dict, values: dict) -> None:
        try:
            values = self._normalize_values(values)
        except ValueError as exc:
            QMessageBox.warning(self, "Check Fields", str(exc))
            return
        if mode == "add" and self._duplicate_exists(values):
            ask = QMessageBox.question(self, "Duplicate Warning", "A record with the same Name + Contact exists. Are you sure?")
            if ask != QMessageBox.Yes:
                return
        if mode == "add":
            values["created_by"] = self.main.current_user.get("username", "")
            values["created_at"] = datetime.now().isoformat(timespec="seconds")
            cols = self._insert_columns()
            placeholders = ", ".join("?" for _ in cols)
            new_id = self.services.insert(
                f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(values.get(col) for col in cols),
            )
            self.main.after_record_saved(self.spec.table, new_id)
            self.refresh()
            if self.form_page:
                self.form_page.clear_for_next()
            self.main.update_status_bar(f"{self.spec.title} saved")
            return
        record_id = int(data["id"])
        update_values = {key: values.get(key) for key in values}
        if is_admin_role(self.main.role):
            update_values["last_edited_by"] = self.main.current_user.get("username", "")
            update_values["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            cols = [key for key in update_values if key in self.services.table_columns(self.spec.table)]
            assignments = ", ".join(f"{col}=?" for col in cols)
            self.services.execute(
                f"UPDATE {self.spec.table} SET {assignments} WHERE id=?",
                tuple(update_values.get(col) for col in cols) + (record_id,),
            )
            self.show_table()
            self.main.update_status_bar(f"{self.spec.title} updated")
        else:
            approval_id = self.services.submit_approval(
                "edit",
                self.spec.table,
                record_id,
                update_values,
                str(self.main.current_user.get("username") or ""),
            )
            QMessageBox.information(self, "Pending Approval", f"Edit request #{approval_id} was sent for admin approval.")
            self.show_table()

    def _duplicate_exists(self, values: dict) -> bool:
        name = str(values.get(self.spec.name_key) or "").strip()
        contact = PhoneValidator.normalize(values.get("contact") or values.get("contact_phone") or values.get("owner_phone"))
        if not name and not contact:
            return False
        contact_columns = [
            column
            for column in ("contact", "contact_phone", "owner_phone")
            if column in self.services.table_columns(self.spec.table)
        ]
        if not contact_columns:
            return False
        contact_filter = " OR ".join(f"COALESCE({column},'')=?" for column in contact_columns)
        row = self.services.fetch_one(
            f"""SELECT id FROM {self.spec.table}
                WHERE COALESCE(is_deleted,0)=0
                  AND LOWER(COALESCE({self.spec.name_key},''))=LOWER(?)
                  AND ({contact_filter})
                LIMIT 1""",
            (name, *([contact] * len(contact_columns))),
        )
        return bool(row)

    def delete_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        if QMessageBox.question(self, "Recycle", f"Move {len(rows)} record(s) to recycle?") != QMessageBox.Yes:
            return
        username = str(self.main.current_user.get("username") or "")
        if is_admin_role(self.main.role):
            for row in rows:
                self.services.execute(
                    f"UPDATE {self.spec.table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                    (username, datetime.now().isoformat(timespec="seconds"), row["id"]),
                )
                self.main.log_audit("delete", self.spec.table, int(row["id"]))
            self.refresh()
            return
        for row in rows:
            self.services.submit_approval("delete", self.spec.table, int(row["id"]), {}, username)
        QMessageBox.information(self, "Pending Approval", "Delete request sent for admin approval.")

    def toggle_recycle(self) -> None:
        self.showing_recycle = not self.showing_recycle
        self.refresh()
        if self.showing_recycle and is_admin_role(self.main.role):
            ask = QMessageBox.question(self, "Recycle Bin", "Recycle Bin is open. Restore selected records now?")
            if ask == QMessageBox.Yes:
                self.restore_selected()

    def restore_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            return
        for row in rows:
            self.services.execute(
                f"UPDATE {self.spec.table} SET is_deleted=0, deleted_by=NULL, deleted_at=NULL WHERE id=?",
                (row["id"],),
            )
        self.refresh()

    def match_selected(self) -> None:
        row = self.selected_row()
        if not row or not self.spec.match_target:
            return
        target = self.desk.section_specs[self.spec.match_target]
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
        matches = self.desk.find_matches(full, target)
        MatchResultsDialog(self.main, full, matches, f"{self.spec.title} Matches").exec()

    def export_rows(self) -> None:
        rows = self.selected_rows() or self.rows
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export",
            str(OUTPUT_DIR / f"{self.spec.table}_{datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if not path:
            return
        headers = [col.label for col in self.spec.columns]
        data = [{col.label: row.get(col.key, "") for col in self.spec.columns} for row in rows]
        if path.lower().endswith(".xlsx"):
            try:
                import pandas as pd
                pd.DataFrame(data, columns=headers).to_excel(path, index=False)
            except Exception as exc:
                QMessageBox.warning(self, "Excel Export", f"Excel export needs pandas/openpyxl.\n{exc}")
                return
        else:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
        QMessageBox.information(self, "Exported", f"Saved {len(rows)} row(s).")

    def save_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template",
            str(OUTPUT_DIR / f"{self.spec.table}_template.csv"),
            "CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if not path:
            return
        headers = [field.label.replace(" *", "") for field in self.spec.fields]
        if path.lower().endswith(".xlsx"):
            try:
                import pandas as pd
                pd.DataFrame(columns=headers).to_excel(path, index=False)
            except Exception as exc:
                QMessageBox.warning(self, "Excel Template", f"Excel templates need pandas/openpyxl.\n{exc}")
                return
        else:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(headers)
        QMessageBox.information(self, "Template", f"Template saved:\n{path}")

    def import_rows(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = self._read_import_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Import", f"Could not read file:\n{exc}")
            return
        if not rows:
            QMessageBox.information(self, "Import", "No rows found.")
            return
        if ImportPreviewDialog(self.spec, rows, self).exec() != QDialog.Accepted:
            return
        duplicates = sum(1 for row in rows if self._duplicate_exists(row))
        if duplicates:
            ask = QMessageBox.question(self, "Duplicate Rows", f"{duplicates} duplicate row(s) found. Import anyway?")
            if ask != QMessageBox.Yes:
                return
        username = str(self.main.current_user.get("username") or "")
        cols = self._insert_columns()
        imported = 0
        for row in rows:
            try:
                row = self._normalize_values(row)
            except ValueError:
                continue
            row["created_by"] = username
            row["created_at"] = datetime.now().isoformat(timespec="seconds")
            placeholders = ", ".join("?" for _ in cols)
            self.services.insert(
                f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(row.get(col) for col in cols),
            )
            imported += 1
        self.refresh()
        QMessageBox.information(self, "Imported", f"Imported {imported} row(s).")

    def _read_import_file(self, path: str) -> list[dict]:
        label_to_key = {field.label.replace(" *", "").strip().lower(): field.key for field in self.spec.fields}
        key_lookup = {field.key.lower(): field.key for field in self.spec.fields}
        if path.lower().endswith(".csv"):
            with open(path, newline="", encoding="utf-8-sig") as handle:
                source_rows = list(csv.DictReader(handle))
        else:
            import pandas as pd
            source_rows = pd.read_excel(path).fillna("").to_dict(orient="records")
        rows: list[dict] = []
        for source in source_rows:
            mapped: dict[str, Any] = {}
            for raw_key, value in source.items():
                key_text = str(raw_key).strip().lower()
                key = label_to_key.get(key_text) or key_lookup.get(key_text.replace(" ", "_"))
                if key:
                    mapped[key] = value
            for spec_field in self.spec.fields:
                mapped.setdefault(spec_field.key, "")
                if spec_field.numeric:
                    mapped[spec_field.key] = safe_float(mapped[spec_field.key])
            if any(str(value).strip() for value in mapped.values()):
                rows.append(mapped)
        return rows


class PhaseOneApprovalsPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk"):
        super().__init__()
        self.main = main
        self.desk = desk
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Pending Approvals")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        approve = QPushButton("Approve")
        approve.setObjectName("AccentButton")
        approve.clicked.connect(lambda: self.review(True))
        reject = QPushButton("Reject")
        reject.setObjectName("DangerButton")
        reject.clicked.connect(lambda: self.review(False))
        header.addWidget(refresh)
        header.addWidget(approve)
        header.addWidget(reject)
        layout.addLayout(header)
        self.table = QTableWidget()
        configure_multi_select_table(self.table)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.main.services.pending_approvals()
        headers = ["ID", "Action", "Table", "Record", "Requested By", "Requested At"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for row_idx, row in enumerate(self.rows):
            for col_idx, key in enumerate(["id", "action", "table_name", "record_id", "requested_by", "requested_at"]):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(key) or "")))
        self.table.horizontalHeader().setStretchLastSection(True)

    def selected(self) -> dict | None:
        indexes = selected_table_row_indexes(self.table, len(self.rows))
        if not indexes:
            QMessageBox.information(self, "Select", "Select a pending approval first.")
            return None
        return self.rows[indexes[0]]

    def review(self, approved: bool) -> None:
        row = self.selected()
        if not row:
            return
        full = self.main.services.fetch_one("SELECT * FROM pending_approvals WHERE id=?", (row["id"],))
        if not full:
            return
        if approved:
            self.apply_approval(full)
        self.main.services.review_approval(int(row["id"]), approved, str(self.main.current_user.get("username") or ""))
        self.refresh()
        self.desk.refresh_sections()

    def apply_approval(self, approval: dict) -> None:
        table = approval["table_name"]
        record_id = approval["record_id"]
        payload = json.loads(approval.get("payload") or "{}")
        username = str(self.main.current_user.get("username") or "")
        if approval["action"] == "edit":
            payload["last_edited_by"] = username
            payload["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            columns = self.main.services.table_columns(table)
            cols = [key for key in payload if key in columns]
            assignments = ", ".join(f"{col}=?" for col in cols)
            self.main.services.execute(
                f"UPDATE {table} SET {assignments} WHERE id=?",
                tuple(payload.get(col) for col in cols) + (record_id,),
            )
        elif approval["action"] == "delete":
            self.main.services.execute(
                f"UPDATE {table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                (approval.get("requested_by") or "", datetime.now().isoformat(timespec="seconds"), record_id),
            )
            self.main.log_audit("delete", table, int(record_id))
        elif approval["action"] == "restore":
            self.main.services.execute(
                f"UPDATE {table} SET is_deleted=0, deleted_by=NULL, deleted_at=NULL WHERE id=?",
                (record_id,),
            )


class SettingsListEditor(QWidget):
    def __init__(self, title: str, values: list[str], defaults: list[str]):
        super().__init__()
        self.title = title
        self.defaults = list(defaults)
        self.setObjectName("SettingsListEditor")
        self.setMinimumHeight(126)
        self.setMaximumHeight(148)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        top = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("SettingsListTitle")
        self.count_label = QLabel()
        self.count_label.setObjectName("SettingsCount")
        top.addWidget(label)
        top.addStretch(1)
        top.addWidget(self.count_label)
        layout.addLayout(top)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setMinimumHeight(40)
        self.list_widget.setMaximumHeight(54)
        self.list_widget.itemChanged.connect(lambda _item: self._refresh_count())
        layout.addWidget(self.list_widget, 1)

        entry_row = QHBoxLayout()
        entry_row.setSpacing(6)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(f"Add {title.lower()}")
        self.entry.returnPressed.connect(self.add_item)
        add = QPushButton("Add")
        add.setObjectName("AccentButton")
        add.clicked.connect(self.add_item)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_selected)
        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset_defaults)
        self.entry.setFixedHeight(30)
        for button in (add, remove, reset):
            button.setMinimumWidth(62)
            button.setFixedHeight(30)
        entry_row.addWidget(self.entry, 1)
        entry_row.addWidget(add)
        entry_row.addWidget(remove)
        entry_row.addWidget(reset)
        layout.addLayout(entry_row)

        self.set_values(values)

    def set_values(self, values: list[str]) -> None:
        self.list_widget.clear()
        for value in normalize_setting_lines("\n".join(values), self.defaults):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)
        self._refresh_count()

    def current_items(self) -> list[str]:
        return [
            self.list_widget.item(index).text().strip()
            for index in range(self.list_widget.count())
            if self.list_widget.item(index).text().strip()
        ]

    def values(self) -> list[str]:
        return normalize_setting_lines("\n".join(self.current_items()), self.defaults)

    def values_text(self) -> str:
        return "\n".join(self.values())

    def add_item(self) -> None:
        text = self.entry.text().strip()
        if not text:
            return
        existing = {self.list_widget.item(index).text().strip().lower() for index in range(self.list_widget.count())}
        if text.lower() not in existing:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)
        self.entry.clear()
        self._refresh_count()

    def remove_selected(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self._refresh_count()

    def reset_defaults(self) -> None:
        if QMessageBox.question(self, "Reset List", f"Reset {self.title} to defaults?") == QMessageBox.Yes:
            self.set_values(self.defaults)

    def _refresh_count(self) -> None:
        self.count_label.setText(f"{len(self.current_items())} items")


class PhaseOneSettingsPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk"):
        super().__init__()
        self.main = main
        self.desk = desk
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        title = QLabel("Phase 1 Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.company = QLineEdit(main.services.settings_get("company_name", main.company_name))
        self.address = QLineEdit(main.services.settings_get("company_address", ""))
        self.phone = QLineEdit(main.services.settings_get("company_phone", ""))
        self.email = QLineEdit(main.services.settings_get("company_email", ""))
        self.logo = QLineEdit(main.services.settings_get("company_logo", str(crm_logo_path())))
        self.currency = QLineEdit(main.services.settings_get("currency_symbol", "Rs."))
        self.default_commission = QLineEdit(main.services.settings_get("default_commission", ""))
        self.tax_rate = QLineEdit(main.services.settings_get("tax_rate", ""))
        self.bank_account = QLineEdit(main.services.settings_get("bank_account", ""))
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        self.areas = SettingsListEditor("Areas", setting_lines(main.services, "phase1_areas", COMMON_AREAS), COMMON_AREAS)
        self.facilities = SettingsListEditor("Facilities", setting_lines(main.services, "phase1_facilities", FACILITY_OPTIONS), FACILITY_OPTIONS)
        self.floors = SettingsListEditor("Floors", setting_lines(main.services, "phase1_floors", FLOOR_OPTIONS), FLOOR_OPTIONS)
        self.property_types = SettingsListEditor("Property Types", setting_lines(main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS), PROPERTY_TYPE_OPTIONS)
        self.measurement_units = SettingsListEditor("Measurement Units", setting_lines(main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS), MEASUREMENT_UNIT_OPTIONS)
        self.expense_categories = SettingsListEditor("Expense Categories", setting_lines(main.services, "expense_categories", list(EXPENSE_CATEGORIES)), list(EXPENSE_CATEGORIES))
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)
        form.addWidget(QLabel("Agency Name"), 0, 0)
        form.addWidget(self.company, 0, 1)
        form.addWidget(QLabel("Company Address"), 1, 0)
        form.addWidget(self.address, 1, 1, 1, 2)
        form.addWidget(QLabel("Company Phone"), 2, 0)
        form.addWidget(self.phone, 2, 1)
        form.addWidget(QLabel("Company Email"), 2, 2)
        form.addWidget(self.email, 2, 3)
        form.addWidget(QLabel("Logo Path"), 3, 0)
        form.addWidget(self.logo, 3, 1, 1, 2)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_logo)
        form.addWidget(browse, 3, 3)
        form.addWidget(QLabel("Currency Symbol"), 4, 0)
        form.addWidget(self.currency, 4, 1)
        form.addWidget(QLabel("Default Commission %"), 4, 2)
        form.addWidget(self.default_commission, 4, 3)
        form.addWidget(QLabel("Tax Rate %"), 5, 0)
        form.addWidget(self.tax_rate, 5, 1)
        form.addWidget(QLabel("Theme"), 5, 2)
        form.addWidget(self.theme, 5, 3)
        form.addWidget(QLabel("Bank Account"), 6, 0)
        form.addWidget(self.bank_account, 6, 1, 1, 3)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        layout.addLayout(form)
        list_grid = QGridLayout()
        list_grid.setHorizontalSpacing(10)
        list_grid.setVerticalSpacing(8)
        for index, editor in enumerate(
            (self.areas, self.facilities, self.floors, self.property_types, self.measurement_units, self.expense_categories)
        ):
            list_grid.addWidget(editor, index // 2, index % 2)
            list_grid.setColumnStretch(index % 2, 1)
        layout.addLayout(list_grid)
        save = QPushButton("Save Settings")
        save.setObjectName("AccentButton")
        save.setFixedHeight(42)
        save.clicked.connect(self.save)
        layout.addWidget(save)

    def browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose Logo", "", "Images (*.png *.jpg *.jpeg *.ico)")
        if path:
            self.logo.setText(path)

    def refresh(self) -> None:
        self.company.setText(self.main.services.settings_get("company_name", self.main.company_name))
        self.address.setText(self.main.services.settings_get("company_address", ""))
        self.phone.setText(self.main.services.settings_get("company_phone", ""))
        self.email.setText(self.main.services.settings_get("company_email", ""))
        self.logo.setText(self.main.services.settings_get("company_logo", str(crm_logo_path())))
        self.currency.setText(self.main.services.settings_get("currency_symbol", "Rs."))
        self.default_commission.setText(self.main.services.settings_get("default_commission", ""))
        self.tax_rate.setText(self.main.services.settings_get("tax_rate", ""))
        self.bank_account.setText(self.main.services.settings_get("bank_account", ""))
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        self.areas.set_values(setting_lines(self.main.services, "phase1_areas", COMMON_AREAS))
        self.facilities.set_values(setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        self.floors.set_values(setting_lines(self.main.services, "phase1_floors", FLOOR_OPTIONS))
        self.property_types.set_values(setting_lines(self.main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS))
        self.measurement_units.set_values(setting_lines(self.main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS))
        self.expense_categories.set_values(setting_lines(self.main.services, "expense_categories", list(EXPENSE_CATEGORIES)))

    def save(self) -> None:
        self.main.services.settings_set("company_name", self.company.text().strip())
        self.main.services.settings_set("company_address", self.address.text().strip())
        self.main.services.settings_set("company_phone", self.phone.text().strip())
        self.main.services.settings_set("company_email", self.email.text().strip())
        self.main.services.settings_set("company_logo", self.logo.text().strip())
        self.main.services.settings_set("currency_symbol", self.currency.text().strip())
        self.main.services.settings_set("default_commission", self.default_commission.text().strip())
        self.main.services.settings_set("tax_rate", self.tax_rate.text().strip())
        self.main.services.settings_set("bank_account", self.bank_account.text().strip())
        self.main.services.settings_set("phase1_theme", self.theme.currentText())
        self.main.services.settings_set("phase1_areas", self.areas.values_text())
        self.main.services.settings_set("phase1_facilities", self.facilities.values_text())
        self.main.services.settings_set("phase1_floors", self.floors.values_text())
        self.main.services.settings_set("phase1_property_types", self.property_types.values_text())
        self.main.services.settings_set("phase1_measurement_units", self.measurement_units.values_text())
        self.main.services.settings_set("expense_categories", self.expense_categories.values_text())
        self.main.reload_settings()
        self.main.reload_dynamic_specs()
        self.main.refresh_all_pages()
        QMessageBox.information(self, "Settings", "Settings saved.")


class PhaseOneDesk(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.section_specs = phase1_section_specs(main)
        self.section_pages: dict[str, PhaseOneSectionPage] = {}
        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.home = self._home_page()
        self.stack.addWidget(self.home)
        for key, spec in self.section_specs.items():
            page = PhaseOneSectionPage(main, self, spec)
            self.section_pages[key] = page
            self.stack.addWidget(page)
        if is_admin_role(main.role):
            self.approvals = PhaseOneApprovalsPage(main, self)
            self.settings = PhaseOneSettingsPage(main, self)
            self.stack.addWidget(self.approvals)
            self.stack.addWidget(self.settings)
        self.show_home()

    def reload_specs(self) -> None:
        self.section_specs = phase1_section_specs(self.main)
        for key, page in self.section_pages.items():
            if key in self.section_specs:
                page.spec = self.section_specs[key]

    def refresh(self) -> None:
        self.reload_specs()
        self.refresh_sections()
        if hasattr(self, "settings"):
            self.settings.refresh()

    def refresh_sections(self) -> None:
        for page in self.section_pages.values():
            page.refresh()

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("QT_CRM Data Desk")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        cards = [
            ("Rent Requirement", "rent_req"),
            ("Rent Availability", "rent_av"),
            ("Sale Requirement", "sale_req"),
            ("Sale Availability", "sale_av"),
        ]
        for index, (label, key) in enumerate(cards):
            button = QPushButton(label)
            button.setObjectName("PhaseCard")
            button.setMinimumHeight(110)
            button.clicked.connect(lambda _checked=False, k=key: self.open_section(k))
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)

        search_box = QFrame()
        search_box.setObjectName("Panel")
        search_layout = QVBoxLayout(search_box)
        search_title = QLabel("Search")
        search_title.setObjectName("SectionTitle")
        search_layout.addWidget(search_title)
        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Client, broker, owner name, contact, location, rooms, floor, facilities")
        search_btn = QPushButton("Search")
        search_btn.setObjectName("AccentButton")
        search_btn.clicked.connect(self.run_search)
        row.addWidget(self.search_input, 1)
        row.addWidget(search_btn)
        search_layout.addLayout(row)
        self.search_results = QVBoxLayout()
        search_layout.addLayout(self.search_results)
        layout.addWidget(search_box, 1)

        if is_admin_role(self.main.role):
            admin_row = QHBoxLayout()
            approvals = QPushButton("Pending Approvals")
            approvals.clicked.connect(lambda: self.stack.setCurrentWidget(self.approvals))
            settings = QPushButton("Phase 1 Settings")
            settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings))
            admin_row.addWidget(approvals)
            admin_row.addWidget(settings)
            admin_row.addStretch(1)
            layout.addLayout(admin_row)
        return page

    def show_home(self) -> None:
        self.stack.setCurrentWidget(self.home)

    def open_section(self, key: str) -> None:
        page = self.section_pages[key]
        page.refresh()
        self.stack.setCurrentWidget(page)

    def _clear_search_results(self) -> None:
        while self.search_results.count():
            item = self.search_results.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def run_search(self) -> None:
        query = self.search_input.text().strip().lower()
        self._clear_search_results()
        if not query:
            return
        for spec in self.section_specs.values():
            columns = [col.key for col in spec.columns]
            text_fields = [field.key for field in spec.fields if not field.numeric]
            clauses = " OR ".join(f"LOWER(COALESCE({field},'')) LIKE ?" for field in text_fields)
            params = tuple(f"%{query}%" for _ in text_fields)
            rows = self.main.services.fetch_all(
                f"SELECT {', '.join(columns)} FROM {spec.table} WHERE COALESCE(is_deleted,0)=0 AND ({clauses}) ORDER BY id DESC LIMIT 50",
                params,
            )
            label = QLabel(f"{spec.title} ({len(rows)})")
            label.setObjectName("SectionTitle")
            self.search_results.addWidget(label)
            table = QTableWidget()
            table.setMaximumHeight(210)
            table.setColumnCount(min(6, len(spec.columns)))
            table.setHorizontalHeaderLabels([col.label for col in spec.columns[:6]])
            table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                for col_idx, col in enumerate(spec.columns[:6]):
                    value = row.get(col.key)
                    text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                    table.setItem(row_idx, col_idx, QTableWidgetItem(text))
            table.horizontalHeader().setStretchLastSection(True)
            self.search_results.addWidget(table)

    def find_matches(self, requirement: dict, target: PhaseOneSectionSpec) -> list[dict]:
        rows = self.main.services.fetch_all(f"SELECT * FROM {target.table} WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        scored = []
        for row in rows:
            score, reasons = self._match_score(requirement, row, target)
            if score > 0:
                scored.append({"score": min(score, 100), "reasons": reasons, "row": row})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:50]

    def _match_score(self, req: dict, row: dict, target: PhaseOneSectionSpec) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        req_location = normalize_text(req.get("location"))
        row_location = normalize_text(row.get("location"))
        if req_location and row_location:
            if req_location == row_location:
                score += 45
                reasons.append("same location")
            elif self._nearby(req_location, row_location):
                score += 35
                reasons.append("nearby/similar location")
            elif req_location in row_location or row_location in req_location:
                score += 25
                reasons.append("similar location text")
        req_amount = safe_float(req.get("budget") or req.get("budget_max"))
        row_amount = safe_float(row.get(target.amount_key or "") if target.amount_key else 0)
        if req_amount and row_amount:
            if row_amount <= req_amount:
                score += 20
                reasons.append("price within budget")
            elif row_amount <= req_amount * 1.1:
                score += 12
                reasons.append("price near budget")
        if normalize_text(req.get("size")) and normalize_text(req.get("size")) == normalize_text(row.get("size")):
            score += 15
            reasons.append("matching rooms")
        if multi_option_overlap(req.get("floor"), row.get("floor"), FLOOR_OPTIONS):
            score += 10
            reasons.append("matching floor")
        req_facilities = parse_facilities(req.get("facilities"), setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        row_facilities = parse_facilities(row.get("facilities"), setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        overlap = req_facilities & row_facilities
        if overlap:
            score += min(10, len(overlap) * 3)
            reasons.append(f"{len(overlap)} facilities matched")
        return score, reasons

    def _nearby(self, left: str, right: str) -> bool:
        groups = [
            {"gizri", "dha", "defence", "dha phase 4", "dha phase 5", "dha phase 6", "zamzama", "clifton", "boat basin", "sea view", "marina"},
            {"clifton", "clifton block 1", "clifton block 2", "clifton block 3", "clifton block 4", "clifton block 5", "clifton block 6", "clifton block 7", "clifton block 8", "clifton block 9", "boat basin"},
            {"pechs", "tariq road", "bahadurabad", "kda scheme"},
            {"north nazimabad", "nazimabad", "fb area", "hyderi", "water pump"},
        ]
        return any(left in group and right in group for group in groups)


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
        self.rows = self.main.services.fetch_all(
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


REPORT_COLUMN_LABELS = {
    "section": "Section",
    "id": "ID",
    "date": "Date",
    "client_name": "Client",
    "owner_name": "Owner",
    "contact": "Contact",
    "property_requires": "Required",
    "property_availability": "Available",
    "size": "Rooms",
    "measurement": "Measurement",
    "measurement_unit": "Unit",
    "budget": "Budget",
    "monthly_rent": "Rent",
    "demand": "Demand",
    "floor": "Floor",
    "location": "Location",
    "workflow_stage": "Stage",
    "priority": "Priority",
    "assigned_to": "Assigned To",
    "deal_probability": "Probability",
    "approval_status": "Approval",
    "remarks": "Remarks",
}
REPORT_TABLE_COLUMNS = [
    "section", "id", "date", "client_name", "owner_name", "contact",
    "property_requires", "property_availability", "size", "measurement",
    "measurement_unit", "budget", "monthly_rent", "demand", "floor",
    "location", "workflow_stage", "priority", "assigned_to", "deal_probability",
    "approval_status", "remarks",
]
REPORT_MONEY_KEYS = {
    "budget", "monthly_rent", "demand", "amount", "rent", "price", "salary",
    "total_requirement_budget", "average_requirement_budget", "total_monthly_rent",
    "average_monthly_rent", "total_owner_demand", "average_owner_demand",
    "total_income", "total_expense", "net_profit", "total_payroll",
}


def report_label(key: str) -> str:
    return REPORT_COLUMN_LABELS.get(key, key.replace("_", " ").title())


def report_display_value(key: str, value: Any, currency_symbol: str) -> str:
    if value in (None, ""):
        return "-"
    if key in REPORT_MONEY_KEYS or any(token in key for token in ("amount", "budget", "rent", "demand", "salary", "income", "expense", "profit")):
        return money(value, currency_symbol)
    if "date" in key or key.endswith("_at"):
        return format_date_display(value)
    if key.endswith("pct") or key.endswith("percent") or "probability" in key or "margin" in key:
        return f"{safe_float(value):.0f}%"
    return str(value)


def report_summary_html(summary: dict, currency_symbol: str) -> str:
    if not summary:
        return ""
    cards: list[tuple[str, str]] = []
    detail_sections: list[str] = []
    for key, value in summary.items():
        if isinstance(value, dict):
            rows = "".join(
                "<tr>"
                f"<td>{html.escape(report_label(str(sub_key)))}</td>"
                f"<td>{html.escape(report_display_value(str(sub_key), sub_value, currency_symbol))}</td>"
                "</tr>"
                for sub_key, sub_value in value.items()
            )
            if rows:
                detail_sections.append(
                    "<div class='summary-table'>"
                    f"<h3>{html.escape(report_label(key))}</h3>"
                    f"<table>{rows}</table>"
                    "</div>"
                )
        else:
            cards.append((report_label(key), report_display_value(key, value, currency_symbol)))
    card_rows = []
    for offset in range(0, len(cards), 4):
        cells = []
        for label, value in cards[offset:offset + 4]:
            cells.append(
                "<td class='metric'>"
                f"<span>{html.escape(label)}</span>"
                f"<strong>{html.escape(value)}</strong>"
                "</td>"
            )
        while len(cells) < 4:
            cells.append("<td class='metric metric-empty'></td>")
        card_rows.append(f"<tr>{''.join(cells)}</tr>")
    card_html = f"<table class='metrics-table'>{''.join(card_rows)}</table>" if card_rows else ""
    detail_rows = []
    for offset in range(0, len(detail_sections), 2):
        left = detail_sections[offset]
        right = detail_sections[offset + 1] if offset + 1 < len(detail_sections) else ""
        detail_rows.append(f"<tr><td>{left}</td><td>{right}</td></tr>")
    detail_html = f"<table class='summary-grid'>{''.join(detail_rows)}</table>" if detail_rows else ""
    return card_html + detail_html


def report_rows_html(rows: list[dict], currency_symbol: str) -> str:
    if not rows:
        return ""
    present = {key for row in rows for key in row if row.get(key) not in (None, "")}
    columns = [key for key in REPORT_TABLE_COLUMNS if key in present]
    columns += sorted(present - set(columns))
    if not columns:
        return ""
    header = "".join(f"<th>{html.escape(report_label(key))}</th>" for key in columns)
    body_rows = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(report_display_value(key, row.get(key), currency_symbol))}</td>"
            for key in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        "<section class='table-section'>"
        "<h3>Record Detail</h3>"
        "<table class='records-table'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</section>"
    )


def report_result_html(result: ReportResult, company_name: str, currency_symbol: str) -> str:
    generated = result.generated_at.strftime("%d/%m/%Y %I:%M %p")
    rows_html = report_rows_html(result.rows, currency_symbol)
    text_html = ""
    if not rows_html:
        text_html = f"<pre>{html.escape(result.text or 'No report data generated.')}</pre>"
    return f"""
    <html>
    <head>
      <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #102033; margin: 0; }}
        .page {{ padding: 18px 20px; }}
        .report-header {{ width: 100%; border-bottom: 3px solid #2563eb; padding-bottom: 12px; margin-bottom: 14px; }}
        h1 {{ margin: 0 0 5px; font-size: 24px; color: #0f172a; }}
        h2, h3 {{ margin: 0; color: #0f172a; }}
        .meta {{ color: #52647a; font-size: 11px; line-height: 1.45; text-align: right; }}
        .company {{ color: #1d4ed8; font-size: 13px; font-weight: 800; }}
        .metrics-table {{ margin: 12px 0; border-collapse: separate; border-spacing: 7px; }}
        .metric {{ border: 1px solid #d8e2ef; border-radius: 7px; padding: 9px; background: #f8fbff; width: 25%; }}
        .metric-empty {{ border: none; background: transparent; }}
        .metric span {{ display: block; color: #64748b; font-size: 9px; font-weight: 800; text-transform: uppercase; }}
        .metric strong {{ display: block; margin-top: 4px; color: #0f172a; font-size: 16px; }}
        .summary-grid {{ margin: 12px 0; border-collapse: separate; border-spacing: 8px; }}
        .summary-grid > tr > td, .summary-grid td {{ vertical-align: top; width: 50%; border: none; padding: 0; }}
        .summary-table {{ border: 1px solid #d8e2ef; border-radius: 7px; overflow: hidden; }}
        .summary-table h3, .table-section h3 {{ padding: 8px 10px; background: #eef6ff; font-size: 13px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #0f4387; color: white; font-size: 9px; padding: 6px; text-align: left; }}
        td {{ border-bottom: 1px solid #e5edf6; font-size: 9px; padding: 5px 6px; vertical-align: top; }}
        tbody tr:nth-child(even) td {{ background: #f8fbff; }}
        .table-section {{ margin-top: 12px; border: 1px solid #d8e2ef; border-radius: 7px; overflow: hidden; }}
        pre {{ white-space: pre-wrap; font-family: Consolas, monospace; font-size: 10px; border: 1px solid #d8e2ef; padding: 12px; border-radius: 7px; background: #fbfdff; }}
        .footer {{ margin-top: 14px; color: #64748b; font-size: 9px; text-align: right; }}
      </style>
    </head>
    <body>
      <div class='page'>
        <table class='report-header'><tr>
          <td>
            <h1>{html.escape(result.title)}</h1>
            <div class='company'>{html.escape(company_name)}</div>
          </td>
          <td class='meta'>Generated: {html.escape(generated)}<br>Records: {len(result.rows):,}</td>
        </tr></table>
        {report_summary_html(result.summary, currency_symbol)}
        {rows_html}
        {text_html}
        <div class='footer'>Printed from Real Estate CRM</div>
      </div>
    </body>
    </html>
    """


def report_document(result: ReportResult, main: "ModernCRMWindow") -> QTextDocument:
    doc = QTextDocument()
    doc.setHtml(report_result_html(result, main.company_name, main.currency_symbol))
    return doc


def print_report_result(result: ReportResult, main: "ModernCRMWindow", parent: QWidget) -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    configure_legal_landscape_printer(printer)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(f"Print {result.title}")
    if dialog.exec() == QDialog.Accepted:
        report_document(result, main).print_(printer)


def write_report_pdf(result: ReportResult, main: "ModernCRMWindow", path: str) -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    configure_legal_landscape_printer(printer)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    report_document(result, main).print_(printer)


def save_report_pdf(result: ReportResult, main: "ModernCRMWindow", parent: QWidget) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    default_name = f"{result.filename_slug}_{datetime.now().strftime('%Y%m%d')}.pdf"
    path, _ = QFileDialog.getSaveFileName(parent, "Save Report PDF", str(OUTPUT_DIR / default_name), "PDF Files (*.pdf)")
    if not path:
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    write_report_pdf(result, main, path)
    QMessageBox.information(parent, "Saved", f"Report PDF saved:\n{path}")


class ReportsModule(QWidget):
    QUICK_REPORTS = [
        ("Rent Report", "rent"),
        ("Sale Report", "sale"),
        ("Combined Report", "rent + sale"),
        ("Financial", "financial"),
        ("Properties", "properties"),
        ("Clients", "clients"),
    ]

    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.last_report: ReportResult | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel("Reports")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        report_shell = QFrame()
        report_shell.setObjectName("ReportShell")
        shell_layout = QVBoxLayout(report_shell)
        shell_layout.setContentsMargins(14, 14, 14, 14)
        shell_layout.setSpacing(12)

        quick = QGridLayout()
        quick.setHorizontalSpacing(10)
        quick.setVerticalSpacing(10)
        for index, (label, key) in enumerate(self.QUICK_REPORTS):
            button = QPushButton(label)
            button.setObjectName("ReportQuickButton" if index else "ReportQuickButtonActive")
            button.clicked.connect(lambda _checked=False, report_key=key: self.generate(report_key))
            quick.addWidget(button, index // 3, index % 3)
            quick.setColumnStretch(index % 3, 1)
        shell_layout.addLayout(quick)

        controls_frame = QFrame()
        controls_frame.setObjectName("ReportControls")
        controls = QHBoxLayout(controls_frame)
        controls.setContentsMargins(10, 10, 10, 10)
        controls.setSpacing(10)
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
        print_btn = QPushButton("Print")
        print_btn.clicked.connect(self.print_report)
        pdf_btn = QPushButton("Save PDF")
        pdf_btn.clicked.connect(self.save_pdf)
        export = QPushButton("Export Data")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Report"))
        controls.addWidget(self.report_type)
        controls.addWidget(QLabel("From"))
        controls.addWidget(self.start_date)
        controls.addWidget(QLabel("To"))
        controls.addWidget(self.end_date)
        controls.addStretch(1)
        controls.addWidget(generate)
        controls.addWidget(print_btn)
        controls.addWidget(pdf_btn)
        controls.addWidget(export)
        shell_layout.addWidget(controls_frame)

        self.preview = QTextEdit()
        self.preview.setObjectName("ReportPreview")
        self.preview.setReadOnly(True)
        self.preview.setHtml(self._empty_preview_html())
        shell_layout.addWidget(self.preview, 1)
        layout.addWidget(report_shell, 1)

    def generate(self, report_type: str | None = None) -> None:
        kind = (report_type or self.report_type.currentText()).lower()
        self.report_type.setCurrentText(self._report_label_for_kind(kind))
        start = self.start_date.date().toString(DATE_STORAGE_FORMAT)
        end = self.end_date.date().toString(DATE_STORAGE_FORMAT)
        svc = self.main.report_service
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
        self.last_report = result
        self.main.last_report = result
        self.preview.setHtml(report_result_html(result, self.main.company_name, self.main.currency_symbol))
        self.main.update_status_bar(f"{result.title} ready to print")

    def _report_label_for_kind(self, kind: str) -> str:
        labels = {
            "rent": "Rent",
            "sale": "Sale",
            "rent + sale": "Rent + Sale",
            "financial": "Financial",
            "properties": "Properties",
            "clients": "Clients",
            "employees": "Employees",
            "attendance": "Attendance",
        }
        return labels.get(kind, self.report_type.currentText())

    def _empty_preview_html(self) -> str:
        return """
        <div style='font-family:Segoe UI,Arial;padding:34px;color:#52647a'>
          <h2 style='color:#0f172a;margin:0 0 8px'>Ready to generate</h2>
          <p style='margin:0'>Choose a report, date range, then use Generate. Print and PDF use the formatted preview.</p>
        </div>
        """

    def _require_report(self) -> ReportResult | None:
        if self.last_report:
            return self.last_report
        QMessageBox.information(self, "Report", "Generate a report first.")
        return None

    def print_report(self) -> None:
        result = self._require_report()
        if result:
            print_report_result(result, self.main, self)

    def save_pdf(self) -> None:
        result = self._require_report()
        if result:
            save_report_pdf(result, self.main, self)

    def export(self) -> None:
        result = self._require_report()
        if not result:
            return
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            str(OUTPUT_DIR / f"{result.filename_slug}.csv"),
            "PDF Files (*.pdf);;CSV Files (*.csv);;Text Files (*.txt)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if suffix == ".csv" or "CSV" in selected_filter:
            export_report_csv(result, path)
        elif suffix == ".txt" or "Text" in selected_filter:
            export_report_text(result, path)
        else:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            write_report_pdf(result, self.main, path)
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
        self.main = parent if hasattr(parent, "company_name") and hasattr(parent, "currency_symbol") else None
        self.setWindowTitle(result.title)
        self.resize(980, 680)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel(result.title)
        title.setObjectName("DialogTitle")
        header.addWidget(title)
        header.addStretch(1)
        print_btn = QPushButton("Print")
        save_pdf_btn = QPushButton("Save PDF")
        csv_btn = QPushButton("Export CSV")
        txt = QPushButton("Export TXT")
        print_btn.setObjectName("AccentButton")
        print_btn.clicked.connect(self.print_report)
        save_pdf_btn.clicked.connect(self.save_pdf)
        csv_btn.clicked.connect(lambda: self.export("csv"))
        txt.clicked.connect(lambda: self.export("txt"))
        header.addWidget(print_btn)
        header.addWidget(save_pdf_btn)
        header.addWidget(csv_btn)
        header.addWidget(txt)
        layout.addLayout(header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        if self.main:
            self.preview.setHtml(report_result_html(result, self.main.company_name, self.main.currency_symbol))
        else:
            self.preview.setPlainText(result.text)
        layout.addWidget(self.preview, 1)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

    def print_report(self) -> None:
        if self.main:
            print_report_result(self.result, self.main, self)
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.Accepted:
            doc = QTextDocument()
            doc.setPlainText(self.result.text)
            doc.print_(printer)

    def save_pdf(self) -> None:
        if self.main:
            save_report_pdf(self.result, self.main, self)
            return
        self.export("pdf")

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
        if kind == "pdf":
            if self.main:
                write_report_pdf(self.result, self.main, path)
            else:
                export_report_pdf(self.result, path)
        elif kind == "csv":
            export_report_csv(self.result, path)
        else:
            export_report_text(self.result, path)
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


class SettingsModule(QWidget):
    KEYS = [
        ("Company Name", "company_name"),
        ("Company Address", "company_address"),
        ("Company Phone", "company_phone"),
        ("Company Email", "company_email"),
        ("Logo Path", "company_logo"),
        ("Currency Symbol", "currency_symbol"),
        ("Default Commission %", "default_commission"),
        ("Tax Rate %", "tax_rate"),
        ("Bank Account", "bank_account"),
    ]
    LIST_KEYS = [
        ("Locations", "phase1_areas", COMMON_AREAS),
        ("Facilities", "phase1_facilities", FACILITY_OPTIONS),
        ("Floors", "phase1_floors", FLOOR_OPTIONS),
        ("Property Types", "phase1_property_types", PROPERTY_TYPE_OPTIONS),
        ("Measurement Units", "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS),
        ("Expense Categories", "expense_categories", list(EXPENSE_CATEGORIES)),
    ]

    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.inputs: dict[str, QLineEdit] = {}
        self.list_inputs: dict[str, SettingsListEditor] = {}
        self.theme = QComboBox()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._company_tab(), "Company")
        tabs.addTab(self._crm_lists_tab(), "CRM Lists")
        tabs.addTab(self._financial_tab(), "Financial")
        layout.addWidget(tabs, 1)

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

    def _line_input(self, key: str) -> QLineEdit:
        edit = QLineEdit(self.main.services.settings_get(key))
        self.inputs[key] = edit
        return edit

    def _add_form_row(self, layout: QGridLayout, row: int, col: int, label: str, widget: QWidget) -> None:
        label_widget = QLabel(label)
        label_widget.setObjectName("FormLabel")
        layout.addWidget(label_widget, row, col * 2)
        layout.addWidget(widget, row, col * 2 + 1)

    def _scroll_page(self, body: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        return scroll

    def _company_tab(self) -> QScrollArea:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        panel = QFrame()
        panel.setObjectName("Panel")
        form = QGridLayout(panel)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self._add_form_row(form, 0, 0, "Company Name", self._line_input("company_name"))
        self._add_form_row(form, 0, 1, "Company Phone", self._line_input("company_phone"))
        self._add_form_row(form, 1, 0, "Company Email", self._line_input("company_email"))
        self._add_form_row(form, 1, 1, "Logo Path", self._line_input("company_logo"))
        self._add_form_row(form, 2, 0, "Company Address", self._line_input("company_address"))
        self.theme.addItems(["Light", "Dark"])
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        self._add_form_row(form, 2, 1, "Theme", self.theme)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        layout.addWidget(panel)
        layout.addStretch(1)
        return self._scroll_page(body)

    def _crm_lists_tab(self) -> QScrollArea:
        body = QWidget()
        layout = QGridLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        crm_keys = {"phase1_areas", "phase1_facilities", "phase1_floors", "phase1_property_types", "phase1_measurement_units"}
        index = 0
        for label, key, defaults in self.LIST_KEYS:
            if key not in crm_keys:
                continue
            editor = SettingsListEditor(label, setting_lines(self.main.services, key, defaults), defaults)
            self.list_inputs[key] = editor
            layout.addWidget(editor, index // 2, index % 2)
            layout.setColumnStretch(index % 2, 1)
            index += 1
        return self._scroll_page(body)

    def _financial_tab(self) -> QScrollArea:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        panel = QFrame()
        panel.setObjectName("Panel")
        form = QGridLayout(panel)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self._add_form_row(form, 0, 0, "Currency Symbol", self._line_input("currency_symbol"))
        self._add_form_row(form, 0, 1, "Default Commission %", self._line_input("default_commission"))
        self._add_form_row(form, 1, 0, "Tax Rate %", self._line_input("tax_rate"))
        self._add_form_row(form, 1, 1, "Bank Account", self._line_input("bank_account"))
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        layout.addWidget(panel)
        label, key, defaults = next(item for item in self.LIST_KEYS if item[1] == "expense_categories")
        editor = SettingsListEditor(label, setting_lines(self.main.services, key, defaults), defaults)
        self.list_inputs[key] = editor
        layout.addWidget(editor, 1)
        return self._scroll_page(body)

    def save(self) -> None:
        for key, widget in self.inputs.items():
            self.main.services.settings_set(key, widget.text().strip())
        self.main.services.settings_set("phase1_theme", self.theme.currentText())
        for key, widget in self.list_inputs.items():
            self.main.services.settings_set(key, widget.values_text())
        self.main.reload_settings()
        self.main.reload_dynamic_specs()
        self.main.refresh_all_pages()
        QMessageBox.information(self, "Settings", "Settings saved.")

    def refresh(self) -> None:
        for _label, key in self.KEYS:
            if key in self.inputs:
                self.inputs[key].setText(self.main.services.settings_get(key))
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        for _label, key, defaults in self.LIST_KEYS:
            if key in self.list_inputs:
                self.list_inputs[key].set_values(setting_lines(self.main.services, key, defaults))

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
            "property_requires": "Property Required / Needed",
            "property_availability": "Property Available",
            "size": "Rooms",
            "measurement": "Measurement",
            "measurement_unit": "Size",
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
        specs = FIND_RESULT_COLUMNS.get(table, [])
        if not specs:
            for key in self.table_columns(table):
                normalized[key] = row.get(key)
                if key not in columns:
                    columns.append(key)
            normalized["_columns"] = columns
            return normalized
        for key, _label, aliases, default in specs:
            normalized[key] = self.result_value(row, aliases, default)
            if key not in columns:
                columns.append(key)
        normalized["_columns"] = columns
        return normalized

    def display_schema(self, rows: list[dict]) -> tuple[list[str], dict[str, str]]:
        selected_table = self.source_filter.currentData()
        if selected_table:
            specs = FIND_RESULT_COLUMNS.get(selected_table, [])
            if specs:
                return [key for key, _label, _aliases, _default in specs], {
                    key: label for key, label, _aliases, _default in specs
                }
            columns = ["_source"] + self.table_columns(selected_table)
            return columns, {key: self.field_label(key) for key in columns}

        present: set[str] = set()
        for row in rows:
            present.update(row.get("_columns", []))
        columns = [key for key in FIND_ALL_COLUMN_ORDER if key in present]
        columns.extend(sorted(key for key in present if key not in columns and key not in GLOBAL_SEARCH_HIDDEN_COLUMNS))
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


# SuccessFactors module

class SFEmployeeCentralPage(DataTablePage):
    """SF Employee Central."""
    pass


class SFRecruitingPage(DataTablePage):
    """SF Recruiting."""
    pass


class SFPerformancePage(DataTablePage):
    """SF Performance and Goals."""
    pass


class SFMustWinBattlesPage(DataTablePage):
    """SF Must Win Battles."""
    pass


class SFKPIsPage(DataTablePage):
    """SF KPIs."""
    pass


class SFLearningPage(DataTablePage):
    """SF Learning Management."""
    pass


class SFCompensationPage(DataTablePage):
    """SF Compensation."""
    pass


class SFOnboardingPage(DataTablePage):
    """SF Onboarding."""
    pass


class SFPositionsPage(DataTablePage):
    """SF Org Chart and Position Management."""
    pass


class SFDashboardPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("SuccessFactors Overview")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        self.cards_layout = QGridLayout()
        layout.addLayout(self.cards_layout)
        layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def count(table: str) -> int:
            row = self.main.services.fetch_one(f"SELECT COUNT(*) AS c FROM {table}")
            return int(row["c"]) if row else 0

        metrics = [
            ("SF Employees", count("sf_employees"), "blue"),
            ("Open Positions", count("sf_positions"), "cyan"),
            ("Active Recruitments", count("sf_recruiting"), "royal"),
            ("Goals In Progress", count("sf_performance_goals"), "green"),
            ("Must Win Battles", count("sf_must_win_battles"), "slate"),
            ("KPIs Tracked", count("sf_kpis"), "sky"),
            ("Learning Assigned", count("sf_learning"), "sky"),
            ("Onboarding Tasks", count("sf_onboarding"), "slate"),
        ]
        for index, (label, value, tone) in enumerate(metrics):
            tile = self.main._dashboard_tile(label, value, tone)
            self.cards_layout.addWidget(tile, index // 3, index % 3)
            self.cards_layout.setColumnStretch(index % 3, 1)


def _sf_employee_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("SF Employee ID", "sf_employee_id"),
        FieldSpec("Full Name *", "full_name", required=True),
        FieldSpec("Email", "email"),
        FieldSpec("Department *", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"], required=True),
        FieldSpec("Job Title *", "job_title", required=True),
        FieldSpec("Manager", "manager_name"),
        FieldSpec("Hire Date", "hire_date", "date"),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Cost Center", "cost_center"),
        FieldSpec("Status", "employment_status", "combo", "Active", ["Active", "On Leave", "Terminated", "Suspended"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("sf_employee_id", "SF ID", width=110),
        ColumnSpec("full_name", "Name", width=170),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("job_title", "Job Title", width=150),
        ColumnSpec("manager_name", "Manager", width=140),
        ColumnSpec("hire_date", "Hire Date", d, 100),
        ColumnSpec("employment_status", "Status", width=100),
        ColumnSpec("location", "Location", width=140),
        ColumnSpec("cost_center", "Cost Center", width=110),
    ]
    insert = [
        "sf_employee_id", "full_name", "email", "department", "job_title",
        "manager_name", "hire_date", "location", "cost_center",
        "employment_status", "notes", "created_by", "created_at",
    ]
    update = [
        "sf_employee_id", "full_name", "email", "department", "job_title",
        "manager_name", "hire_date", "location", "cost_center",
        "employment_status", "notes",
    ]
    return TableSpec("SF Employee Central", "sf_employees", cols, fields, insert, update, permission="successfactors")


def _sf_recruiting_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Requisition ID", "job_requisition_id"),
        FieldSpec("Job Title *", "job_title", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Hiring Manager", "hiring_manager"),
        FieldSpec("Recruiter", "recruiter"),
        FieldSpec("Open Date", "open_date", "date"),
        FieldSpec("Close Date", "close_date", "date"),
        FieldSpec("Status", "status", "combo", "Open", ["Open", "On Hold", "Filled", "Cancelled"]),
        FieldSpec("Applications", "applications_count", numeric=True),
        FieldSpec("Shortlisted", "shortlisted_count", numeric=True),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("job_requisition_id", "Req ID", width=110),
        ColumnSpec("job_title", "Job Title", width=180),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("hiring_manager", "Hiring Mgr", width=140),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("open_date", "Open Date", d, 100),
        ColumnSpec("close_date", "Close Date", d, 100),
        ColumnSpec("applications_count", "Applications", width=110),
        ColumnSpec("shortlisted_count", "Shortlisted", width=100),
    ]
    insert = [
        "job_requisition_id", "job_title", "department", "location",
        "hiring_manager", "recruiter", "open_date", "close_date", "status",
        "applications_count", "shortlisted_count", "notes", "created_by", "created_at",
    ]
    update = [
        "job_requisition_id", "job_title", "department", "location",
        "hiring_manager", "recruiter", "open_date", "close_date", "status",
        "applications_count", "shortlisted_count", "notes",
    ]
    return TableSpec("SF Recruiting", "sf_recruiting", cols, fields, insert, update, permission="successfactors")


def _sf_performance_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Goal Title *", "goal_title", required=True),
        FieldSpec("Description", "goal_description", "text"),
        FieldSpec("Review Period", "review_period", "combo_other", options=["Q1", "Q2", "Q3", "Q4", "H1", "H2", "Annual"]),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Progress %", "progress_pct", numeric=True),
        FieldSpec("Status", "status", "combo", "In Progress", ["In Progress", "Completed", "On Hold", "Cancelled"]),
        FieldSpec("Rating", "rating", "combo", options=["", "Exceeds", "Meets", "Below", "N/A"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("goal_title", "Goal", width=220),
        ColumnSpec("review_period", "Period", width=90),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("progress_pct", "Progress", pct, 90),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("rating", "Rating", width=90),
    ]
    insert = [
        "employee_name", "goal_title", "goal_description", "review_period",
        "due_date", "progress_pct", "status", "rating", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "goal_title", "goal_description", "review_period",
        "due_date", "progress_pct", "status", "rating", "notes",
    ]
    return TableSpec("SF Performance & Goals", "sf_performance_goals", cols, fields, insert, update, permission="successfactors")


def _sf_must_win_battles_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("Battle Code", "battle_code", "entry", lambda: gen_id("MWB")),
        FieldSpec("Battle Title *", "battle_title", required=True),
        FieldSpec("Owner Name *", "owner_name", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Objective", "objective", "text"),
        FieldSpec("Start Date", "start_date", "date"),
        FieldSpec("End Date", "end_date", "date"),
        FieldSpec("Priority", "priority", "combo", "High", ["Low", "Medium", "High", "Critical"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "At Risk", "Won", "Lost", "On Hold"]),
        FieldSpec("Target Value", "target_value", numeric=True),
        FieldSpec("Current Value", "current_value", numeric=True),
        FieldSpec("Progress %", "progress_pct", numeric=True),
        FieldSpec("Business Impact", "business_impact", "combo_other", options=["Revenue", "Cost Saving", "Customer Growth", "Operational Excellence", "Compliance", "People"]),
        FieldSpec("Risks / Blockers", "risks", "text"),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("battle_code", "Code", width=110),
        ColumnSpec("battle_title", "Must Win Battle", width=220),
        ColumnSpec("owner_name", "Owner", width=150),
        ColumnSpec("department", "Department", width=120),
        ColumnSpec("start_date", "Start", d, 100),
        ColumnSpec("end_date", "End", d, 100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("priority", "Priority", width=90),
        ColumnSpec("progress_pct", "Progress", pct, 90),
        ColumnSpec("business_impact", "Impact", width=160),
    ]
    insert = [
        "battle_code", "battle_title", "owner_name", "department", "objective",
        "start_date", "end_date", "priority", "status", "target_value",
        "current_value", "progress_pct", "business_impact", "risks", "notes",
        "created_by", "created_at",
    ]
    update = [
        "battle_code", "battle_title", "owner_name", "department", "objective",
        "start_date", "end_date", "priority", "status", "target_value",
        "current_value", "progress_pct", "business_impact", "risks", "notes",
    ]
    return TableSpec("SF Must Win Battles", "sf_must_win_battles", cols, fields, insert, update, permission="successfactors")


def _sf_kpis_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("KPI Code", "kpi_code", "entry", lambda: gen_id("KPI")),
        FieldSpec("KPI Name *", "kpi_name", required=True),
        FieldSpec("Employee Name", "employee_name"),
        FieldSpec("Owner Name", "owner_name"),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Category", "category", "combo_other", options=["Revenue", "Sales", "Operations", "Customer", "People", "Compliance", "Quality"]),
        FieldSpec("Period", "period", "combo_other", options=["Q1", "Q2", "Q3", "Q4", "H1", "H2", "Annual", "Monthly"]),
        FieldSpec("Start Date", "start_date", "date"),
        FieldSpec("End Date", "end_date", "date"),
        FieldSpec("Target Value", "target_value", numeric=True),
        FieldSpec("Actual Value", "actual_value", numeric=True),
        FieldSpec("Unit", "unit", "combo_other", options=["Count", "PKR", "USD", "%", "Days", "Hours", "Score"]),
        FieldSpec("Weight %", "weight_pct", numeric=True),
        FieldSpec("Achievement %", "achievement_pct", numeric=True),
        FieldSpec("Status", "status", "combo", "On Track", ["Not Started", "On Track", "At Risk", "Off Track", "Completed"]),
        FieldSpec("Review Date", "review_date", "date"),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("kpi_code", "Code", width=110),
        ColumnSpec("kpi_name", "KPI", width=220),
        ColumnSpec("employee_name", "Employee", width=150),
        ColumnSpec("owner_name", "Owner", width=140),
        ColumnSpec("department", "Department", width=120),
        ColumnSpec("period", "Period", width=90),
        ColumnSpec("target_value", "Target", width=100),
        ColumnSpec("actual_value", "Actual", width=100),
        ColumnSpec("achievement_pct", "Achievement", pct, 105),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("review_date", "Review", d, 100),
    ]
    insert = [
        "kpi_code", "kpi_name", "employee_name", "owner_name", "department",
        "category", "period", "start_date", "end_date", "target_value",
        "actual_value", "unit", "weight_pct", "achievement_pct", "status",
        "review_date", "notes", "created_by", "created_at",
    ]
    update = [
        "kpi_code", "kpi_name", "employee_name", "owner_name", "department",
        "category", "period", "start_date", "end_date", "target_value",
        "actual_value", "unit", "weight_pct", "achievement_pct", "status",
        "review_date", "notes",
    ]
    return TableSpec("SF KPIs", "sf_kpis", cols, fields, insert, update, permission="successfactors")


def _sf_learning_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Course Title *", "course_title", required=True),
        FieldSpec("Course Code", "course_code"),
        FieldSpec("Category", "category", "combo_other", options=["Compliance", "Technical", "Soft Skills", "Leadership", "Safety", "Induction"]),
        FieldSpec("Instructor", "instructor"),
        FieldSpec("Assigned Date", "assigned_date", "date"),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Completion Date", "completion_date", "date"),
        FieldSpec("Status", "status", "combo", "Assigned", ["Assigned", "In Progress", "Completed", "Overdue", "Waived"]),
        FieldSpec("Score", "score", numeric=True),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=160),
        ColumnSpec("course_title", "Course", width=220),
        ColumnSpec("category", "Category", width=120),
        ColumnSpec("assigned_date", "Assigned", d, 100),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("completion_date", "Completed", d, 100),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("score", "Score", width=80),
    ]
    insert = [
        "employee_name", "course_title", "course_code", "category", "instructor",
        "assigned_date", "due_date", "completion_date", "status", "score", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "course_title", "course_code", "category", "instructor",
        "assigned_date", "due_date", "completion_date", "status", "score", "notes",
    ]
    return TableSpec("SF Learning (LMS)", "sf_learning", cols, fields, insert, update, permission="successfactors")


def _sf_compensation_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Base Salary *", "base_salary", numeric=True, required=True),
        FieldSpec("Bonus", "bonus", numeric=True),
        FieldSpec("Allowances", "allowances", numeric=True),
        FieldSpec("Total Compensation", "total_compensation", numeric=True),
        FieldSpec("Currency", "currency", "combo", "PKR", ["PKR", "USD", "AED", "GBP"]),
        FieldSpec("Effective Date", "effective_date", "date"),
        FieldSpec("Review Cycle", "review_cycle", "combo_other", options=["Annual", "Semi-Annual", "Quarterly"]),
        FieldSpec("Approved By", "approved_by"),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Pending", "Expired"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("base_salary", "Base Salary", m, 130),
        ColumnSpec("bonus", "Bonus", m, 110),
        ColumnSpec("allowances", "Allowances", m, 110),
        ColumnSpec("total_compensation", "Total", m, 130),
        ColumnSpec("currency", "Currency", width=80),
        ColumnSpec("effective_date", "Effective", d, 100),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = [
        "employee_name", "base_salary", "bonus", "allowances", "total_compensation",
        "currency", "effective_date", "review_cycle", "approved_by", "status", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "base_salary", "bonus", "allowances", "total_compensation",
        "currency", "effective_date", "review_cycle", "approved_by", "status", "notes",
    ]
    return TableSpec("SF Compensation", "sf_compensation", cols, fields, insert, update, permission="successfactors")


def _sf_onboarding_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Task Title *", "task_title", required=True),
        FieldSpec("Category", "task_category", "combo_other", options=["Documentation", "IT Setup", "Training", "Orientation", "Compliance", "Access"]),
        FieldSpec("Assigned To", "assigned_to"),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Completion Date", "completion_date", "date"),
        FieldSpec("Status", "status", "combo", "Pending", ["Pending", "In Progress", "Completed", "Waived"]),
        FieldSpec("Priority", "priority", "combo", "Medium", ["Low", "Medium", "High", "Critical"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("task_title", "Task", width=220),
        ColumnSpec("task_category", "Category", width=130),
        ColumnSpec("assigned_to", "Assigned To", width=130),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("priority", "Priority", width=90),
    ]
    insert = [
        "employee_name", "task_title", "task_category", "assigned_to",
        "due_date", "completion_date", "status", "priority", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "task_title", "task_category", "assigned_to",
        "due_date", "completion_date", "status", "priority", "notes",
    ]
    return TableSpec("SF Onboarding", "sf_onboarding", cols, fields, insert, update, permission="successfactors")


def _sf_positions_spec() -> TableSpec:
    fields = [
        FieldSpec("Position Code", "position_code", "entry", lambda: gen_id("POS")),
        FieldSpec("Position Title *", "position_title", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Max Headcount", "headcount_max", numeric=True),
        FieldSpec("Current Headcount", "headcount_current", numeric=True),
        FieldSpec("Reports To", "reports_to"),
        FieldSpec("Status", "status", "combo", "Open", ["Open", "Filled", "Frozen", "Closed"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("position_code", "Code", width=110),
        ColumnSpec("position_title", "Title", width=200),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("location", "Location", width=140),
        ColumnSpec("headcount_max", "Max HC", width=80),
        ColumnSpec("headcount_current", "Current HC", width=90),
        ColumnSpec("reports_to", "Reports To", width=140),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = [
        "position_code", "position_title", "department", "location",
        "headcount_max", "headcount_current", "reports_to", "status",
        "created_by", "created_at",
    ]
    update = [
        "position_code", "position_title", "department", "location",
        "headcount_max", "headcount_current", "reports_to", "status",
    ]
    return TableSpec("SF Positions", "sf_positions", cols, fields, insert, update, permission="successfactors")


class SuccessFactorsModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("SAP SuccessFactors")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        tabs = QTabWidget()
        self.sf_dashboard = SFDashboardPage(main)
        self.employee_central = SFEmployeeCentralPage(main, _sf_employee_spec())
        self.recruiting = SFRecruitingPage(main, _sf_recruiting_spec())
        self.performance = SFPerformancePage(main, _sf_performance_spec())
        self.must_win_battles = SFMustWinBattlesPage(main, _sf_must_win_battles_spec())
        self.kpis = SFKPIsPage(main, _sf_kpis_spec())
        self.learning = SFLearningPage(main, _sf_learning_spec())
        self.compensation = SFCompensationPage(main, _sf_compensation_spec())
        self.onboarding = SFOnboardingPage(main, _sf_onboarding_spec())
        self.positions = SFPositionsPage(main, _sf_positions_spec())

        tabs.addTab(self.sf_dashboard, "Overview")
        tabs.addTab(self.employee_central, "Employee Central")
        tabs.addTab(self.recruiting, "Recruiting")
        tabs.addTab(self.performance, "Performance & Goals")
        tabs.addTab(self.must_win_battles, "Must Win Battles")
        tabs.addTab(self.kpis, "KPIs")
        tabs.addTab(self.learning, "Learning (LMS)")
        tabs.addTab(self.compensation, "Compensation")
        tabs.addTab(self.onboarding, "Onboarding")
        tabs.addTab(self.positions, "Positions")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.sf_dashboard.refresh()
        self.employee_central.refresh()
        self.recruiting.refresh()
        self.performance.refresh()
        self.must_win_battles.refresh()
        self.kpis.refresh()
        self.learning.refresh()
        self.compensation.refresh()
        self.onboarding.refresh()
        self.positions.refresh()


# Workflow Engine module

def _wf_workflows_spec() -> TableSpec:
    fields = [
        FieldSpec("Workflow Name *", "workflow_name", required=True),
        FieldSpec("Type", "workflow_type", "combo_other", options=["Approval", "Notification", "Automation", "Escalation", "Onboarding", "Custom"]),
        FieldSpec("Trigger Event", "trigger_event", "combo_other", options=["Manual", "Record Create", "Record Edit", "Record Delete", "Status Change", "Scheduled", "API Call"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Draft", "Paused", "Archived"]),
        FieldSpec("Version", "version", numeric=True),
        FieldSpec("Description", "description", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Name", width=220),
        ColumnSpec("workflow_type", "Type", width=130),
        ColumnSpec("trigger_event", "Trigger", width=150),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("version", "Version", width=70),
        ColumnSpec("description", "Description", width=240),
    ]
    insert = ["workflow_name", "workflow_type", "trigger_event", "status", "version", "description", "created_by", "created_at"]
    update = ["workflow_name", "workflow_type", "trigger_event", "status", "version", "description"]
    return TableSpec("Workflow Definitions", "wf_workflows", cols, fields, insert, update, permission="workflow")


def _wf_steps_spec() -> TableSpec:
    fields = [
        FieldSpec("Workflow ID", "workflow_id", numeric=True),
        FieldSpec("Step Name *", "step_name", required=True),
        FieldSpec("Step Order", "step_order", numeric=True),
        FieldSpec("Step Type", "step_type", "combo_other", options=["Approval", "Notification", "Auto-Action", "Conditional", "Wait", "End"]),
        FieldSpec("Assignee Role", "assignee_role", "combo_other", options=list(ROLE_PERMISSIONS.keys())),
        FieldSpec("Assignee Name", "assignee_name"),
        FieldSpec("SLA (Hours)", "sla_hours", numeric=True),
        FieldSpec("On Approve", "action_on_approve", "combo_other", options=["Next Step", "Close", "Notify", "Auto-Update", "Escalate"]),
        FieldSpec("On Reject", "action_on_reject", "combo_other", options=["Stop", "Return to Requester", "Notify", "Escalate"]),
        FieldSpec("Conditional", "is_conditional", "combo", "0", ["0", "1"]),
        FieldSpec("Condition Field", "condition_field"),
        FieldSpec("Condition Value", "condition_value"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_id", "WF ID", width=70),
        ColumnSpec("step_order", "Order", width=70),
        ColumnSpec("step_name", "Step", width=200),
        ColumnSpec("step_type", "Type", width=120),
        ColumnSpec("assignee_role", "Role", width=120),
        ColumnSpec("assignee_name", "Assignee", width=140),
        ColumnSpec("sla_hours", "SLA (hrs)", width=80),
        ColumnSpec("action_on_approve", "On Approve", width=120),
        ColumnSpec("action_on_reject", "On Reject", width=120),
    ]
    insert = [
        "workflow_id", "step_order", "step_name", "step_type", "assignee_role",
        "assignee_name", "sla_hours", "action_on_approve", "action_on_reject",
        "is_conditional", "condition_field", "condition_value", "created_by", "created_at",
    ]
    update = [
        "workflow_id", "step_order", "step_name", "step_type", "assignee_role",
        "assignee_name", "sla_hours", "action_on_approve", "action_on_reject",
        "is_conditional", "condition_field", "condition_value",
    ]
    return TableSpec("Workflow Steps", "wf_workflow_steps", cols, fields, insert, update, permission="workflow")


def _wf_instances_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("reference_table", "Source Table", width=140),
        ColumnSpec("reference_id", "Record ID", width=80),
        ColumnSpec("initiated_by", "Started By", width=130),
        ColumnSpec("initiated_at", "Started At", d, 110),
        ColumnSpec("current_step", "Step", width=70),
        ColumnSpec("current_assignee", "Assignee", width=130),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("due_at", "Due", d, 100),
        ColumnSpec("priority", "Priority", width=90),
    ]
    return TableSpec("Running Instances", "wf_instances", cols, [], [], [], permission="workflow")


def _wf_tasks_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Workflow Name", "workflow_name"),
        FieldSpec("Step Name", "step_name"),
        FieldSpec("Assigned To *", "assigned_to", required=True),
        FieldSpec("Assigned At", "assigned_at", "date"),
        FieldSpec("Due Date", "due_at", "date"),
        FieldSpec("Status", "status", "combo", "Pending", ["Pending", "Completed", "Rejected", "Cancelled"]),
        FieldSpec("Priority", "priority", "combo", "Normal", ["Low", "Normal", "High", "Critical"]),
        FieldSpec("Reference Table", "reference_table", "combo_other", options=["rent_requirements", "rent_availability", "sale_requirements", "sale_availability", "sf_employees", "sf_recruiting", "sf_onboarding", "clients"]),
        FieldSpec("Reference ID", "reference_id", numeric=True),
        FieldSpec("Comments", "comments", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("step_name", "Step", width=160),
        ColumnSpec("assigned_to", "Assigned To", width=140),
        ColumnSpec("assigned_at", "Assigned", d, 100),
        ColumnSpec("due_at", "Due", d, 100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("priority", "Priority", width=90),
        ColumnSpec("action_taken", "Action", width=110),
        ColumnSpec("reference_table", "Source", width=130),
    ]
    insert = [
        "instance_id", "workflow_name", "step_name", "assigned_to", "assigned_at",
        "due_at", "priority", "reference_table", "reference_id", "comments", "status",
    ]
    update = [
        "workflow_name", "step_name", "assigned_to", "due_at", "priority",
        "reference_table", "reference_id", "comments", "status", "action_taken", "completed_at",
    ]
    return TableSpec("Tasks", "wf_tasks", cols, fields, insert, update, permission="workflow")


def _wf_approvals_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("approval_type", "Type", width=120),
        ColumnSpec("requested_by", "Requested By", width=130),
        ColumnSpec("requested_at", "Requested At", d, 110),
        ColumnSpec("reviewed_by", "Reviewed By", width=130),
        ColumnSpec("reviewed_at", "Reviewed At", d, 110),
        ColumnSpec("decision", "Decision", width=100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("comments", "Comments", width=200),
    ]
    return TableSpec("Approvals", "wf_approvals", cols, [], [], [], permission="workflow")


def _wf_notifications_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Recipient *", "recipient", required=True),
        FieldSpec("Subject *", "subject", required=True),
        FieldSpec("Body", "body", "text"),
        FieldSpec("Channel", "channel", "combo", "In-App", ["In-App", "Email", "SMS", "WhatsApp"]),
        FieldSpec("Status", "status", "combo", "Unread", ["Unread", "Read", "Sent", "Failed"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("recipient", "Recipient", width=150),
        ColumnSpec("subject", "Subject", width=220),
        ColumnSpec("channel", "Channel", width=100),
        ColumnSpec("sent_at", "Sent At", d, 110),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = ["recipient", "subject", "body", "channel", "status", "created_at"]
    update = ["recipient", "subject", "body", "channel", "status", "read_at"]
    return TableSpec("Notifications", "wf_notifications", cols, fields, insert, update, permission="workflow")


def _wf_sla_spec() -> TableSpec:
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("instance_id", "Instance", width=90),
        ColumnSpec("task_id", "Task", width=80),
        ColumnSpec("sla_target_hours", "SLA Target(h)", width=110),
        ColumnSpec("actual_hours", "Actual (h)", width=100),
        ColumnSpec("breached", "Breached", width=90),
        ColumnSpec("logged_at", "Logged At", None, 110),
    ]
    return TableSpec("SLA Log", "wf_sla_log", cols, [], [], [], permission="workflow")


def _wf_audit_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("action", "Action", width=160),
        ColumnSpec("performed_by", "By", width=130),
        ColumnSpec("performed_at", "At", d, 110),
        ColumnSpec("reference_table", "Table", width=140),
        ColumnSpec("reference_id", "Record ID", width=80),
        ColumnSpec("old_value", "Old Value", width=180),
        ColumnSpec("new_value", "New Value", width=180),
    ]
    return TableSpec("Audit Trail", "wf_audit_log", cols, [], [], [], permission="workflow")


class WFDashboardPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Workflow Overview")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        self.cards_layout = QGridLayout()
        layout.addLayout(self.cards_layout)
        layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def count(table: str, where: str = "") -> int:
            sql = f"SELECT COUNT(*) AS c FROM {table}"
            if where:
                sql += f" WHERE {where}"
            row = self.main.services.fetch_one(sql)
            return int(row["c"]) if row else 0

        metrics = [
            ("Workflows Defined", count("wf_workflows", "status='Active'"), "blue"),
            ("Running Instances", count("wf_instances", "status='Running'"), "cyan"),
            ("Pending Tasks", count("wf_tasks", "status='Pending'"), "royal"),
            ("Pending Approvals", count("wf_approvals", "status='Pending'"), "green"),
            ("SLA Breaches", count("wf_sla_log", "breached=1"), "slate"),
            ("Unread Notifs", count("wf_notifications", "status='Unread'"), "sky"),
        ]
        for index, (label, value, tone) in enumerate(metrics):
            tile = self.main._dashboard_tile(label, value, tone)
            self.cards_layout.addWidget(tile, index // 3, index % 3)
            self.cards_layout.setColumnStretch(index % 3, 1)


class WorkflowModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Workflow Engine")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        tabs = QTabWidget()
        self.wf_dashboard = WFDashboardPage(main)
        self.workflows = DataTablePage(main, _wf_workflows_spec())
        self.steps = DataTablePage(main, _wf_steps_spec())
        self.instances = DataTablePage(main, _wf_instances_spec())
        self.tasks = DataTablePage(main, _wf_tasks_spec())
        self.approvals = DataTablePage(main, _wf_approvals_spec())
        self.notifications = DataTablePage(main, _wf_notifications_spec())
        self.sla_log = DataTablePage(main, _wf_sla_spec())
        self.audit_log = DataTablePage(main, _wf_audit_spec())

        tabs.addTab(self.wf_dashboard, "Overview")
        tabs.addTab(self.workflows, "Workflow Definitions")
        tabs.addTab(self.steps, "Workflow Steps")
        tabs.addTab(self.instances, "Running Instances")
        tabs.addTab(self.tasks, "Tasks")
        tabs.addTab(self.approvals, "Approvals")
        tabs.addTab(self.notifications, "Notifications")
        tabs.addTab(self.sla_log, "SLA Log")
        tabs.addTab(self.audit_log, "Audit Trail")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        for page in (
            self.wf_dashboard,
            self.workflows,
            self.steps,
            self.instances,
            self.tasks,
            self.approvals,
            self.notifications,
            self.sla_log,
            self.audit_log,
        ):
            if hasattr(page, "refresh"):
                page.refresh()


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
        self.theme_name = self.services.settings_get("phase1_theme", "Light")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_APP_STYLE if self.theme_name == "Dark" else APP_STYLE)
        self.report_service = ReportService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)

    def reload_dynamic_specs(self) -> None:
        self._build_specs()

        phase_page = self.pages.get("phase1")
        if isinstance(phase_page, PhaseOneDesk):
            phase_page.reload_specs()

        rent_page = self.pages.get("rent")
        if isinstance(rent_page, DealModule):
            rent_page.requirement_spec = self.specs["rent_req"]
            rent_page.availability_spec = self.specs["rent_av"]
            rent_page.closed_spec = self.specs["rented"]
            rent_page.requirements.spec = self.specs["rent_req"]
            rent_page.availability.spec = self.specs["rent_av"]
            if rent_page.closed:
                rent_page.closed.spec = self.specs["rented"]

        sale_page = self.pages.get("sale")
        if isinstance(sale_page, DealModule):
            sale_page.requirement_spec = self.specs["sale_req"]
            sale_page.availability_spec = self.specs["sale_av"]
            sale_page.closed_spec = self.specs["sold"]
            sale_page.requirements.spec = self.specs["sale_req"]
            sale_page.availability.spec = self.specs["sale_av"]
            if sale_page.closed:
                sale_page.closed.spec = self.specs["sold"]

        financials = self.pages.get("financials")
        if isinstance(financials, FinancialModule):
            financials.income.spec = self.specs["income"]
            financials.expenses.spec = self.specs["expenses"]

    def _build_specs(self) -> None:
        m = lambda value, symbol: money(value, symbol)
        d = lambda value, _symbol: format_date_display(value)
        option_sets = {
            "areas": setting_lines(self.services, "phase1_areas", COMMON_AREAS),
            "facilities": setting_lines(self.services, "phase1_facilities", FACILITY_OPTIONS),
            "floors": setting_lines(self.services, "phase1_floors", FLOOR_OPTIONS),
            "property_types": setting_lines(self.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS),
            "measurement_units": setting_lines(self.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS),
        }
        self.specs = {
            "rent_req": TableSpec(
                "Rent Requirements",
                "rent_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Required/Needed", width=180),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget", option_sets),
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
                    ColumnSpec("status", "Availability", width=120),
                    ColumnSpec("property_availability", "Property Available", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("monthly_rent", "Rent", m, 115), ColumnSpec("deposit", "Deposit", m, 115),
                    ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "monthly_rent", option_sets),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                owner_broker_availability_update_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                deal_table=True,
            ),
            "rented": TableSpec(
                "Rented Properties",
                "rented_properties",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("closed_at", "Rented Date", d, 110),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Rented", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("monthly_rent", "Rent", m, 115), ColumnSpec("deposit", "Deposit", m, 115),
                    ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("building_name", "Building Name", width=160),
                    ColumnSpec("closed_status", "Status", width=110), ColumnSpec("archived_by", "Archived By", width=120),
                    ColumnSpec("source_id", "Source ID", width=90),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                [],
                [],
                [],
                permission="rent",
                order_by="closed_at DESC, id DESC",
            ),
            "sale_req": TableSpec(
                "Sale Requirements",
                "sale_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Required/Needed", width=180),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget", option_sets),
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
                    ColumnSpec("status", "Availability", width=120),
                    ColumnSpec("property_availability", "Property Available", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("demand", "Demand", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "demand", option_sets),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "demand"),
                owner_broker_availability_update_columns("owner_name", "property_availability", "demand"),
                permission="sale",
                deal_table=True,
            ),
            "sold": TableSpec(
                "Sold Properties",
                "sold_properties",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("closed_at", "Sold Date", d, 110),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Sold", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("demand", "Demand", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                    ColumnSpec("floor", "Floor", width=90), ColumnSpec("location", "Location", width=150),
                    ColumnSpec("building_name", "Building Name", width=160),
                    ColumnSpec("closed_status", "Status", width=110), ColumnSpec("archived_by", "Archived By", width=120),
                    ColumnSpec("source_id", "Source ID", width=90),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                [],
                [],
                [],
                permission="sale",
                order_by="closed_at DESC, id DESC",
            ),
            "properties": property_spec(),
            "clients": client_spec(),
            "broker_contacts": broker_contact_spec(),
            "income": income_spec(),
            "expenses": expense_spec(self.services.expense_categories()),
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
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 12, 12, 12)
        side.setSpacing(10)

        brand_card = QFrame()
        brand_card.setObjectName("BrandCard")
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(10, 10, 10, 10)
        brand_layout.setSpacing(8)
        logo = QLabel()
        logo.setObjectName("LogoImage")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(44, 44)
        logo_pixmap = QPixmap(str(crm_logo_path()))
        if logo_pixmap.isNull():
            logo.setObjectName("LogoBadge")
            logo.setText("RE")
        else:
            logo.setPixmap(
                logo_pixmap.scaled(
                    44,
                    44,
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
        content_layout.setContentsMargins(18, 12, 18, 14)
        content_layout.setSpacing(10)

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

        def add_separator_if_needed(menu: Any) -> None:
            if not menu.isEmpty():
                menu.addSeparator()

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

        def new_submenu(label: str) -> Any:
            submenu = new_menu.addMenu(label)
            self._menus.append(submenu)
            return submenu

        rent_new_menu = new_submenu("Rent")
        add_deal_action(rent_new_menu, "Requirement", "rent", "requirements", "Ctrl+N")
        add_deal_action(rent_new_menu, "Availability", "rent", "availability", "Ctrl+Shift+N")
        sale_new_menu = new_submenu("Sale")
        add_deal_action(sale_new_menu, "Requirement", "sale", "requirements", "Ctrl+Alt+N")
        add_deal_action(sale_new_menu, "Availability", "sale", "availability", "Ctrl+Alt+A")
        records_new_menu = new_submenu("Records")
        add_record_action(records_new_menu, "Property", "properties", "Ctrl+Shift+P")
        add_record_action(records_new_menu, "Client", "clients", "Ctrl+Shift+C")
        add_record_action(records_new_menu, "Broker Contact", "broker_contacts", None)
        for submenu in (rent_new_menu, sale_new_menu, records_new_menu):
            if submenu.isEmpty():
                new_menu.removeAction(submenu.menuAction())
        if new_menu.isEmpty():
            file_menu.removeAction(new_menu.menuAction())
        add_separator_if_needed(file_menu)
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

        records_menu = menu("Records")
        for group in (("properties", "clients", "broker_contacts"), ("financials", "employees"), ("users", "settings")):
            available = [key for key in group if key in self.nav_buttons]
            if not available:
                continue
            add_separator_if_needed(records_menu)
            for key in available:
                add_page_action(records_menu, key)
        if records_menu.isEmpty():
            empty = QAction("No record pages available", self)
            empty.setEnabled(False)
            records_menu.addAction(empty)

        reports_menu = menu("Reports")
        reports_menu.addAction(action("Rent Report", lambda: self.preview_named_report("rent"), "Ctrl+Shift+1", "Preview rent report"))
        reports_menu.addAction(action("Sale Report", lambda: self.preview_named_report("sale"), "Ctrl+Shift+2", "Preview sale report"))
        reports_menu.addAction(action("Combined Report", lambda: self.preview_named_report("both"), "Ctrl+Shift+3", "Preview combined report"))
        add_separator_if_needed(reports_menu)
        for report_key, label in (
            ("properties", "Property Report"),
            ("clients", "Client Report"),
        ):
            reports_menu.addAction(action(label, lambda key=report_key: self.preview_named_report(key), None, f"Preview {label.lower()}"))
        operations_report_added = False
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            if not operations_report_added:
                add_separator_if_needed(reports_menu)
                operations_report_added = True
            reports_menu.addAction(action("Financial Summary", lambda: self.preview_named_report("financial"), "Ctrl+Shift+4", "Preview financial summary"))
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            if not operations_report_added:
                add_separator_if_needed(reports_menu)
                operations_report_added = True
            reports_menu.addAction(action("Employee Report", lambda: self.preview_named_report("employees"), None, "Preview employee report"))
            reports_menu.addAction(action("Attendance Report", lambda: self.preview_named_report("attendance"), None, "Preview attendance report"))

        if "successfactors" in self.nav_buttons:
            sf_menu = menu("SuccessFactors")
            add_page_action(sf_menu, "successfactors")
            sf_menu.addSeparator()
            for label, tab_hint in [
                ("Employee Central", "Employee Central"),
                ("Recruiting", "Recruiting"),
                ("Performance", "Performance & Goals"),
                ("Must Win Battles", "Must Win Battles"),
                ("KPIs", "KPIs"),
                ("Learning (LMS)", "Learning (LMS)"),
                ("Compensation", "Compensation"),
                ("Onboarding", "Onboarding"),
                ("Positions", "Positions"),
            ]:
                sf_menu.addAction(
                    action(
                        label,
                        lambda hint=tab_hint: (
                            self.switch_page("successfactors"),
                            self.update_status_bar(f"SuccessFactors -> {hint}"),
                        ),
                    )
                )

        if "workflow" in self.nav_buttons:
            wf_menu = menu("Workflow")
            add_page_action(wf_menu, "workflow")
            wf_menu.addSeparator()
            for label in [
                "Workflow Definitions", "Workflow Steps",
                "Running Instances", "Tasks",
                "Approvals", "Notifications", "SLA Log", "Audit Trail",
            ]:
                wf_menu.addAction(
                    action(
                        label,
                        lambda lbl=label: (
                            self.switch_page("workflow"),
                            self.update_status_bar(f"Workflow -> {lbl}"),
                        ),
                    )
                )

        tools_menu = menu("Tools")
        tools_menu.addAction(action("Find", self.open_search, "Ctrl+F", "Find records across rent and sale dealings"))
        tools_menu.addAction(action("Refresh", self.refresh_all_pages, "F5", "Reload CRM data"))
        tools_menu.addSeparator()
        tools_menu.addAction(action("Ecosystem Health", self.show_ecosystem_health, None, "Audit Desktop, Web, database, settings, and backups"))
        tools_menu.addAction(action("Server Health", self.show_api_health, "Ctrl+H", "Show LAN browser server details"))

        help_menu = menu("Help")
        help_menu.addAction(action("User Guide", self.show_user_guide, "F1", "Open the user guide"))
        help_menu.addAction(action("Roles && Permissions", self.show_roles_info, None, "Show role permissions"))
        help_menu.addSeparator()
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
            "clients", "broker_contacts", "properties", "employees", "attendance", "salary_payments",
        }
        if has_permission(self.role, "successfactors") or has_permission(self.role, "sf_view"):
            all_tables.update(SF_TABLES)
        if has_permission(self.role, "workflow") or has_permission(self.role, "wf_view"):
            all_tables.update(WF_TABLES)
        allowed = set(staff_tables if self.is_staff_restricted() else all_tables)
        if self.is_staff_restricted() and (has_permission(self.role, "workflow") or has_permission(self.role, "wf_view")):
            allowed.update({"wf_instances", "wf_tasks", "wf_approvals", "wf_notifications", "wf_sla_log", "wf_audit_log"})
        return allowed

    def api_can_write_table(self, table: str) -> bool:
        if table in READ_ONLY_API_TABLES:
            return False
        if table in PHASE1_TABLES:
            if table.startswith("rent"):
                return has_permission(self.role, "rent")
            if table.startswith("sale"):
                return has_permission(self.role, "sale")
        if table in SF_TABLES:
            return has_permission(self.role, "successfactors")
        if table in WF_TABLES:
            return has_permission(self.role, "workflow")
        permission_map = {
            "income_transactions": "financial",
            "expense_transactions": "financial",
            "clients": "clients",
            "broker_contacts": "clients",
            "properties": "properties",
            "employees": "employees",
            "attendance": "employees",
            "salary_payments": "employees",
        }
        permission = permission_map.get(table)
        return bool(permission and has_permission(self.role, permission))

    def child_reference_summary(self, table: str, row_id: int) -> list[str]:
        references: list[str] = []
        for child_table, child_column in PARENT_CHILD_TABLES.get(table, ()):
            columns = self.services.table_columns(child_table)
            if child_column not in columns:
                continue
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {quote_identifier(child_table)} WHERE {quote_identifier(child_column)}=?",
                (row_id,),
            )
            count = int(row["count"]) if row else 0
            if count:
                references.append(f"{child_table}: {count}")
        return references

    def can_delete_record(self, table: str, row_id: int) -> tuple[bool, str]:
        references = self.child_reference_summary(table, row_id)
        if references:
            return False, "Cannot delete because related records exist: " + "; ".join(references)
        return True, ""

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
                return app.services.repo.table_columns(table)

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

            def _normalize_payload(self, table: str, cleaned: dict) -> tuple[dict, str]:
                number_keys = GLOBAL_SEARCH_MONEY_COLUMNS | {
                    "base_salary", "bonus", "deductions", "net_salary", "maintenance_charge",
                    "deposit", "sale_price", "allowances", "total_compensation", "target_value",
                    "current_value", "actual_value", "progress_pct", "weight_pct",
                    "achievement_pct", "score", "actual_hours",
                }
                date_keys = {
                    key for key in cleaned
                    if is_date_key(key) or key in {"due_at", "assigned_at", "completed_at"}
                }
                try:
                    for key in set(cleaned) & PHONE_FORM_KEYS:
                        cleaned[key] = PhoneValidator.validate_phone(cleaned.get(key))
                    for key in date_keys:
                        if cleaned.get(key) not in (None, ""):
                            cleaned[key] = DateUtils.store_date(cleaned.get(key))
                    for key in set(cleaned) & number_keys:
                        if cleaned.get(key) in (None, ""):
                            cleaned[key] = 0
                            continue
                        number = parse_currency(cleaned.get(key))
                        if number is None:
                            return cleaned, f"{key} must be a number"
                        if number < 0:
                            return cleaned, f"{key} cannot be negative"
                        cleaned[key] = number
                    if table in {"rent_requirements", "sale_requirements"} and "client_status" in cleaned:
                        cleaned["client_status"] = normalize_contact_role(cleaned.get("client_status"), "Client")
                    if table in {"rent_availability", "sale_availability"}:
                        if "client_broker" in cleaned:
                            cleaned["client_broker"] = normalize_contact_role(cleaned.get("client_broker"), "Owner")
                        if "status" in cleaned:
                            cleaned["status"] = normalize_availability_status(cleaned.get("status"), "Available")
                except ValueError as exc:
                    return cleaned, str(exc)
                return cleaned, ""

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
                        "expense_categories": app.services.expense_categories(),
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
                if path in ("/options", "/records/options"):
                    self._send({
                        "ok": True,
                        "expense_categories": app.services.expense_categories(),
                        "tables": {
                            "expense_transactions": {
                                "expense_category": app.services.expense_categories(),
                            },
                        },
                    })
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
                    columns = self._table_columns(table)
                    where_parts: list[str] = []
                    sql_params: list[Any] = []
                    if "is_deleted" in columns:
                        where_parts.append("COALESCE(is_deleted, 0)=0")
                    keyword = (params.get("keyword") or params.get("q") or "").strip()
                    if keyword:
                        searchable = [
                            column for column in sorted(columns)
                            if column not in {"password_hash", "is_deleted", "deleted_by", "deleted_at"}
                        ]
                        if searchable:
                            where_parts.append(
                                "(" + " OR ".join(f"LOWER(CAST(COALESCE({quote_identifier(column)}, '') AS TEXT)) LIKE ?" for column in searchable) + ")"
                            )
                            sql_params.extend([f"%{keyword.lower()}%"] * len(searchable))
                    stage = params.get("stage")
                    if stage and "workflow_stage" in columns:
                        where_parts.append(f"{quote_identifier('workflow_stage')}=?")
                        sql_params.append(stage)
                    status = params.get("status")
                    if status and "status" in columns:
                        where_parts.append(f"{quote_identifier('status')}=?")
                        sql_params.append(status)
                    if table == "broker_contacts":
                        for filter_key in ("area", "office_address", "home_address"):
                            filter_value = (params.get(filter_key) or "").strip()
                            if not filter_value or filter_key not in columns:
                                continue
                            terms = [term.strip().lower() for term in re.split(r"[,;]+", filter_value) if term.strip()]
                            if terms:
                                quoted = quote_identifier(filter_key)
                                where_parts.append(
                                    "(" + " OR ".join(
                                        f"LOWER(CAST(COALESCE({quoted}, '') AS TEXT)) LIKE ?" for _term in terms
                                    ) + ")"
                                )
                                sql_params.extend([f"%{term}%" for term in terms])
                    date_key = next(
                        (
                            key for key in (
                                "date", "transaction_date", "payment_date", "hire_date",
                                "open_date", "close_date", "due_date", "assigned_date",
                                "completion_date", "effective_date", "initiated_at", "assigned_at",
                                "due_at", "completed_at", "requested_at", "reviewed_at",
                                "sent_at", "read_at", "logged_at", "performed_at",
                                "created_at", "last_edited_at",
                            )
                            if key in columns
                        ),
                        None,
                    )
                    start = params.get("start_date") or params.get("date_from")
                    end = params.get("end_date") or params.get("date_to")
                    try:
                        if date_key and start:
                            where_parts.append(f"date({quote_identifier(date_key)}) >= date(?)")
                            sql_params.append(DateUtils.store_date(start))
                        if date_key and end:
                            where_parts.append(f"date({quote_identifier(date_key)}) <= date(?)")
                            sql_params.append(DateUtils.store_date(end))
                    except ValueError as exc:
                        self._send({"ok": False, "error": str(exc)}, 400)
                        return
                    default_sort = "area" if table == "broker_contacts" else "id"
                    default_direction = "asc" if table == "broker_contacts" else "desc"
                    sort_key = (params.get("sort_by") or params.get("sort") or default_sort).strip()
                    if sort_key not in columns:
                        self._send({"ok": False, "error": f"invalid sort_by: {sort_key}"}, 400)
                        return
                    direction = (params.get("sort_order") or params.get("direction") or default_direction).strip().upper()
                    if direction not in {"ASC", "DESC"}:
                        self._send({"ok": False, "error": "invalid sort direction"}, 400)
                        return
                    where_sql = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
                    total_row = app.services.fetch_one(
                        f"SELECT COUNT(*) AS count FROM {quote_identifier(table)}{where_sql}",
                        tuple(sql_params),
                    )
                    order_sql = f" ORDER BY {quote_identifier(sort_key)} {direction}"
                    if sort_key != "id" and "id" in columns:
                        order_sql += f", {quote_identifier('id')} DESC"
                    rows = app.services.fetch_all(
                        f"SELECT * FROM {quote_identifier(table)}{where_sql}{order_sql} LIMIT ? OFFSET ?",
                        tuple(sql_params + [limit, offset]),
                    )
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
                            for column in sorted(app.services.repo.table_columns(table))
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
                                or fields.get("name")
                                or fields.get("full_name")
                                or fields.get("title")
                                or fields.get("property_code")
                                or fields.get("id")
                            )
                            detail = (
                                fields.get("contact")
                                or fields.get("contact_phone")
                                or fields.get("owner_phone")
                                or fields.get("phone")
                                or fields.get("owner_contact")
                                or fields.get("email")
                                or fields.get("location")
                                or fields.get("area")
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
                if not app.api_can_write_table(table):
                    self._send({"ok": False, "error": "write access denied"}, 403)
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
                cleaned, validation_error = self._normalize_payload(table, cleaned)
                if validation_error:
                    self._send({"ok": False, "error": validation_error}, 422)
                    return
                try:
                    if method == "POST":
                        cols = ", ".join(quote_identifier(col) for col in cleaned)
                        placeholders = ", ".join("?" for _ in cleaned)
                        new_id = app.services.insert(f"INSERT INTO {quote_identifier(table)} ({cols}) VALUES ({placeholders})", tuple(cleaned.values()))
                        app.after_record_saved(table, new_id)
                        self._send({"ok": True, "table": table, "id": new_id, "message": "record created"}, 201)
                    else:
                        set_clause = ", ".join(f"{quote_identifier(key)}=?" for key in cleaned)
                        changed = app.services.execute(f"UPDATE {quote_identifier(table)} SET {set_clause} WHERE id=?", tuple(cleaned.values()) + (row_id,))
                        if changed <= 0:
                            self._send({"ok": False, "error": "record not found"}, 404)
                            return
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
                if not app.api_can_write_table(table):
                    self._send({"ok": False, "error": "write access denied"}, 403)
                    return
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok": False, "error": "invalid id"}, 400)
                    return
                try:
                    ok, message = app.can_delete_record(table, row_id)
                    if not ok:
                        self._send({"ok": False, "error": message}, 409)
                        return
                    columns = self._table_columns(table)
                    if "is_deleted" in columns:
                        changed = app.services.execute(
                            f"UPDATE {quote_identifier(table)} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                            (app.current_user.get("username", "api"), datetime.now().isoformat(timespec="seconds"), row_id),
                        )
                    else:
                        changed = app.services.execute(f"DELETE FROM {quote_identifier(table)} WHERE id=?", (row_id,))
                    if changed <= 0:
                        self._send({"ok": False, "error": "record not found"}, 404)
                        return
                    app.log_audit("delete", table, row_id)
                    self._send({"ok": True, "table": table, "id": row_id, "message": "record recycled" if "is_deleted" in columns else "record deleted"})
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
            "phase1": "QT",
            "dashboard": "DB",
            "rent": "RN",
            "sale": "SL",
            "properties": "PR",
            "clients": "CL",
            "broker_contacts": "BC",
            "financials": "FI",
            "employees": "EM",
            "reports": "RP",
            "ai": "AI",
            "users": "US",
            "settings": "ST",
            "successfactors": "SF",
            "workflow": "WF",
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
        self._add_nav_section("QT CRM")
        self._report_startup(69, "Loading QT_CRM data desk")
        self._add_page("phase1", "QT_CRM Desk", PhaseOneDesk(self))
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
                self._add_page("rent", "Rent Dealings", DealModule(self, "Rent Dealings", self.specs["rent_req"], self.specs["rent_av"], self.specs["rented"], "Rented"))
            if "sale" in deal_pages:
                self._report_startup(78, "Loading sale dealings")
                self._add_page("sale", "Sale Dealings", DealModule(self, "Sale Dealings", self.specs["sale_req"], self.specs["sale_av"], self.specs["sold"], "Sold"))
        record_pages = []
        if has_permission(self.role, "properties"):
            record_pages.append("properties")
        if has_permission(self.role, "clients"):
            record_pages.append("clients")
            record_pages.append("broker_contacts")
        if record_pages:
            self._add_nav_section("Records")
            if "properties" in record_pages:
                self._report_startup(82, "Loading property records")
                self._add_page("properties", "Properties", DataTablePage(self, self.specs["properties"]))
            if "clients" in record_pages:
                self._report_startup(84, "Loading client records")
                self._add_page("clients", "Clients", DataTablePage(self, self.specs["clients"]))
            if "broker_contacts" in record_pages:
                self._report_startup(84, "Loading broker contact records")
                self._add_page("broker_contacts", "Broker Contact List", DataTablePage(self, self.specs["broker_contacts"]))
        operation_keys = []
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            operation_keys.append("financials")
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            operation_keys.append("employees")
        if has_permission(self.role, "successfactors") or has_permission(self.role, "sf_view"):
            operation_keys.append("successfactors")
        if has_permission(self.role, "workflow") or has_permission(self.role, "wf_view"):
            operation_keys.append("workflow")
        if has_permission(self.role, "reports"):
            operation_keys.append("reports")
        if operation_keys:
            self._add_nav_section("Operations")
        if "financials" in operation_keys:
            self._report_startup(86, "Loading financials")
            self._add_page("financials", "Financials", FinancialModule(self, self.specs["income"], self.specs["expenses"]))
        if "employees" in operation_keys:
            self._report_startup(87, "Loading employees")
            self._add_page("employees", "Employees", EmployeesModule(self, self.specs["employees"], self.specs["salary"]))
        if "successfactors" in operation_keys:
            self._report_startup(89, "Loading SuccessFactors")
            self._add_page("successfactors", "SuccessFactors", SuccessFactorsModule(self))
        if "workflow" in operation_keys:
            self._report_startup(89, "Loading Workflow Engine")
            self._add_page("workflow", "Workflow Engine", WorkflowModule(self))
        if "reports" in operation_keys:
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
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QFrame()
        body.setObjectName("DashboardReportSurface")
        body.setStyleSheet(
            "#DashboardReportSurface { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop:0 #e2f1ff, stop:0.58 #f4f9ff, stop:1 #d5ebff); "
            "border: 1px solid #bdd6f4; border-radius: 12px; }"
        )
        self.dashboard_layout = QVBoxLayout(body)
        self.dashboard_layout.setContentsMargins(30, 28, 30, 34)
        self.dashboard_layout.setSpacing(18)
        scroll.setWidget(body)
        layout.addWidget(scroll)
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
                "phone": str(row.get("contact_phone") or row.get("contact") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_status"), default_type),
            })
        elif table in {"rent_availability", "sale_availability"}:
            contacts.append({
                "name": str(row.get("owner_name") or "").strip(),
                "phone": str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip(),
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
        owner_contact = str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip()
        floor = str(row.get("floor") or row.get("floor_no") or "").strip()
        if owner_contact and location:
            params: list[Any] = [owner_contact, location]
            where = [
                "owner_contact=?",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            if floor:
                floor_where = where + ["LOWER(COALESCE(floor,''))=LOWER(?)"]
                found = self.services.fetch_one(
                    f"SELECT id FROM properties WHERE {' AND '.join(floor_where)} LIMIT 1",
                    tuple(params + [floor]),
                )
                if found:
                    return found
            found = self.services.fetch_one(
                f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1",
                tuple(params),
            )
            if found:
                return found
        if owner_name and location:
            params = [owner_name, location]
            where = [
                "LOWER(COALESCE(owner_name,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if title and location:
            params = [title, location]
            where = [
                "LOWER(COALESCE(title,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if owner_contact and not location:
            return self.services.fetch_one("SELECT id FROM properties WHERE owner_contact=? LIMIT 1", (owner_contact,))
        return None

    def availability_property_status(self, table: str, row: dict) -> str:
        try:
            status = normalize_availability_status(row.get("status"), "Available")
        except ValueError:
            status = str(row.get("status") or "Available").strip()
        stage = str(row.get("workflow_stage") or "").strip()
        if stage == "Pending" and status == "Available":
            return "Pending"
        if table == "rent_availability" and status == "Sold":
            return "Available"
        if table == "sale_availability" and status == "Rented":
            return "Available"
        return status

    def sync_property_from_availability(self, table: str, row: dict, status: str) -> int | None:
        if table not in {"rent_availability", "sale_availability"}:
            return None
        property_type = str(row.get("property_availability") or row.get("property_type") or "").strip()
        location = str(row.get("location") or "").strip()
        if not property_type and not location:
            return None
        title = f"{property_type or 'Property'} - {location or 'Location'}"
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip()
        area = " ".join(str(row.get(key) or "").strip() for key in ("size", "measurement") if row.get(key)).strip()
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
            "maintenance_charge": maintenance,
            "facilities": row.get("facilities") or "",
            "description": description,
        }
        if table.startswith("rent"):
            fields["monthly_rent"] = safe_float(row.get("monthly_rent"))
        elif table.startswith("sale"):
            fields["sale_price"] = safe_float(row.get("demand") or row.get("asking_price"))
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

    def archive_closed_availability(self, table: str, record_id: int, archived_by: str | None = None) -> bool:
        rule = CLOSED_AVAILABILITY_ARCHIVES.get(table)
        if not rule:
            return False
        closed_status, archive_table, deal_type = rule
        row = self.services.fetch_one(f"SELECT * FROM {quote_identifier(table)} WHERE id=?", (record_id,))
        if not row:
            return False
        try:
            status = normalize_availability_status(row.get("status"), "Available")
        except ValueError:
            status = str(row.get("status") or "").strip()
        if status != closed_status:
            return False
        archive_columns = self.services.table_columns(archive_table)
        source_columns = self.services.table_columns(table)
        if not archive_columns:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        username = archived_by or str(self.current_user.get("username") or "system")
        copy_columns = [
            "date", "owner_name", "owner_phone", "contact_phone", "contact",
            "property_availability", "size", "measurement", "measurement_unit",
            "monthly_rent", "demand", "deposit", "maintenance_charge", "floor",
            "location", "bedrooms", "bathrooms", "furnishing", "parking",
            "nearby_landmarks", "area_notes", "verification_status", "photo_paths",
            "facilities", "client_broker", "bachelor_family", "remarks", "persons",
            "building_name", "workflow_stage", "priority", "assigned_to",
            "deal_probability", "expected_close_value", "approval_status",
            "created_by", "created_at",
        ]
        archive_data: dict[str, Any] = {
            "source_table": table,
            "source_id": record_id,
            "deal_type": deal_type,
            "closed_status": closed_status,
            "closed_at": row.get("closed_at") or now,
            "archived_at": now,
            "archived_by": username,
            "workflow_stage": row.get("workflow_stage") or "Deal Done",
            "deal_probability": row.get("deal_probability") or 100,
            "original_payload": json.dumps(row, default=str, ensure_ascii=True),
        }
        for column in copy_columns:
            if column in archive_columns:
                archive_data.setdefault(column, row.get(column))
        keys = [key for key in archive_data if key in archive_columns]
        existing = self.services.fetch_one(
            f"SELECT id FROM {quote_identifier(archive_table)} WHERE source_table=? AND source_id=?",
            (table, record_id),
        )
        if existing:
            update_keys = [key for key in keys if key not in {"source_table", "source_id"}]
            assignments = ", ".join(f"{quote_identifier(key)}=?" for key in update_keys)
            self.services.execute(
                f"UPDATE {quote_identifier(archive_table)} SET {assignments} WHERE id=?",
                tuple(archive_data[key] for key in update_keys) + (existing["id"],),
            )
        else:
            placeholders = ", ".join("?" for _ in keys)
            self.services.insert(
                f"INSERT INTO {quote_identifier(archive_table)} "
                f"({', '.join(quote_identifier(key) for key in keys)}) VALUES ({placeholders})",
                tuple(archive_data[key] for key in keys),
            )
        updates = []
        params: list[Any] = []
        if "status" in source_columns:
            updates.append("status=?")
            params.append(closed_status)
        if "workflow_stage" in source_columns:
            updates.append("workflow_stage=?")
            params.append("Deal Done")
        if "deal_probability" in source_columns:
            updates.append("deal_probability=?")
            params.append(100)
        if "closed_at" in source_columns:
            updates.append("closed_at=COALESCE(closed_at, ?)")
            params.append(now)
        if "is_deleted" in source_columns:
            updates.append("is_deleted=1")
        if "deleted_by" in source_columns:
            updates.append("deleted_by=?")
            params.append(username)
        if "deleted_at" in source_columns:
            updates.append("deleted_at=?")
            params.append(now)
        if updates:
            params.append(record_id)
            self.services.execute(
                f"UPDATE {quote_identifier(table)} SET {', '.join(updates)} WHERE id=?",
                tuple(params),
            )
        self.log_audit(f"archive_{closed_status.lower()}", table, record_id, new_value=archive_table)
        return True

    def log_audit(
        self,
        action: str,
        reference_table: str,
        reference_id: int | None,
        old_value: str = "",
        new_value: str = "",
    ) -> None:
        self.services.execute(
            """INSERT INTO wf_audit_log
               (action, performed_by, performed_at,
                reference_table, reference_id, old_value, new_value)
               VALUES (?,?,?,?,?,?,?)""",
            (
                action,
                str(self.current_user.get("username") or "system"),
                datetime.now().isoformat(timespec="seconds"),
                reference_table,
                reference_id,
                old_value,
                new_value,
            ),
        )

    def after_record_saved(self, table: str, row_id: int | None) -> None:
        if row_id:
            self.log_audit("save", table, row_id)
        if table not in DEAL_TABLES or not row_id:
            return
        row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not row:
            return
        self.sync_phase1_aliases(table, row)
        row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,)) or row
        self.upsert_client_from_deal(table, row)
        if table in {"rent_availability", "sale_availability"}:
            self.sync_property_from_availability(table, row, self.availability_property_status(table, row))
            self.archive_closed_availability(table, int(row_id))

    def sync_phase1_aliases(self, table: str, row: dict) -> None:
        if table not in DEAL_TABLES or not row.get("id"):
            return
        columns = self.services.table_columns(table)
        updates: dict[str, Any] = {}
        if row.get("date") not in (None, "") and "date" in columns:
            try:
                updates["date"] = DateUtils.store_date(row.get("date"))
            except ValueError:
                pass
        if table in {"rent_requirements", "sale_requirements"}:
            try:
                updates["client_status"] = normalize_contact_role(row.get("client_status"), "Client")
            except ValueError:
                pass
            phone = PhoneValidator.normalize(row.get("contact") or row.get("contact_phone"))
            if phone:
                for key in ("contact", "contact_phone"):
                    if key in columns:
                        updates[key] = phone
            if "contact_person" in columns:
                updates["contact_person"] = row.get("client_name") or row.get("contact_person") or ""
        else:
            try:
                updates["client_broker"] = normalize_contact_role(row.get("client_broker"), "Owner")
            except ValueError:
                pass
            if "status" in columns:
                try:
                    updates["status"] = normalize_availability_status(row.get("status"), "Available")
                except ValueError:
                    pass
            phone = PhoneValidator.normalize(row.get("contact") or row.get("owner_phone") or row.get("contact_phone"))
            if phone:
                for key in ("contact", "owner_phone", "contact_phone"):
                    if key in columns:
                        updates[key] = phone
        if not updates:
            return
        cols = [key for key in updates if key in columns]
        assignments = ", ".join(f"{key}=?" for key in cols)
        self.services.execute(
            f"UPDATE {table} SET {assignments} WHERE id=?",
            tuple(updates[key] for key in cols) + (row["id"],),
        )

    def sync_all_deal_contacts(self) -> int:
        synced = 0
        for table in DEAL_TABLES:
            for row in self.services.fetch_all(f"SELECT * FROM {table} ORDER BY id"):
                self.sync_phase1_aliases(table, row)
                row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row["id"],)) or row
                self.upsert_client_from_deal(table, row)
                if table in {"rent_availability", "sale_availability"}:
                    self.sync_property_from_availability(table, row, self.availability_property_status(table, row))
                    self.archive_closed_availability(table, int(row["id"]))
                synced += 1
        return synced

    def update_deal_workflow_status(self, table: str, record_id: int, status: str) -> tuple[dict, int | None]:
        columns = self.services.table_columns(table)
        now = datetime.now()
        final_status = status in {"Rented", "Sold"}
        stage = "Pending" if status == "Pending" else "Deal Done" if final_status else "Contacted"
        probability = 60.0 if status == "Pending" else 100.0 if final_status else 25.0
        assignments: list[str] = []
        params: list[Any] = []
        if "workflow_stage" in columns:
            assignments.append("workflow_stage=?")
            params.append(stage)
        if "priority" in columns:
            assignments.append("priority=?")
            params.append("High" if status == "Pending" else "Medium")
        if "deal_probability" in columns:
            assignments.append("deal_probability=?")
            params.append(probability)
        if "last_contacted" in columns:
            assignments.append("last_contacted=?")
            params.append(now.strftime(PY_DATE_STORAGE_FORMAT))
        if "status" in columns and (status == "Pending" or final_status):
            assignments.append("status=?")
            params.append(normalize_availability_status(status))
        if final_status and "closed_at" in columns:
            assignments.append("closed_at=COALESCE(closed_at, ?)")
            params.append(now)
        if assignments:
            params.append(record_id)
            self.services.execute(f"UPDATE {table} SET {', '.join(assignments)} WHERE id=?", tuple(params))
        full = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (record_id,)) or {"id": record_id}
        property_id: int | None = None
        if table in {"rent_availability", "sale_availability"}:
            property_id = self.sync_property_from_availability(table, full, self.availability_property_status(table, full))
            self.archive_closed_availability(table, record_id)
        self.upsert_client_from_deal(table, full)
        return full, property_id

    def mark_records_workflow(self, page: DataTablePage, table: str, status: str) -> None:
        if self.role == "Viewer":
            QMessageBox.warning(self, "Access Denied", "Viewer users cannot change workflow status.")
            return
        if status in {"Rented", "Sold"} and table not in {"rent_availability", "sale_availability"}:
            return
        row = page.require_single_row(f"marking as {status.lower()}")
        if not row:
            return
        ask = QMessageBox.question(self, status, f"Mark {table.replace('_', ' ')} #{row['id']} as {status}?")
        if ask != QMessageBox.Yes:
            return
        _full, property_id = self.update_deal_workflow_status(table, int(row["id"]), status)
        page.refresh()
        module = self.pages.get("rent" if table.startswith("rent") else "sale")
        if isinstance(module, DealModule) and module.closed:
            module.closed.refresh()
        self.refresh_dashboard()
        message = f"Record #{row['id']} marked {status}"
        if property_id:
            message += f" and synced to property #{property_id}"
        QMessageBox.information(self, status, message)
        self.update_status_bar(message)

    def mark_availability_closed(self, page: DataTablePage, table: str, status: str) -> None:
        self.mark_records_workflow(page, table, status)

    def refresh_all_pages(self) -> None:
        self.reload_settings()
        self.reload_dynamic_specs()
        if "dashboard" in self.pages:
            self.refresh_dashboard()
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

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _dashboard_active_where(self, table: str) -> str:
        columns = self.services.table_columns(table)
        clauses = []
        if "is_deleted" in columns:
            clauses.append("COALESCE(is_deleted, 0)=0")
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(table)
        if closed_rule and "status" in columns:
            clauses.append(f"LOWER(COALESCE(status,''))<>LOWER('{closed_rule[0]}')")
        return "WHERE " + " AND ".join(clauses) if clauses else ""

    def _dashboard_count(self, table: str) -> int:
        where = self._dashboard_active_where(table)
        row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} {where}")
        return int(row["count"]) if row else 0

    def _dashboard_pending_approvals(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.services.table_columns(table)
            if "approval_status" not in columns:
                continue
            where = self._dashboard_active_where(table)
            connector = " AND " if where else "WHERE "
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {where}{connector}approval_status='Pending'"
            )
            total += int(row["count"]) if row else 0
        if self.services.table_columns("pending_approvals"):
            row = self.services.fetch_one("SELECT COUNT(*) AS count FROM pending_approvals WHERE status='Pending'")
            total += int(row["count"]) if row else 0
        return total

    def _dashboard_location_label(self, value: Any) -> str:
        text = " ".join(str(value or "").strip().split())
        if not text:
            return "Unspecified"
        upper = text.upper()
        if "GIZRI" in upper:
            return "Gizri"
        if "DHA" in upper or "DEFENCE" in upper:
            return "DHA"
        if "CLIFTON" in upper:
            return "Clifton"
        if "PECHS" in upper:
            return "PECHS"
        if "NORTH" in upper and "NAZIM" in upper:
            return "North Nazim"
        if "BAHRIA" in upper:
            return "Bahria"
        return text[:18]

    def _dashboard_location_buckets(self) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        mapping = (
            ("rent_requirements", "rent_requirements"),
            ("rent_availability", "rent_availability"),
            ("sale_requirements", "sale_requirements"),
            ("sale_availability", "sale_availability"),
        )
        for table, key in mapping:
            where = self._dashboard_active_where(table)
            rows = self.services.fetch_all(
                f"SELECT COALESCE(location, '') AS location, COUNT(*) AS total FROM {table} {where} GROUP BY COALESCE(location, '')"
            )
            for row in rows:
                label = self._dashboard_location_label(row.get("location"))
                bucket = buckets.setdefault(label, {
                    "location": label,
                    "rent_requirements": 0,
                    "rent_availability": 0,
                    "sale_requirements": 0,
                    "sale_availability": 0,
                })
                bucket[key] += int(row.get("total") or 0)
        ranked = sorted(
            buckets.values(),
            key=lambda item: item["rent_requirements"] + item["rent_availability"] + item["sale_requirements"] + item["sale_availability"],
            reverse=True,
        )
        return ranked[:6] or [{"location": "No Data", "rent_requirements": 0, "rent_availability": 0}]

    def _dashboard_client_segments(self, total: int) -> list[dict[str, Any]]:
        if total <= 0:
            return [
                {"label": "Active Searchers", "value": 0, "percent": 0, "color": "#1976d2"},
                {"label": "Long-Term Leads", "value": 0, "percent": 0, "color": "#43a047"},
                {"label": "Past Clients", "value": 0, "percent": 0, "color": "#007c91"},
            ]
        active = self.services.fetch_one(
            """SELECT COUNT(*) AS count FROM clients
               WHERE LOWER(COALESCE(status,''))='active'
                 AND LOWER(COALESCE(client_type,'')) IN ('tenant', 'buyer', 'investor')"""
        )
        long_term = self.services.fetch_one(
            """SELECT COUNT(*) AS count FROM clients
               WHERE LOWER(COALESCE(client_type,'')) IN ('owner', 'seller', 'broker')"""
        )
        active_count = int(active["count"]) if active else 0
        long_count = int(long_term["count"]) if long_term else 0
        if active_count + long_count > total:
            long_count = max(total - active_count, 0)
        past_count = max(total - active_count - long_count, 0)
        rows = [
            ("Active Searchers", active_count, "#1976d2"),
            ("Long-Term Leads", long_count, "#43a047"),
            ("Past Clients", past_count, "#007c91"),
        ]
        return [
            {"label": label, "value": value, "percent": round((value / total) * 100), "color": color}
            for label, value, color in rows
        ]

    def _dashboard_closed_count(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.services.table_columns(table)
            clauses = []
            if "workflow_stage" in columns:
                clauses.append("LOWER(COALESCE(workflow_stage,''))='deal done'")
            if "status" in columns:
                clauses.append("LOWER(COALESCE(status,'')) IN ('rented', 'sold')")
            if not clauses:
                continue
            active_where = self._dashboard_active_where(table)
            connector = " AND " if active_where else "WHERE "
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {active_where}{connector}({' OR '.join(clauses)})"
            )
            total += int(row["count"]) if row else 0
        for table in ("rented_properties", "sold_properties"):
            if self.services.table_columns(table):
                row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                total += int(row["count"]) if row else 0
        return total

    def _dashboard_summary_data(self) -> dict[str, Any]:
        data = self.report_service.dashboard_summary(
            generated_by=self.current_user.get("full_name") or self.current_user.get("username") or "CRM User",
            generated_role=self.role,
        )
        clients = int(data.get("clients") or 0)
        operation_colors = {"blue": "#0e82b1", "orange": "#ff9818", "green": "#43a047"}
        return {
            "kpis": [
                ("Rent Requirements", int(data.get("rent_requirements") or 0), "blue"),
                ("Rent Availability", int(data.get("rent_available") or 0), "cyan"),
                ("Sale Requirements", int(data.get("sale_requirements") or 0), "silver"),
                ("Sale Availability", int(data.get("sale_available") or 0), "green"),
                ("Rented Done", int(data.get("rented_done") or 0), "royal"),
                ("Sold Done", int(data.get("sold_done") or 0), "sky"),
                ("Properties", int(data.get("properties") or 0), "royal"),
                ("Clients", clients, "sky"),
                ("Employee", int(data.get("employees") or 0), "slate"),
            ],
            "pending": int(data.get("pending_approvals") or 0),
            "locations": data.get("demand_supply") or [],
            "segments": data.get("client_segments") or [],
            "clients": clients,
            "roadmap": data.get("roadmap") or [],
            "operations": [
                (
                    str(row.get("label") or ""),
                    str(row.get("value") or ""),
                    operation_colors.get(str(row.get("tone") or "blue"), "#0e82b1"),
                )
                for row in data.get("operations", [])
            ],
        }

    def _dashboard_label(self, text: str, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, color: str = "#17345c") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", size, weight))
        label.setStyleSheet(f"color: {color};")
        return label

    def _dashboard_tile(self, title: str, value: Any, tone: str) -> QFrame:
        colors = {
            "blue": ("#1f7ee7", "#0569c9", "#ffffff"),
            "cyan": ("#3cb7f2", "#218bd6", "#ffffff"),
            "silver": ("#cbd5e1", "#a9b5c4", "#0b2b50"),
            "green": ("#2ca84f", "#0d7a38", "#ffffff"),
            "royal": ("#217ae4", "#115fcd", "#ffffff"),
            "sky": ("#55b5e9", "#2d94d3", "#ffffff"),
            "slate": ("#c7d0dc", "#aab5c1", "#0b2b50"),
        }
        top, bottom, text = colors.get(tone, colors["blue"])
        frame = QFrame()
        frame.setMinimumHeight(104)
        frame.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {top}, stop:1 {bottom}); "
            "border-radius: 8px; border: 1px solid #dbeafe; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(6)
        value_label = self._dashboard_label(f"{int(value):,}" if isinstance(value, int) else str(value), 26, QFont.Weight.Black, text)
        title_label = self._dashboard_label(title, 9, QFont.Weight.Black, text)
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return frame

    def _dashboard_panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setStyleSheet(
            "#DashboardPanel { background: #f8fbff; border: 1px solid #b8d1ef; "
            "border-radius: 10px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        heading = self._dashboard_label(title, 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        return panel, layout

    def _dashboard_legend_item(self, text: str, color: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QFrame()
        dot.setFixedSize(18, 12)
        dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
        label = self._dashboard_label(text, 8, QFont.Weight.Bold, "#15457f")
        layout.addWidget(dot)
        layout.addWidget(label)
        return widget

    def _dashboard_approval_card(self, pending: int) -> QFrame:
        frame = QFrame()
        frame.setMinimumHeight(202)
        frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ff9f16, stop:1 #ec7900); "
            "border-radius: 10px; border: 1px solid #ffd08a; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 24)
        value = self._dashboard_label(f"{pending:,}", 38, QFont.Weight.Black, "#ffffff")
        title = self._dashboard_label("Pending Approvals", 17, QFont.Weight.Black, "#ffffff")
        note = self._dashboard_label("Needs Admin Review", 11, QFont.Weight.Bold, "#ffffff")
        layout.addStretch(1)
        layout.addWidget(value)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch(1)
        return frame

    def _dashboard_demand_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._dashboard_panel("Rent Demand vs. Supply")
        layout.addWidget(DashboardBarChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._dashboard_legend_item("Rent Requirements", "#1976d2"))
        legend.addSpacing(20)
        legend.addWidget(self._dashboard_legend_item("Rent Availability", "#21964b"))
        layout.addLayout(legend)
        return panel

    def _dashboard_segments_panel(self, total: int, segments: list[dict[str, Any]], operations: list[tuple[str, str, str]]) -> QFrame:
        panel, layout = self._dashboard_panel("")
        layout.takeAt(0).widget().deleteLater()
        top = QHBoxLayout()
        top.setSpacing(24)
        top.addWidget(DashboardDonut(total, segments), 0, Qt.AlignmentFlag.AlignCenter)
        right = QVBoxLayout()
        heading = self._dashboard_label("Client Segments", 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(heading)
        for row in segments:
            item = QHBoxLayout()
            dot = QFrame()
            dot.setFixedSize(24, 24)
            dot.setStyleSheet(f"background: {row.get('color')}; border-radius: 12px;")
            item.addWidget(dot)
            item.addWidget(self._dashboard_label(str(row.get("label") or ""), 10, QFont.Weight.Normal, "#0f3768"), 1)
            item.addWidget(self._dashboard_label(f"{int(row.get('percent') or 0)}%", 11, QFont.Weight.Black, "#1976d2"))
            right.addLayout(item)
        top.addLayout(right, 1)
        layout.addLayout(top)
        table = QFrame()
        table.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #c7dcf3; border-radius: 8px; }")
        table_layout = QVBoxLayout(table)
        table_layout.setContentsMargins(12, 8, 12, 8)
        table_layout.setSpacing(6)
        for label, value, color in operations:
            row = QHBoxLayout()
            square = QFrame()
            square.setFixedSize(24, 24)
            square.setStyleSheet(f"background: {color}; border-radius: 3px;")
            row.addWidget(square)
            row.addWidget(self._dashboard_label(label, 9, QFont.Weight.Normal, "#163f79"), 1)
            row.addWidget(self._dashboard_label(value, 10, QFont.Weight.Black, "#0f7fe6"))
            table_layout.addLayout(row)
        layout.addWidget(table)
        return panel

    def _dashboard_roadmap_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._dashboard_panel("30 / 90 / 180 Day Roadmap")
        layout.addWidget(DashboardLineChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._dashboard_legend_item("Response Time", "#1976d2"))
        legend.addWidget(self._dashboard_legend_item("Approvals Cleared", "#ef7d00"))
        legend.addWidget(self._dashboard_legend_item("Conversion", "#3b9629"))
        layout.addLayout(legend)
        return panel

    def refresh_dashboard(self) -> None:
        if "dashboard" not in self.pages or not hasattr(self, "dashboard_layout"):
            return
        self._clear_layout(self.dashboard_layout)
        data = self._dashboard_summary_data()

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 0, 18, 4)
        title = self._dashboard_label(f"{self.company_name} Report Summary", 27, QFont.Weight.Black, "#245ca9")
        user_line = f"{self.current_user.get('full_name') or self.current_user.get('username') or 'CRM User'}, {self.role}"
        subtitle = self._dashboard_label(user_line, 13, QFont.Weight.Normal, "#315784")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.dashboard_layout.addWidget(header)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)
        for index, (label, value, tone) in enumerate(data["kpis"]):
            kpi_grid.addWidget(self._dashboard_tile(label, value, tone), 0, index)
            kpi_grid.setColumnStretch(index, 1)
        self.dashboard_layout.addLayout(kpi_grid)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self._dashboard_approval_card(data["pending"]), 3)
        top_row.addWidget(self._dashboard_demand_panel(data["locations"]), 8)
        self.dashboard_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        bottom_row.addWidget(self._dashboard_segments_panel(data["clients"], data["segments"], data["operations"]), 1)
        bottom_row.addWidget(self._dashboard_roadmap_panel(data["roadmap"]), 1)
        self.dashboard_layout.addLayout(bottom_row)
        self.dashboard_layout.addStretch(1)

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
        try:
            return self.intelligence_service.match_report(table, row_id)
        except Exception as exc:
            fallback_header = f"Local AI match unavailable: {exc}\nUsing basic matching fallback.\n\n"
        target = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not target:
            return "No record found."
        if table == "rent_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, monthly_rent AS amount, property_availability AS type
                   FROM rent_availability
                   WHERE COALESCE(is_deleted,0)=0
                     AND LOWER(COALESCE(status,''))<>'rented'
                     AND (LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?))
                   ORDER BY ABS(COALESCE(monthly_rent,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_requires") or "", target.get("budget") or 0),
            )
        elif table == "sale_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, demand AS amount, property_availability AS type
                   FROM sale_availability
                   WHERE COALESCE(is_deleted,0)=0
                     AND LOWER(COALESCE(status,''))<>'sold'
                     AND (LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?))
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
        if kind == "sale":
            result = self.report_service.sale_report()
        elif kind == "both":
            result = self.report_service.dealings_report()
        else:
            result = self.report_service.rent_report()
        self.last_report = result
        self.update_status_bar(f"{result.title} generated")
        ReportPreviewDialog(result, self).exec()

    def preview_named_report(self, kind: str) -> None:
        normalized = kind.strip().lower()
        if normalized in {"rent", "sale", "both", "rent + sale"}:
            self.preview_report("both" if normalized in {"both", "rent + sale"} else normalized)
            return
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
            for key in ("id", "client_name", "owner_name", "name", "full_name", "title", "phone", "contact", "location", "area", "status", "role"):
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
            "income_transactions", "expense_transactions", "employees", "clients", "broker_contacts", "properties",
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
        with sqlite3.connect(DB_PATH, timeout=30) as source, sqlite3.connect(path) as destination:
            source.execute("PRAGMA busy_timeout=30000")
            source.backup(destination, pages=100, sleep=0.001)
        QMessageBox.information(self, "Backup", f"Database backed up to:\n{path}")
        self.update_status_bar("Database backup saved")

    def auto_backup_on_close(self) -> Path | None:
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = BACKUP_DIR / f"auto_close_backup_{stamp}.db"
            with sqlite3.connect(DB_PATH, timeout=30) as source, sqlite3.connect(destination) as backup:
                source.execute("PRAGMA busy_timeout=30000")
                source.backup(backup, pages=100, sleep=0.001)
            backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
            for old_backup in backups[30:]:
                try:
                    old_backup.unlink()
                except OSError:
                    pass
            return destination
        except Exception as exc:
            print(f"Auto backup on close failed: {exc}")
            return None

    def show_ecosystem_health(self) -> None:
        try:
            report = format_ecosystem_report(collect_ecosystem_health(DB_PATH))
        except Exception as exc:
            report = f"QT_CRM ECOSYSTEM HEALTH\n========================\nStatus: Error\n\n{exc}"
        self.show_text_dialog("QT_CRM Ecosystem Health", report, width=860, height=620)

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
            "Dashboard          Yes          Yes     Yes       Yes     Yes",
            "Rent/Sale Deals    Full         Full    Full      Add/Edit View",
            "Find Rent/Sale     Yes          Yes     Yes       Yes     Yes",
            "Properties         Full         Full    Full      No      No",
            "Clients            Full         Full    Full      No      No",
            "Financials         Full         Full    Full      No      No",
            "Employees          Full         Full    Full      View    View",
            "Reports            Yes          Yes     Yes       Yes     Yes",
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
        self.auto_backup_on_close()
        self.stop_browser_server()
        self.stop_local_service()
        super().closeEvent(event)


def deal_common_fields(
    name_key: str,
    property_key: str,
    amount_key: str,
    *,
    name_label: str | None = None,
    option_sets: dict[str, list[str]] | None = None,
) -> list[FieldSpec]:
    option_sets = option_sets or {}
    areas = option_sets.get("areas", COMMON_AREAS)
    facilities = option_sets.get("facilities", FACILITY_OPTIONS)
    floors = option_sets.get("floors", FLOOR_OPTIONS)
    property_types = option_sets.get("property_types", PROPERTY_TYPE_OPTIONS)
    measurement_units = option_sets.get("measurement_units", MEASUREMENT_UNIT_OPTIONS)
    name_label = name_label or ("Name *" if name_key == "client_name" else "Owner Name *")
    property_label = "Property Required / Needed" if "requires" in property_key else "Property Available"
    amount_label = "Budget" if amount_key == "budget" else ("Rent" if amount_key == "monthly_rent" else "Demand")
    return [
        FieldSpec("Date *", "date", "date", required=True),
        FieldSpec(name_label, name_key, required=True),
        FieldSpec("Contact *", "contact", required=True),
        FieldSpec(f"{property_label} *", property_key, "combo", options=property_types, required=True),
        FieldSpec("Rooms *", "size", "combo_other", options=["1 BED", "2 BED", "3 BED", "4 BED", "2-3 BED", "3 BED DD", "Studio", "Shop", "Office"], required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec(f"{amount_label} (Rs.) *", amount_key, numeric=True, required=True),
        FieldSpec("Floor", "floor", "multiselect", options=floors),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
        FieldSpec("Bachelor / Family", "bachelor_family", "combo_other", options=FAMILY_OPTIONS),
        FieldSpec("Remarks", "remarks", "text"),
    ]


def deal_fields(name_key: str, property_key: str, amount_key: str, option_sets: dict[str, list[str]] | None = None) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, option_sets=option_sets)
    fields.insert(2, FieldSpec("Client/Broker/Owner *", "client_status", "combo", "Client", OWNER_BROKER_OPTIONS, required=True))
    return fields


def availability_fields(name_key: str, property_key: str, amount_key: str, option_sets: dict[str, list[str]] | None = None) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, option_sets=option_sets)
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields


def owner_broker_availability_fields(
    name_key: str,
    property_key: str,
    amount_key: str,
    option_sets: dict[str, list[str]] | None = None,
) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, name_label="Name *", option_sets=option_sets)
    fields.insert(2, FieldSpec("Client/Broker/Owner *", "client_broker", "combo", "Owner", OWNER_BROKER_OPTIONS, required=True))
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields


def deal_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def deal_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks",
    ]


def availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks",
    ]


def owner_broker_availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    columns = availability_insert_columns(name_key, property_key, amount_key)
    columns.insert(columns.index("bachelor_family"), "client_broker")
    return columns


def owner_broker_availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    columns = availability_update_columns(name_key, property_key, amount_key)
    columns.insert(columns.index("bachelor_family"), "client_broker")
    return columns


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
        FieldSpec("Floor", "floor", "multiselect", options=FLOOR_OPTIONS),
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


def broker_contact_spec() -> TableSpec:
    fields = [
        FieldSpec("Name *", "name", required=True),
        FieldSpec("Contact *", "contact", required=True),
        FieldSpec("Area", "area", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Office Address", "office_address", "text"),
        FieldSpec("Home Address", "home_address", "text"),
        FieldSpec("Remarks", "remarks", "text"),
    ]
    cols = [
        ColumnSpec("id", "Sr. No", width=80),
        ColumnSpec("name", "Name", width=180),
        ColumnSpec("contact", "Contact", width=140),
        ColumnSpec("area", "Area", width=170),
        ColumnSpec("office_address", "Office Address", width=240),
        ColumnSpec("home_address", "Home Address", width=240),
        ColumnSpec("remarks", "Remarks", width=260),
    ]
    insert = ["name", "contact", "area", "office_address", "home_address", "remarks", "created_at"]
    update = ["name", "contact", "area", "office_address", "home_address", "remarks"]
    return TableSpec(
        "Broker Contact List",
        "broker_contacts",
        cols,
        fields,
        insert,
        update,
        permission="clients",
        order_by="area ASC, name ASC, id DESC",
    )


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


def expense_spec(categories: list[str] | None = None) -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    category_options = categories or list(EXPENSE_CATEGORIES)
    fields = [
        FieldSpec("Date *", "transaction_date", "date", required=True),
        FieldSpec("Category *", "expense_category", "combo", options=category_options, required=True),
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
QMenuBar {
    background: #ffffff;
    color: #102033;
    border-bottom: 1px solid #d9e2ef;
    padding: 5px 12px;
    font-weight: 700;
}
QMenuBar::item {
    background: transparent;
    border-radius: 6px;
    padding: 7px 11px;
}
QMenuBar::item:selected {
    background: #eef6ff;
    color: #1d4ed8;
}
QMenuBar::item:pressed {
    background: #dbeafe;
}
QMenu {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    border-radius: 6px;
    padding: 8px 24px 8px 12px;
}
QMenu::item:selected {
    background: #eef6ff;
    color: #1d4ed8;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 6px 4px;
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
#PhaseCard {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 22px;
    font-weight: 900;
    padding: 18px;
    text-align: left;
}
#PhaseCard:hover {
    background: #eff6ff;
    border-color: #2563eb;
}
#MetricCard, #Panel {
    background: white;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#SettingsListEditor {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#SettingsListTitle {
    color: #0f172a;
    font-size: 14px;
    font-weight: 900;
}
#SettingsCount {
    background: #e0f2fe;
    color: #075985;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 900;
}
#ReportShell {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 10px;
}
#ReportControls {
    background: #f8fbff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#ReportQuickButton, #ReportQuickButtonActive {
    min-height: 48px;
    font-size: 14px;
    font-weight: 900;
    text-align: left;
}
#ReportQuickButtonActive {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
#ReportQuickButtonActive:hover {
    background: #1d4ed8;
}
#ReportPreview {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
    padding: 0;
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
QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #dbeafe;
}
QListWidget {
    color: #0f172a;
    alternate-background-color: #f8fafc;
    outline: none;
}
QListWidget::item {
    min-height: 24px;
    padding: 5px 7px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
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
    padding: 8px 13px;
    min-height: 20px;
    font-size: 13px;
    font-weight: 750;
}
QPushButton:hover {
    background: #f8fafc;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background: #e2e8f0;
    border-color: #64748b;
}
QPushButton:focus {
    border-color: #2563eb;
}
QPushButton:disabled {
    background: #f1f5f9;
    color: #94a3b8;
    border-color: #d8e1ea;
}
#AccentButton {
    background: #2563eb;
    color: white;
    border: 1px solid #2563eb;
}
#AccentButton:hover { background: #1d4ed8; }
#AccentButton:pressed { background: #1e40af; }
#AccentButton:disabled {
    background: #bfdbfe;
    color: #f8fafc;
    border-color: #bfdbfe;
}
#WarningButton {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #f59e0b;
}
#WarningButton:hover { background: #fde68a; }
#WarningButton:pressed { background: #fcd34d; }
#DangerButton {
    background: #dc2626;
    color: white;
    border: 1px solid #dc2626;
}
#DangerButton:hover { background: #b91c1c; }
#DangerButton:pressed { background: #991b1b; }
#DangerButton:disabled {
    background: #fecaca;
    color: #fff7f7;
    border-color: #fecaca;
}
#FacilitiesBox, #MultiSelectBox {
    background: #f8fafc;
    border: 1px solid #d9e2ef;
    border-radius: 6px;
}
QLabel#FormGroupTitle {
    color: #0f172a;
    background: #eef6ff;
    border: 1px solid #d9e2ef;
    border-radius: 6px;
    padding: 7px 10px;
    font-weight: 900;
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
QCheckBox#MultiSelectCheck {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 8px;
    font-weight: 700;
    spacing: 7px;
}
QCheckBox#MultiSelectCheck:hover {
    background: #eef6ff;
    border-color: #93c5fd;
}
QCheckBox#MultiSelectCheck::indicator {
    width: 15px;
    height: 15px;
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


DARK_APP_STYLE = APP_STYLE + """
QMainWindow, #Content { background: #0f172a; }
QMenuBar {
    background: #0f172a;
    color: #e5e7eb;
    border-bottom-color: #334155;
}
QMenuBar::item:selected {
    background: #1f2937;
    color: #bfdbfe;
}
QMenuBar::item:pressed {
    background: #172554;
}
QMenu {
    background: #111827;
    color: #e5e7eb;
    border-color: #334155;
}
QMenu::item:selected {
    background: #172554;
    color: #bfdbfe;
}
QMenu::separator {
    background: #334155;
}
#PageTitle, #SectionTitle, #TopTitle, QLabel#FormLabel, QLabel#RequiredLabel {
    color: #e5e7eb;
}
QLabel#FormGroupTitle {
    color: #e5e7eb;
    background: #172554;
    border-color: #334155;
}
#Panel, #MetricCard, QTabWidget::pane {
    background: #111827;
    border-color: #334155;
}
#SettingsListEditor {
    background: #111827;
    border-color: #334155;
}
#SettingsListTitle {
    color: #e5e7eb;
}
#SettingsCount {
    background: #172554;
    color: #bfdbfe;
}
#ReportShell, #ReportControls, #ReportPreview {
    background: #111827;
    border-color: #334155;
}
#ReportQuickButton {
    background: #1f2937;
    color: #e5e7eb;
    border-color: #475569;
}
#ReportQuickButtonActive {
    background: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}
QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit {
    background: #111827;
    color: #e5e7eb;
    border-color: #334155;
}
QListWidget {
    alternate-background-color: #0f172a;
}
QListWidget::item:selected {
    background: #1e40af;
    color: #f8fafc;
}
QTableWidget::item { color: #e5e7eb; }
QHeaderView::section {
    background: #1f2937;
    color: #e5e7eb;
    border-bottom-color: #334155;
}
QPushButton {
    background: #1f2937;
    color: #e5e7eb;
    border-color: #475569;
}
QPushButton:hover {
    background: #334155;
    border-color: #64748b;
}
QPushButton:pressed {
    background: #0f172a;
    border-color: #94a3b8;
}
QPushButton:disabled {
    background: #111827;
    color: #64748b;
    border-color: #253044;
}
#AccentButton {
    background: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}
#AccentButton:hover { background: #1d4ed8; }
#AccentButton:pressed { background: #1e40af; }
#WarningButton {
    background: #422006;
    color: #facc15;
    border-color: #854d0e;
}
#WarningButton:hover { background: #713f12; }
#WarningButton:pressed { background: #854d0e; }
#DangerButton {
    background: #991b1b;
    color: #ffffff;
    border-color: #b91c1c;
}
#DangerButton:hover { background: #7f1d1d; }
#DangerButton:pressed { background: #450a0a; }
#PhaseCard {
    background: #111827;
    color: #f8fafc;
    border-color: #334155;
}
#PhaseCard:hover {
    background: #172554;
    border-color: #60a5fa;
}
#MutedText, #SelectionCount, #MetricNote, #MetricTitle {
    color: #cbd5e1;
}
"""


try:
    from qt_crm_premium_style import APP_STYLE as PREMIUM_APP_STYLE, DARK_APP_STYLE as PREMIUM_DARK_APP_STYLE
except Exception as exc:
    print(f"Premium Qt theme unavailable, using built-in theme: {exc}")
else:
    APP_STYLE = PREMIUM_APP_STYLE
    DARK_APP_STYLE = PREMIUM_DARK_APP_STYLE


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
