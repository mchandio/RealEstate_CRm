"""Employees management module."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy
from typing import Any

# ─── CRM module imports ───
from CRM.modules.data_table import DataTablePage
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.modules.attendance import AttendancePage
from CRM.modules.salary import SalaryPage

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