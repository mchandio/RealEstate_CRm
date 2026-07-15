"""Login dialog."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QDialogButtonBox, QMessageBox

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



# ─── CRM module imports ───
from CRM.constants import crm_app_icon, crm_logo_path, app_resource_path
from CRM.services import CRMServices
from CRM.utils import validate_form_value, safe_float, parse_facilities, parse_multi_options, normalize_text

