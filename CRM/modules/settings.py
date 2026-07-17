"""Settings module."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog, QMessageBox, QSizePolicy
from datetime import datetime
from typing import Any

# ─── CRM module imports ───
from CRM.constants import COMMON_AREAS, FACILITY_OPTIONS, FLOOR_OPTIONS, PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, EXPENSE_CATEGORIES
from CRM.modules.data_table import DataTablePage
from CRM.modules.phase_one import SettingsListEditor
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.utils import setting_lines
from CRM.dialogs.record import RecordDialog

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
        """Save settings with audit logging (Section 23 recommendation)."""
        changes: dict[str, str] = {}
        for key, widget in self.inputs.items():
            old_value = self.main.services.settings_get(key)
            new_value = widget.text().strip()
            if old_value != new_value:
                changes[key] = f"{old_value!r} -> {new_value!r}"
            self.main.services.settings_set(key, new_value)
        old_theme = self.main.services.settings_get("phase1_theme")
        new_theme = self.theme.currentText()
        if old_theme != new_theme:
            changes["phase1_theme"] = f"{old_theme!r} -> {new_theme!r}"
        self.main.services.settings_set("phase1_theme", new_theme)
        for key, widget in self.list_inputs.items():
            old_value = self.main.services.settings_get(key)
            new_value = widget.values_text()
            if old_value != new_value:
                changes[key] = f"list updated ({len(widget.values_text().splitlines())} items)"
            self.main.services.settings_set(key, new_value)
        # Audit log for settings changes (Section 23 - use audit_logs table)
        if changes:
            try:
                self.main.services.execute(
                    """INSERT INTO audit_logs
                       (table_name, record_id, action, username, summary, details, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "app_settings",
                        None,
                        "settings_update",
                        self.main.current_user.get("username", "system"),
                        f"Updated {len(changes)} setting(s)",
                        str(changes),
                        datetime.now().isoformat(),
                    ),
                )
            except Exception:
                pass  # Don't fail save on audit error
        self.main.reload_settings()
        self.main.reload_dynamic_specs()
        self.main.refresh_all_pages()
        QMessageBox.information(self, "Settings", "Settings saved." + (f" ({len(changes)} changes logged)" if changes else ""))

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