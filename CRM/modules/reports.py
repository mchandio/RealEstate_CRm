"""Reports module."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame, QLabel, QPushButton, QComboBox, QDateEdit, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QHeaderView, QAbstractItemView, QMessageBox, QFileDialog, QSizePolicy
from typing import Any
from datetime import datetime
from pathlib import Path

# ─── CRM module imports ───
from CRM.utils import safe_float
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import DATE_STORAGE_FORMAT, DATE_DISPLAY_FORMAT, OUTPUT_DIR
from crm_core.reports import ReportResult, export_report_csv, export_report_text
from CRM.modules.employees import print_report_result, save_report_pdf, report_result_html, write_report_pdf

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