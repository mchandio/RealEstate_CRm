"""AI Insights module."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QTextEdit, QMessageBox, QSizePolicy, QApplication, QFileDialog
from typing import Any
from datetime import datetime
from pathlib import Path

# ─── CRM module imports ───
from CRM.services import CRMServices
from CRM.constants import OUTPUT_DIR
from crm_core import AI_LIBS_AVAILABLE

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