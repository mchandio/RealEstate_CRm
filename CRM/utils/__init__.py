"""CRM Utility functions."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Any
from crm_core import DB_PATH
from crm_core.constants import PHASE1_TABLES, FACILITY_OPTIONS, FACILITY_ALIASES, has_permission
from crm_core.formatters import format_currency, parse_currency
from crm_core.validators import PhoneValidator
from crm_core.date_utils import DateUtils
from CRM.constants import (
    PY_DATE_DISPLAY_FORMAT, PY_DATE_STORAGE_FORMAT,
    DATE_FORM_KEYS, PHONE_FORM_KEYS, EMAIL_FORM_KEYS,
    CNIC_FORM_KEYS, PERCENT_FORM_KEYS,
    GLOBAL_SEARCH_SOURCES, GLOBAL_SEARCH_HIDDEN_COLUMNS,
    GLOBAL_SEARCH_MONEY_COLUMNS, FIND_SOURCE_PERMISSIONS,
    OUTPUT_DIR,
)

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


