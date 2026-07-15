"""Startup splash dialog."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QApplication

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



# ─── CRM module imports ───
from CRM.constants import crm_app_icon, crm_logo_path, app_resource_path
from CRM.services import CRMServices
from CRM.utils import validate_form_value, safe_float, parse_facilities, parse_multi_options, normalize_text

