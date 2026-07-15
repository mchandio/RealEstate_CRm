"""Report generation helper functions extracted from ModernCRMWindow.

Provides standalone functions for:
- Financial text generation
- Generic table reports
- Attendance reports
- Date range filtering
- Period label formatting
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from crm_core.reports import ReportResult

from CRM.constants import PY_DATE_DISPLAY_FORMAT
from CRM.utils import (
    money,
    format_date_display,
    safe_float,
    parse_py_date,
)


def build_financial_text(
    services: Any,
    company_name: str,
    currency_symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Generate a financial summary text report."""
    income_rows = _rows_in_date_range(services, "income_transactions", "transaction_date", start_date, end_date)
    expense_rows = _rows_in_date_range(services, "expense_transactions", "transaction_date", start_date, end_date)
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
        f"Company: {company_name}",
        f"Period: {_period_label(start_date, end_date)}",
        "=" * 72,
        "",
        "INCOME BY TYPE",
        "-" * 72,
    ]
    if income_by_type:
        for key, bucket in sorted(income_by_type.items()):
            lines.append(f"{key:<35} Qty:{int(bucket['qty']):>4} {money(bucket['total'], currency_symbol):>18}")
    else:
        lines.append("No income records found for this period.")
    lines += ["", f"TOTAL INCOME:   {money(income, currency_symbol)}", "", "EXPENSES BY CATEGORY", "-" * 72]
    if expense_by_category:
        for key, bucket in sorted(expense_by_category.items()):
            lines.append(f"{key:<35} Qty:{int(bucket['qty']):>4} {money(bucket['total'], currency_symbol):>18}")
    else:
        lines.append("No expense records found for this period.")
    margin = (profit / income * 100) if income else 0
    lines += [
        "",
        f"TOTAL EXPENSES: {money(expenses, currency_symbol)}",
        "=" * 72,
        f"NET PROFIT:     {money(profit, currency_symbol)}",
        f"PROFIT MARGIN:  {margin:.1f}%",
        "=" * 72,
    ]
    return "\n".join(lines)


def generic_report(services: Any, table: str, title: str) -> str:
    """Generate a generic text report for a table."""
    rows = services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC")
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


def attendance_report(services: Any) -> str:
    """Generate an attendance report."""
    rows = services.fetch_all(
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


def get_report_for_kind(
    kind: str,
    services: Any,
    report_service: Any,
    company_name: str,
    currency_symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ReportResult:
    """Get a ReportResult for the given report kind."""
    if kind == "rent":
        return report_service.rent_report(start_date, end_date)
    elif kind == "sale":
        return report_service.sale_report(start_date, end_date)
    elif kind in {"rent + sale", "both"}:
        return report_service.dealings_report(start_date, end_date)
    elif kind == "financial":
        return ReportResult(
            "Financial Summary",
            build_financial_text(services, company_name, currency_symbol, start_date, end_date),
            filename_slug="financial_summary",
        )
    elif kind == "properties":
        return ReportResult(
            "Property Report",
            generic_report(services, "properties", "PROPERTY REPORT"),
            filename_slug="property_report",
        )
    elif kind == "clients":
        return ReportResult(
            "Client Report",
            generic_report(services, "clients", "CLIENT REPORT"),
            filename_slug="client_report",
        )
    elif kind == "employees":
        return ReportResult(
            "Employee Report",
            generic_report(services, "employees", "EMPLOYEE REPORT"),
            filename_slug="employee_report",
        )
    else:
        return ReportResult(
            "Attendance Report",
            attendance_report(services),
            filename_slug="attendance_report",
        )


# ── Internal helpers ──────────────────────────────────────────────────


def _rows_in_date_range(
    services: Any,
    table: str,
    date_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Fetch rows from a table filtered by date range."""
    rows = services.fetch_all(f"SELECT * FROM {table} ORDER BY {date_key} DESC, id DESC")
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


def _period_label(start_date: str | None = None, end_date: str | None = None) -> str:
    """Format a human-readable period label."""
    start = format_date_display(start_date) if parse_py_date(start_date) else "Beginning"
    end = format_date_display(end_date) if parse_py_date(end_date) else "Today"
    if start == "Beginning" and end == "Today":
        return "All records"
    return f"{start} to {end}"
