"""CRM Constants & Configuration."""
from __future__ import annotations
from PySide6.QtGui import QIcon
from pathlib import Path
import sys
import os
import re
from typing import Any
from crm_core import AI_LIBS_AVAILABLE, APP_ROOT, DB_PATH, OUTPUT_DIR
from crm_core.constants import (
    EXPENSE_CATEGORIES, DEAL_STAGES, DEAL_TABLES, PHASE1_TABLES,
    COMMON_AREAS, FACILITY_OPTIONS, FACILITY_ALIASES, FLOOR_OPTIONS,
    PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, OWNER_BROKER_OPTIONS,
    FAMILY_OPTIONS, CLOSED_AVAILABILITY_ARCHIVES, ROLE_PERMISSIONS,
    has_permission, is_admin_role, VERIFICATION_STATUSES,
    KARACHI_PRICE_BRACKETS, KARACHI_RENT_BRACKETS, KARACHI_AREA_PRICES,
)

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


