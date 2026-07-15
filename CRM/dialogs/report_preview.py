"""Report preview dialog."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget, QSizePolicy
from typing import Any

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


