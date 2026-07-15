"""Phase One: Core CRM business module."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QCheckBox, QRadioButton, QPushButton, QTableWidget, QTableWidgetItem, QDialog, QTabWidget, QHeaderView, QAbstractItemView, QDialogButtonBox, QMessageBox, QSizePolicy, QFileDialog, QListWidget, QListWidgetItem
from typing import Any
from datetime import datetime
from dataclasses import dataclass

# ─── CRM module imports ───
from CRM.utils import safe_float, parse_py_date, parse_qdate, safe_int, format_date_display, validate_form_value, parse_facilities, parse_multi_options, setting_lines, setting_lines_text
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import *
from CRM.widgets.table import configure_multi_select_table, configure_table_for_readability, style_workflow_table_item, apply_responsive_table_layout
from CRM.dialogs.record import RecordDialog
from CRM.dialogs.comment import CommentDialog
from CRM.database import ensure_database, ensure_qt_schema
from CRM.utils import *
from CRM.widgets import *
from CRM.dialogs import *

@dataclass
class PhaseOneSectionSpec:
    key: str
    title: str
    table: str
    name_key: str
    amount_key: str | None
    fields: list[FieldSpec]
    columns: list[ColumnSpec]
    match_target: str | None = None


def phase1_section_specs(main: "ModernCRMWindow") -> dict[str, PhaseOneSectionSpec]:
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    areas = setting_lines(main.services, "phase1_areas", COMMON_AREAS)
    facilities = setting_lines(main.services, "phase1_facilities", FACILITY_OPTIONS)
    floors = setting_lines(main.services, "phase1_floors", FLOOR_OPTIONS)
    property_types = setting_lines(main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS)
    measurement_units = setting_lines(main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS)
    meta = [
        ColumnSpec("created_by", "Created By", width=120),
        ColumnSpec("created_at", "Created At", d, 120),
        ColumnSpec("last_edited_by", "Last Edited By", width=130),
        ColumnSpec("last_edited_at", "Last Edited At", d, 130),
    ]
    common_req_tail = [
        FieldSpec("Rooms *", "size", required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
        FieldSpec("Persons", "persons"),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
    ]
    availability_tail = [
        FieldSpec("Rooms *", "size", required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Building Name", "building_name"),
        FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
        FieldSpec("Persons", "persons"),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
    ]
    return {
        "rent_req": PhaseOneSectionSpec(
            "rent_req",
            "Rent Requirement",
            "rent_requirements",
            "client_name",
            "budget",
            [
                FieldSpec("Name *", "client_name", required=True),
                FieldSpec("Status", "client_status", "combo", "Client", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Required / Needed *", "property_requires", "combo", options=property_types, required=True),
                *common_req_tail,
                FieldSpec("Budget", "budget", numeric=True),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("client_name", "Name", width=160), ColumnSpec("client_status", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("property_requires", "Property Required/Needed", width=180),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("location", "Location", width=160), ColumnSpec("budget", "Budget", m, 120),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170),
                ColumnSpec("persons", "Persons", width=90), ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
            "rent_av",
        ),
        "rent_av": PhaseOneSectionSpec(
            "rent_av",
            "Rent Availability",
            "rent_availability",
            "owner_name",
            "monthly_rent",
            [
                FieldSpec("Name *", "owner_name", required=True),
                FieldSpec("Status", "client_broker", "combo", "Owner", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Available *", "property_availability", "combo", options=property_types, required=True),
                *availability_tail,
                FieldSpec("Rent *", "monthly_rent", numeric=True, required=True),
                FieldSpec("Advance", "deposit", numeric=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("owner_name", "Name", width=160), ColumnSpec("client_broker", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("status", "Availability", width=120),
                ColumnSpec("property_availability", "Property Available", width=170),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("monthly_rent", "Rent", m, 120), ColumnSpec("deposit", "Advance", m, 120),
                ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("location", "Location", width=150),
                ColumnSpec("building_name", "Building Name", width=160),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170),
                ColumnSpec("persons", "Persons", width=90), ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
        ),
        "sale_req": PhaseOneSectionSpec(
            "sale_req",
            "Sale Requirement",
            "sale_requirements",
            "client_name",
            "budget",
            [
                FieldSpec("Name *", "client_name", required=True),
                FieldSpec("Status", "client_status", "combo", "Client", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Required / Needed *", "property_requires", "combo", options=property_types, required=True),
                FieldSpec("Rooms *", "size", required=True),
                FieldSpec("Measurement", "measurement", numeric=True),
                FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
                FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
                FieldSpec("Budget *", "budget", numeric=True, required=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
                FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
                FieldSpec("Family / Bachelor / Other", "bachelor_family", "combo", "Family", FAMILY_OPTIONS),
                FieldSpec("Facilities", "facilities", "facilities", options=facilities),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("client_name", "Name", width=160), ColumnSpec("client_status", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("property_requires", "Property Required/Needed", width=180),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("budget", "Budget", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                ColumnSpec("location", "Location", width=160),
                ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("bachelor_family", "Family/Bachelor/Other", width=170), ColumnSpec("facilities", "Facilities", width=240),
                *meta,
            ],
            "sale_av",
        ),
        "sale_av": PhaseOneSectionSpec(
            "sale_av",
            "Sale Availability",
            "sale_availability",
            "owner_name",
            "demand",
            [
                FieldSpec("Name *", "owner_name", required=True),
                FieldSpec("Status", "client_broker", "combo", "Owner", ["Client", "Broker", "Owner"]),
                FieldSpec("Contact *", "contact", required=True),
                FieldSpec("Date *", "date", "date", required=True),
                FieldSpec("Property Available *", "property_availability", "combo", options=property_types, required=True),
                FieldSpec("Rooms *", "size", required=True),
                FieldSpec("Measurement", "measurement", numeric=True),
                FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
                FieldSpec("Floor *", "floor", "multiselect", options=floors, required=True),
                FieldSpec("Demand *", "demand", numeric=True, required=True),
                FieldSpec("Maintenance", "maintenance_charge", numeric=True),
                FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
                FieldSpec("Building Name", "building_name"),
                FieldSpec("Facilities", "facilities", "facilities", options=facilities),
            ],
            [
                ColumnSpec("id", "Serial No.", width=90), ColumnSpec("date", "Date", d, 100),
                ColumnSpec("owner_name", "Name", width=160), ColumnSpec("client_broker", "Status", width=100),
                ColumnSpec("contact", "Contact", width=130),
                ColumnSpec("status", "Availability", width=120),
                ColumnSpec("property_availability", "Property Available", width=170),
                ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                ColumnSpec("measurement_unit", "Size", width=90), ColumnSpec("floor", "Floor", width=95),
                ColumnSpec("demand", "Demand", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                ColumnSpec("location", "Location", width=160), ColumnSpec("building_name", "Building Name", width=170),
                ColumnSpec("workflow_stage", "Workflow", width=120),
                ColumnSpec("facilities", "Facilities", width=240), *meta,
            ],
        ),
    }


def phase_one_form_group_title(key: str) -> str:
    if key in {"client_name", "owner_name", "client_status", "client_broker", "contact", "contact_phone", "owner_phone", "date"}:
        return "Contact"
    if key in {"budget", "monthly_rent", "deposit", "demand", "maintenance_charge", "maintenance"}:
        return "Price"
    if key in {"measurement", "measurement_unit"}:
        return "Property"
    if key in {"facilities", "remarks", "notes"}:
        return "Facilities"
    return "Property"


class PhaseOneForm(QWidget):
    saved = Signal(dict)
    cancelled = Signal()

    def __init__(self, spec: PhaseOneSectionSpec, *, mode: str = "add", data: dict | None = None):
        super().__init__()
        self.spec = spec
        self.mode = mode
        self.data = data or {}
        self.widgets: dict[str, QWidget] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel(f"{'Add New' if self.mode == 'add' else 'Edit'} {self.spec.title}")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        back = QPushButton("Exit")
        back.clicked.connect(self.cancelled.emit)
        header.addWidget(back)
        layout.addLayout(header)

        hint = QLabel("Save keeps this form open for fast next entry. Required fields are marked with *.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 14, 0, 14)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        row = 0
        col_group = 0
        current_group = ""
        for field_spec in self.spec.fields:
            group_title = phase_one_form_group_title(field_spec.key)
            if group_title != current_group:
                if col_group:
                    row += 1
                    col_group = 0
                group = QLabel(group_title)
                group.setObjectName("FormGroupTitle")
                grid.addWidget(group, row, 0, 1, 4)
                row += 1
                current_group = group_title
            value = self.data.get(field_spec.key, field_spec.default() if callable(field_spec.default) else field_spec.default)
            widget = self._make_widget(field_spec, value)
            self.widgets[field_spec.key] = widget
            label = QLabel(field_spec.label)
            label.setObjectName("RequiredLabel" if field_spec.required else "FormLabel")
            if field_spec.kind in {"facilities", "multiselect"}:
                if col_group:
                    row += 1
                    col_group = 0
                grid.addWidget(label, row, 0)
                grid.addWidget(widget, row, 1, 1, 3)
                row += 1
                continue
            label_col = 0 if col_group == 0 else 2
            field_col = 1 if col_group == 0 else 3
            grid.addWidget(label, row, label_col)
            grid.addWidget(widget, row, field_col)
            col_group += 1
            if col_group >= 2:
                row += 1
                col_group = 0
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        save = QPushButton("Save")
        save.setObjectName("AccentButton")
        save.clicked.connect(self._save)
        footer.addWidget(save)
        layout.addLayout(footer)

    def _make_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        if spec.kind == "facilities":
            frame = QFrame()
            frame.setObjectName("FacilitiesBox")
            grid = QGridLayout(frame)
            grid.setContentsMargins(8, 8, 8, 8)
            options = spec.options or FACILITY_OPTIONS
            selected = parse_facilities(value, options)
            boxes: list[QRadioButton] = []
            for index, label in enumerate(options):
                checkbox = QRadioButton(label)
                checkbox.setObjectName("FacilityCheck")
                checkbox.setAutoExclusive(False)
                checkbox.setChecked(label in selected)
                grid.addWidget(checkbox, index // 3, index % 3)
                boxes.append(checkbox)
            frame.facility_boxes = boxes
            return frame
        if spec.kind == "multiselect":
            return self._make_multiselect_widget(spec, value)
        if spec.kind in {"combo", "combo_other", "autocomplete"}:
            widget = QComboBox()
            widget.addItems(spec.options)
            widget.setEditable(spec.kind != "combo")
            if value not in (None, ""):
                idx = widget.findText(str(value))
                if idx < 0 and spec.kind != "combo":
                    widget.addItem(str(value))
                    idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setEditText(str(value))
            return widget
        if spec.kind == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
            widget.setDate(parse_qdate(value) if value else QDate.currentDate())
            return widget
        if spec.kind == "text":
            widget = QTextEdit()
            widget.setPlainText("" if value is None else str(value))
            return widget
        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        if spec.numeric:
            widget.setPlaceholderText("0")
        return widget

    def _make_multiselect_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("MultiSelectBox")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = list(spec.options or [])
        selected = parse_multi_options(value, options)
        option_keys = {normalize_text(option) for option in options}
        for label in selected:
            key = normalize_text(label)
            if key and key not in option_keys:
                options.append(label)
                option_keys.add(key)
        boxes: list[QCheckBox] = []
        selected_keys = {normalize_text(label) for label in selected}
        columns = 4
        for index, label in enumerate(options):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("MultiSelectCheck")
            checkbox.setChecked(normalize_text(label) in selected_keys)
            grid.addWidget(checkbox, index // columns, index % columns)
            boxes.append(checkbox)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        frame.multi_boxes = boxes
        return frame

    def raw_value(self, field_spec: FieldSpec) -> str:
        widget = self.widgets[field_spec.key]
        if field_spec.kind == "facilities":
            boxes = getattr(widget, "facility_boxes", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if field_spec.kind == "multiselect":
            boxes = getattr(widget, "multi_boxes", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if isinstance(widget, QTextEdit):
            return widget.toPlainText().strip()
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        if isinstance(widget, QDateEdit):
            return widget.date().toString(DATE_STORAGE_FORMAT)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_spec in self.spec.fields:
            value: Any = self.raw_value(field_spec)
            if field_spec.numeric:
                value = safe_float(value)
            values[field_spec.key] = value
        return values

    def validate(self) -> tuple[bool, str]:
        try:
            for field_spec in self.spec.fields:
                validate_form_value(
                    field_spec.key,
                    field_spec.label,
                    self.raw_value(field_spec),
                    required=field_spec.required,
                    numeric=field_spec.numeric,
                    options=field_spec.options,
                    strict_options=(field_spec.kind == "combo"),
                )
        except ValueError as exc:
            return False, str(exc)
        return True, ""

    def clear_for_next(self) -> None:
        self.data = {}
        for field_spec in self.spec.fields:
            widget = self.widgets[field_spec.key]
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0 if widget.count() else -1)
            elif field_spec.kind == "facilities":
                for box in getattr(widget, "facility_boxes", []):
                    box.setChecked(False)
            elif field_spec.kind == "multiselect":
                for box in getattr(widget, "multi_boxes", []):
                    box.setChecked(False)

    def _save(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Check Fields", message)
            return
        self.saved.emit(self.values())


class MatchResultsDialog(QDialog):
    def __init__(self, main: "ModernCRMWindow", requirement: dict, matches: list[dict], title: str):
        super().__init__(main)
        self.main = main
        self.requirement = requirement
        self.matches = matches
        self.setWindowTitle(title)
        self.resize(1040, 620)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["Score", "Reasons", "Serial", "Name", "Contact", "Rooms", "Floor", "Amount", "Location"])
        self.table.setRowCount(len(matches))
        for row_idx, item in enumerate(matches):
            row = item["row"]
            values = [
                f"{item['score']:.0f}%",
                "; ".join(item["reasons"]),
                str(row.get("id") or ""),
                str(row.get("owner_name") or row.get("client_name") or ""),
                str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or ""),
                str(row.get("size") or ""),
                str(row.get("floor") or ""),
                money(row.get("monthly_rent") or row.get("demand") or 0, main.currency_symbol),
                str(row.get("location") or ""),
            ]
            for col_idx, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, table_item)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        print_btn = QPushButton("Print")
        print_btn.setObjectName("AccentButton")
        print_btn.clicked.connect(self.print_results)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(print_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _html(self) -> str:
        company = html.escape(self.main.company_name)
        user = html.escape(str(self.main.current_user.get("full_name") or self.main.current_user.get("username") or ""))
        logo_path = self.main.services.settings_get("company_logo", str(crm_logo_path()))
        logo_html = f"<img src='{html.escape(logo_path)}' style='height:54px'>" if logo_path and Path(logo_path).exists() else ""
        req_lines = "".join(
            f"<tr><td><b>{html.escape(str(key).replace('_', ' ').title())}</b></td><td>{html.escape(str(value or ''))}</td></tr>"
            for key, value in self.requirement.items()
            if key in {"id", "date", "client_name", "contact", "size", "floor", "location", "budget", "facilities"}
        )
        rows = "".join(
            "<tr>"
            f"<td>{item['score']:.0f}%</td>"
            f"<td>{html.escape('; '.join(item['reasons']))}</td>"
            f"<td>{html.escape(str(item['row'].get('id') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('owner_name') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('owner_phone') or item['row'].get('contact_phone') or item['row'].get('contact') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('size') or ''))}</td>"
            f"<td>{html.escape(str(item['row'].get('floor') or ''))}</td>"
            f"<td>{html.escape(money(item['row'].get('monthly_rent') or item['row'].get('demand') or 0, self.main.currency_symbol))}</td>"
            f"<td>{html.escape(str(item['row'].get('location') or ''))}</td>"
            "</tr>"
            for item in self.matches
        )
        return f"""
        <html><body>
        <table width='100%'><tr><td>{logo_html}</td><td><h2>QT_CRM - {company}</h2>
        <p>Match Sheet | {datetime.now().strftime('%d/%m/%Y %I:%M %p')} | Staff: {user}</p></td></tr></table>
        <h3>Client Requirement</h3><table border='1' cellspacing='0' cellpadding='5'>{req_lines}</table>
        <h3>Matched Properties</h3>
        <table border='1' cellspacing='0' cellpadding='5' width='100%'>
        <tr><th>Score</th><th>Reasons</th><th>Serial</th><th>Name</th><th>Contact</th><th>Rooms</th><th>Floor</th><th>Amount</th><th>Location</th></tr>
        {rows}
        </table>
        </body></html>
        """

    def print_results(self) -> None:
        printer = QPrinter(QPrinter.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.Accepted:
            return
        doc = QTextDocument()
        doc.setHtml(self._html())
        doc.print_(printer)


class ImportPreviewDialog(QDialog):
    def __init__(self, spec: PhaseOneSectionSpec, rows: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.spec = spec
        self.rows = rows
        self.setWindowTitle(f"Import Preview - {spec.title}")
        self.resize(980, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Preview {len(rows)} row(s). Confirm to import."))
        self.table = QTableWidget()
        self.table.setColumnCount(len(spec.fields))
        self.table.setHorizontalHeaderLabels([f.label.replace(" *", "") for f in spec.fields])
        self.table.setRowCount(min(len(rows), 200))
        for row_idx, row in enumerate(rows[:200]):
            for col_idx, field_spec in enumerate(spec.fields):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(field_spec.key, "") or "")))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class PhaseOneSectionPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk", spec: PhaseOneSectionSpec):
        super().__init__()
        self.main = main
        self.desk = desk
        self.services = main.services
        self.spec = spec
        self.rows: list[dict] = []
        self.showing_recycle = False
        self.stack = QStackedWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack, 1)
        self.table_page = QWidget()
        self.stack.addWidget(self.table_page)
        self.form_page: PhaseOneForm | None = None
        self._build_table_page()
        self.refresh()

    def _build_table_page(self) -> None:
        layout = QVBoxLayout(self.table_page)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        title = QLabel(self.spec.title)
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        back = QPushButton("Home")
        back.clicked.connect(self.desk.show_home)
        header.addWidget(back)
        if self.can_change():
            add = QPushButton("Add New")
            add.setObjectName("AccentButton")
            add.clicked.connect(self.show_add_form)
            header.addWidget(add)
            edit = QPushButton("Edit")
            edit.clicked.connect(self.show_edit_form)
            header.addWidget(edit)
            delete = QPushButton("Delete")
            delete.setObjectName("DangerButton")
            delete.clicked.connect(self.delete_selected)
            header.addWidget(delete)
            pending = QPushButton("Mark Pending")
            pending.setObjectName("WarningButton")
            pending.clicked.connect(lambda: self.mark_selected_workflow("Pending"))
            header.addWidget(pending)
            if self.spec.table == "rent_availability":
                rented = QPushButton("Mark Rented")
                rented.setObjectName("AccentButton")
                rented.clicked.connect(lambda: self.mark_selected_workflow("Rented"))
                header.addWidget(rented)
            elif self.spec.table == "sale_availability":
                sold = QPushButton("Mark Sold")
                sold.setObjectName("AccentButton")
                sold.clicked.connect(lambda: self.mark_selected_workflow("Sold"))
                header.addWidget(sold)
        if self.spec.match_target:
            match = QPushButton("Match Selected")
            match.clicked.connect(self.match_selected)
            header.addWidget(match)
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_rows)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_rows)
        template_btn = QPushButton("Template")
        template_btn.clicked.connect(self.save_template)
        header.addWidget(import_btn)
        header.addWidget(export_btn)
        header.addWidget(template_btn)
        if is_admin_role(self.main.role):
            recycle = QPushButton("Recycle Bin")
            recycle.clicked.connect(self.toggle_recycle)
            header.addWidget(recycle)
        layout.addLayout(header)

        selection = QHBoxLayout()
        self.status = QLabel("0 of 0 selected")
        self.status.setObjectName("SelectionCount")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        details = QPushButton("Details")
        details.clicked.connect(self.show_details)
        copy = QPushButton("Copy Selected")
        copy.clicked.connect(self.copy_selected_rows)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        selection.addWidget(self.status)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        selection.addWidget(details)
        selection.addWidget(copy)
        selection.addWidget(refresh)
        layout.addLayout(selection)

        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_status)
        self.table.doubleClicked.connect(self.show_edit_form)
        layout.addWidget(self.table, 1)

    def can_change(self) -> bool:
        return self.main.role != "Viewer"

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in selected_table_row_indexes(self.table, len(self.rows))]

    def selected_row(self) -> dict | None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select a row first.")
            return None
        if len(rows) > 1:
            QMessageBox.information(self, "Select One", "Select only one row.")
            return None
        return rows[0]

    def update_status(self) -> None:
        self.status.setText(f"{len(self.selected_rows())} of {len(self.rows)} selected")

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_status()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_status()

    def show_details(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select a row first.")
            return
        details: list[str] = []
        for row in rows:
            full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
            details.append(f"{self.spec.title} #{row.get('id')}")
            details.append("-" * 72)
            for key, value in full.items():
                display = "-" if value in (None, "") else format_date_display(value) if is_date_key(key) else value
                details.append(f"{key}: {display}")
            details.append("")
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{self.spec.title} Details")
        dialog.resize(720, 520)
        body = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 10))
        text.setPlainText("\n".join(details))
        body.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        body.addWidget(buttons)
        dialog.exec()

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        lines = ["\t".join(col.label for col in self.spec.columns)]
        for row in rows:
            lines.append("\t".join(str(row.get(col.key, "") or "") for col in self.spec.columns))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"{len(rows)} selected row(s) copied to clipboard.")

    def mark_selected_workflow(self, status: str) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select at least one row first.")
            return
        if status in {"Rented", "Sold"} and self.spec.table not in {"rent_availability", "sale_availability"}:
            return
        ask = QMessageBox.question(
            self,
            status,
            f"Mark {len(rows)} {self.spec.title.lower()} record(s) as {status}?",
        )
        if ask != QMessageBox.Yes:
            return
        updated = 0
        for row in rows:
            self.main.update_deal_workflow_status(self.spec.table, int(row["id"]), status)
            updated += 1
        self.refresh()
        self.main.refresh_dashboard()
        message = f"{updated} record(s) marked {status}"
        self.status.setText(message)
        self.main.update_status_bar(message)

    def refresh(self) -> None:
        cols = [col.key for col in self.spec.columns]
        deleted = 1 if self.showing_recycle else 0
        where = ["COALESCE(is_deleted,0)=?"]
        params: list[Any] = [deleted]
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(self.spec.table)
        if closed_rule and not self.showing_recycle and "status" in cols:
            where.append("LOWER(COALESCE(status,''))<>LOWER(?)")
            params.append(closed_rule[0])
        self.rows = self.services.fetch_all(
            f"SELECT {', '.join(cols)} FROM {self.spec.table} WHERE {' AND '.join(where)} ORDER BY id DESC",
            tuple(params),
        )
        display_columns = responsive_table_columns(self.spec.table, self.spec.columns)
        self.table.setColumnCount(len(display_columns))
        self.table.setHorizontalHeaderLabels([col.label for col in display_columns])
        self.table.setRowCount(len(self.rows))
        for row_idx, row in enumerate(self.rows):
            for col_idx, col in enumerate(display_columns):
                value = row.get(col.key)
                text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                item = QTableWidgetItem(text.replace("\n", " "))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                style_workflow_table_item(item, col.key, text)
                if len(text) > 28:
                    item.setToolTip(text)
                self.table.setItem(row_idx, col_idx, item)
        apply_responsive_table_layout(self.table)
        self.update_status()

    def show_add_form(self) -> None:
        self._show_form("add", {})

    def show_edit_form(self) -> None:
        if not self.can_change():
            return
        row = self.selected_row()
        if not row:
            return
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
        self._show_form("edit", full)

    def _show_form(self, mode: str, data: dict) -> None:
        if self.form_page:
            self.stack.removeWidget(self.form_page)
            self.form_page.deleteLater()
        self.form_page = PhaseOneForm(self.spec, mode=mode, data=data)
        self.form_page.saved.connect(lambda values, mode=mode, data=data: self.save_form(mode, data, values))
        self.form_page.cancelled.connect(self.show_table)
        self.stack.addWidget(self.form_page)
        self.stack.setCurrentWidget(self.form_page)

    def show_table(self) -> None:
        self.refresh()
        self.stack.setCurrentWidget(self.table_page)

    def _insert_columns(self) -> list[str]:
        cols = [field.key for field in self.spec.fields]
        for extra in ("contact_person", "contact_phone", "owner_phone"):
            if extra in self.services.table_columns(self.spec.table) and extra not in cols:
                cols.append(extra)
        for extra in ("created_by", "created_at"):
            if extra in self.services.table_columns(self.spec.table):
                cols.append(extra)
        return cols

    def _normalize_values(self, values: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(values)
        columns = self.services.table_columns(self.spec.table)
        if "date" in normalized and normalized.get("date") not in (None, ""):
            normalized["date"] = DateUtils.store_date(normalized.get("date"))
        if self.spec.table in {"rent_requirements", "sale_requirements"}:
            if "client_status" in normalized:
                normalized["client_status"] = normalize_contact_role(normalized.get("client_status"), "Client")
            phone = PhoneValidator.validate_phone(normalized.get("contact") or normalized.get("contact_phone"), required=True)
            if "contact" in columns:
                normalized["contact"] = phone
            if "contact_phone" in columns:
                normalized["contact_phone"] = phone
            if "contact_person" in columns:
                normalized["contact_person"] = normalized.get(self.spec.name_key) or ""
        elif self.spec.table in {"rent_availability", "sale_availability"}:
            if "client_broker" in normalized:
                normalized["client_broker"] = normalize_contact_role(normalized.get("client_broker"), "Owner")
            if "status" in normalized:
                normalized["status"] = normalize_availability_status(normalized.get("status"), "Available")
            phone = PhoneValidator.validate_phone(
                normalized.get("contact") or normalized.get("owner_phone") or normalized.get("contact_phone"),
                required=True,
            )
            if "contact" in columns:
                normalized["contact"] = phone
            if "owner_phone" in columns:
                normalized["owner_phone"] = phone
            if "contact_phone" in columns:
                normalized["contact_phone"] = phone
        return normalized

    def save_form(self, mode: str, data: dict, values: dict) -> None:
        try:
            values = self._normalize_values(values)
        except ValueError as exc:
            QMessageBox.warning(self, "Check Fields", str(exc))
            return
        if mode == "add" and self._duplicate_exists(values):
            ask = QMessageBox.question(self, "Duplicate Warning", "A record with the same Name + Contact exists. Are you sure?")
            if ask != QMessageBox.Yes:
                return
        if mode == "add":
            values["created_by"] = self.main.current_user.get("username", "")
            values["created_at"] = datetime.now().isoformat(timespec="seconds")
            cols = self._insert_columns()
            placeholders = ", ".join("?" for _ in cols)
            new_id = self.services.insert(
                f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(values.get(col) for col in cols),
            )
            self.main.after_record_saved(self.spec.table, new_id)
            self.refresh()
            if self.form_page:
                self.form_page.clear_for_next()
            self.main.update_status_bar(f"{self.spec.title} saved")
            return
        record_id = int(data["id"])
        update_values = {key: values.get(key) for key in values}
        if is_admin_role(self.main.role):
            update_values["last_edited_by"] = self.main.current_user.get("username", "")
            update_values["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            cols = [key for key in update_values if key in self.services.table_columns(self.spec.table)]
            assignments = ", ".join(f"{col}=?" for col in cols)
            self.services.execute(
                f"UPDATE {self.spec.table} SET {assignments} WHERE id=?",
                tuple(update_values.get(col) for col in cols) + (record_id,),
            )
            self.show_table()
            self.main.update_status_bar(f"{self.spec.title} updated")
        else:
            approval_id = self.services.submit_approval(
                "edit",
                self.spec.table,
                record_id,
                update_values,
                str(self.main.current_user.get("username") or ""),
            )
            QMessageBox.information(self, "Pending Approval", f"Edit request #{approval_id} was sent for admin approval.")
            self.show_table()

    def _duplicate_exists(self, values: dict) -> bool:
        name = str(values.get(self.spec.name_key) or "").strip()
        contact = PhoneValidator.normalize(values.get("contact") or values.get("contact_phone") or values.get("owner_phone"))
        if not name and not contact:
            return False
        contact_columns = [
            column
            for column in ("contact", "contact_phone", "owner_phone")
            if column in self.services.table_columns(self.spec.table)
        ]
        if not contact_columns:
            return False
        contact_filter = " OR ".join(f"COALESCE({column},'')=?" for column in contact_columns)
        row = self.services.fetch_one(
            f"""SELECT id FROM {self.spec.table}
                WHERE COALESCE(is_deleted,0)=0
                  AND LOWER(COALESCE({self.spec.name_key},''))=LOWER(?)
                  AND ({contact_filter})
                LIMIT 1""",
            (name, *([contact] * len(contact_columns))),
        )
        return bool(row)

    def delete_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more rows first.")
            return
        if QMessageBox.question(self, "Recycle", f"Move {len(rows)} record(s) to recycle?") != QMessageBox.Yes:
            return
        username = str(self.main.current_user.get("username") or "")
        if is_admin_role(self.main.role):
            for row in rows:
                self.services.execute(
                    f"UPDATE {self.spec.table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                    (username, datetime.now().isoformat(timespec="seconds"), row["id"]),
                )
                self.main.log_audit("delete", self.spec.table, int(row["id"]))
            self.refresh()
            return
        for row in rows:
            self.services.submit_approval("delete", self.spec.table, int(row["id"]), {}, username)
        QMessageBox.information(self, "Pending Approval", "Delete request sent for admin approval.")

    def toggle_recycle(self) -> None:
        self.showing_recycle = not self.showing_recycle
        self.refresh()
        if self.showing_recycle and is_admin_role(self.main.role):
            ask = QMessageBox.question(self, "Recycle Bin", "Recycle Bin is open. Restore selected records now?")
            if ask == QMessageBox.Yes:
                self.restore_selected()

    def restore_selected(self) -> None:
        rows = self.selected_rows()
        if not rows:
            return
        for row in rows:
            self.services.execute(
                f"UPDATE {self.spec.table} SET is_deleted=0, deleted_by=NULL, deleted_at=NULL WHERE id=?",
                (row["id"],),
            )
        self.refresh()

    def match_selected(self) -> None:
        row = self.selected_row()
        if not row or not self.spec.match_target:
            return
        target = self.desk.section_specs[self.spec.match_target]
        full = self.services.fetch_one(f"SELECT * FROM {self.spec.table} WHERE id=?", (row["id"],)) or row
        matches = self.desk.find_matches(full, target)
        MatchResultsDialog(self.main, full, matches, f"{self.spec.title} Matches").exec()

    def export_rows(self) -> None:
        rows = self.selected_rows() or self.rows
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export",
            str(OUTPUT_DIR / f"{self.spec.table}_{datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if not path:
            return
        headers = [col.label for col in self.spec.columns]
        data = [{col.label: row.get(col.key, "") for col in self.spec.columns} for row in rows]
        if path.lower().endswith(".xlsx"):
            try:
                import pandas as pd
                pd.DataFrame(data, columns=headers).to_excel(path, index=False)
            except Exception as exc:
                QMessageBox.warning(self, "Excel Export", f"Excel export needs pandas/openpyxl.\n{exc}")
                return
        else:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
        QMessageBox.information(self, "Exported", f"Saved {len(rows)} row(s).")

    def save_template(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template",
            str(OUTPUT_DIR / f"{self.spec.table}_template.csv"),
            "CSV Files (*.csv);;Excel Files (*.xlsx)",
        )
        if not path:
            return
        headers = [field.label.replace(" *", "") for field in self.spec.fields]
        if path.lower().endswith(".xlsx"):
            try:
                import pandas as pd
                pd.DataFrame(columns=headers).to_excel(path, index=False)
            except Exception as exc:
                QMessageBox.warning(self, "Excel Template", f"Excel templates need pandas/openpyxl.\n{exc}")
                return
        else:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(headers)
        QMessageBox.information(self, "Template", f"Template saved:\n{path}")

    def import_rows(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "Data Files (*.csv *.xlsx *.xls);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls)")
        if not path:
            return
        try:
            rows = self._read_import_file(path)
        except Exception as exc:
            QMessageBox.warning(self, "Import", f"Could not read file:\n{exc}")
            return
        if not rows:
            QMessageBox.information(self, "Import", "No rows found.")
            return
        if ImportPreviewDialog(self.spec, rows, self).exec() != QDialog.Accepted:
            return
        duplicates = sum(1 for row in rows if self._duplicate_exists(row))
        if duplicates:
            ask = QMessageBox.question(self, "Duplicate Rows", f"{duplicates} duplicate row(s) found. Import anyway?")
            if ask != QMessageBox.Yes:
                return
        username = str(self.main.current_user.get("username") or "")
        cols = self._insert_columns()
        imported = 0
        for row in rows:
            try:
                row = self._normalize_values(row)
            except ValueError:
                continue
            row["created_by"] = username
            row["created_at"] = datetime.now().isoformat(timespec="seconds")
            placeholders = ", ".join("?" for _ in cols)
            self.services.insert(
                f"INSERT INTO {self.spec.table} ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(row.get(col) for col in cols),
            )
            imported += 1
        self.refresh()
        QMessageBox.information(self, "Imported", f"Imported {imported} row(s).")

    def _read_import_file(self, path: str) -> list[dict]:
        label_to_key = {field.label.replace(" *", "").strip().lower(): field.key for field in self.spec.fields}
        key_lookup = {field.key.lower(): field.key for field in self.spec.fields}
        if path.lower().endswith(".csv"):
            with open(path, newline="", encoding="utf-8-sig") as handle:
                source_rows = list(csv.DictReader(handle))
        else:
            import pandas as pd
            source_rows = pd.read_excel(path).fillna("").to_dict(orient="records")
        rows: list[dict] = []
        for source in source_rows:
            mapped: dict[str, Any] = {}
            for raw_key, value in source.items():
                key_text = str(raw_key).strip().lower()
                key = label_to_key.get(key_text) or key_lookup.get(key_text.replace(" ", "_"))
                if key:
                    mapped[key] = value
            for spec_field in self.spec.fields:
                mapped.setdefault(spec_field.key, "")
                if spec_field.numeric:
                    mapped[spec_field.key] = safe_float(mapped[spec_field.key])
            if any(str(value).strip() for value in mapped.values()):
                rows.append(mapped)
        return rows


class PhaseOneApprovalsPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk"):
        super().__init__()
        self.main = main
        self.desk = desk
        self.rows: list[dict] = []
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Pending Approvals")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        approve = QPushButton("Approve")
        approve.setObjectName("AccentButton")
        approve.clicked.connect(lambda: self.review(True))
        reject = QPushButton("Reject")
        reject.setObjectName("DangerButton")
        reject.clicked.connect(lambda: self.review(False))
        header.addWidget(refresh)
        header.addWidget(approve)
        header.addWidget(reject)
        layout.addLayout(header)
        self.table = QTableWidget()
        configure_multi_select_table(self.table)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self.rows = self.main.services.pending_approvals()
        headers = ["ID", "Action", "Table", "Record", "Requested By", "Requested At"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.rows))
        for row_idx, row in enumerate(self.rows):
            for col_idx, key in enumerate(["id", "action", "table_name", "record_id", "requested_by", "requested_at"]):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(row.get(key) or "")))
        self.table.horizontalHeader().setStretchLastSection(True)

    def selected(self) -> dict | None:
        indexes = selected_table_row_indexes(self.table, len(self.rows))
        if not indexes:
            QMessageBox.information(self, "Select", "Select a pending approval first.")
            return None
        return self.rows[indexes[0]]

    def review(self, approved: bool) -> None:
        row = self.selected()
        if not row:
            return
        full = self.main.services.fetch_one("SELECT * FROM pending_approvals WHERE id=?", (row["id"],))
        if not full:
            return
        if approved:
            self.apply_approval(full)
        self.main.services.review_approval(int(row["id"]), approved, str(self.main.current_user.get("username") or ""))
        self.refresh()
        self.desk.refresh_sections()

    def apply_approval(self, approval: dict) -> None:
        table = approval["table_name"]
        record_id = approval["record_id"]
        payload = json.loads(approval.get("payload") or "{}")
        username = str(self.main.current_user.get("username") or "")
        if approval["action"] == "edit":
            payload["last_edited_by"] = username
            payload["last_edited_at"] = datetime.now().isoformat(timespec="seconds")
            columns = self.main.services.table_columns(table)
            cols = [key for key in payload if key in columns]
            assignments = ", ".join(f"{col}=?" for col in cols)
            self.main.services.execute(
                f"UPDATE {table} SET {assignments} WHERE id=?",
                tuple(payload.get(col) for col in cols) + (record_id,),
            )
        elif approval["action"] == "delete":
            self.main.services.execute(
                f"UPDATE {table} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                (approval.get("requested_by") or "", datetime.now().isoformat(timespec="seconds"), record_id),
            )
            self.main.log_audit("delete", table, int(record_id))
        elif approval["action"] == "restore":
            self.main.services.execute(
                f"UPDATE {table} SET is_deleted=0, deleted_by=NULL, deleted_at=NULL WHERE id=?",
                (record_id,),
            )


class SettingsListEditor(QWidget):
    def __init__(self, title: str, values: list[str], defaults: list[str]):
        super().__init__()
        self.title = title
        self.defaults = list(defaults)
        self.setObjectName("SettingsListEditor")
        self.setMinimumHeight(126)
        self.setMaximumHeight(148)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        top = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("SettingsListTitle")
        self.count_label = QLabel()
        self.count_label.setObjectName("SettingsCount")
        top.addWidget(label)
        top.addStretch(1)
        top.addWidget(self.count_label)
        layout.addLayout(top)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setMinimumHeight(40)
        self.list_widget.setMaximumHeight(54)
        self.list_widget.itemChanged.connect(lambda _item: self._refresh_count())
        layout.addWidget(self.list_widget, 1)

        entry_row = QHBoxLayout()
        entry_row.setSpacing(6)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(f"Add {title.lower()}")
        self.entry.returnPressed.connect(self.add_item)
        add = QPushButton("Add")
        add.setObjectName("AccentButton")
        add.clicked.connect(self.add_item)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_selected)
        reset = QPushButton("Reset")
        reset.clicked.connect(self.reset_defaults)
        self.entry.setFixedHeight(30)
        for button in (add, remove, reset):
            button.setMinimumWidth(62)
            button.setFixedHeight(30)
        entry_row.addWidget(self.entry, 1)
        entry_row.addWidget(add)
        entry_row.addWidget(remove)
        entry_row.addWidget(reset)
        layout.addLayout(entry_row)

        self.set_values(values)

    def set_values(self, values: list[str]) -> None:
        self.list_widget.clear()
        for value in normalize_setting_lines("\n".join(values), self.defaults):
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)
        self._refresh_count()

    def current_items(self) -> list[str]:
        return [
            self.list_widget.item(index).text().strip()
            for index in range(self.list_widget.count())
            if self.list_widget.item(index).text().strip()
        ]

    def values(self) -> list[str]:
        return normalize_setting_lines("\n".join(self.current_items()), self.defaults)

    def values_text(self) -> str:
        return "\n".join(self.values())

    def add_item(self) -> None:
        text = self.entry.text().strip()
        if not text:
            return
        existing = {self.list_widget.item(index).text().strip().lower() for index in range(self.list_widget.count())}
        if text.lower() not in existing:
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)
        self.entry.clear()
        self._refresh_count()

    def remove_selected(self) -> None:
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self._refresh_count()

    def reset_defaults(self) -> None:
        if QMessageBox.question(self, "Reset List", f"Reset {self.title} to defaults?") == QMessageBox.Yes:
            self.set_values(self.defaults)

    def _refresh_count(self) -> None:
        self.count_label.setText(f"{len(self.current_items())} items")


class PhaseOneSettingsPage(QWidget):
    def __init__(self, main: "ModernCRMWindow", desk: "PhaseOneDesk"):
        super().__init__()
        self.main = main
        self.desk = desk
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        title = QLabel("Phase 1 Settings")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.company = QLineEdit(main.services.settings_get("company_name", main.company_name))
        self.address = QLineEdit(main.services.settings_get("company_address", ""))
        self.phone = QLineEdit(main.services.settings_get("company_phone", ""))
        self.email = QLineEdit(main.services.settings_get("company_email", ""))
        self.logo = QLineEdit(main.services.settings_get("company_logo", str(crm_logo_path())))
        self.currency = QLineEdit(main.services.settings_get("currency_symbol", "Rs."))
        self.default_commission = QLineEdit(main.services.settings_get("default_commission", ""))
        self.tax_rate = QLineEdit(main.services.settings_get("tax_rate", ""))
        self.bank_account = QLineEdit(main.services.settings_get("bank_account", ""))
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        self.areas = SettingsListEditor("Areas", setting_lines(main.services, "phase1_areas", COMMON_AREAS), COMMON_AREAS)
        self.facilities = SettingsListEditor("Facilities", setting_lines(main.services, "phase1_facilities", FACILITY_OPTIONS), FACILITY_OPTIONS)
        self.floors = SettingsListEditor("Floors", setting_lines(main.services, "phase1_floors", FLOOR_OPTIONS), FLOOR_OPTIONS)
        self.property_types = SettingsListEditor("Property Types", setting_lines(main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS), PROPERTY_TYPE_OPTIONS)
        self.measurement_units = SettingsListEditor("Measurement Units", setting_lines(main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS), MEASUREMENT_UNIT_OPTIONS)
        self.expense_categories = SettingsListEditor("Expense Categories", setting_lines(main.services, "expense_categories", list(EXPENSE_CATEGORIES)), list(EXPENSE_CATEGORIES))
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)
        form.addWidget(QLabel("Agency Name"), 0, 0)
        form.addWidget(self.company, 0, 1)
        form.addWidget(QLabel("Company Address"), 1, 0)
        form.addWidget(self.address, 1, 1, 1, 2)
        form.addWidget(QLabel("Company Phone"), 2, 0)
        form.addWidget(self.phone, 2, 1)
        form.addWidget(QLabel("Company Email"), 2, 2)
        form.addWidget(self.email, 2, 3)
        form.addWidget(QLabel("Logo Path"), 3, 0)
        form.addWidget(self.logo, 3, 1, 1, 2)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_logo)
        form.addWidget(browse, 3, 3)
        form.addWidget(QLabel("Currency Symbol"), 4, 0)
        form.addWidget(self.currency, 4, 1)
        form.addWidget(QLabel("Default Commission %"), 4, 2)
        form.addWidget(self.default_commission, 4, 3)
        form.addWidget(QLabel("Tax Rate %"), 5, 0)
        form.addWidget(self.tax_rate, 5, 1)
        form.addWidget(QLabel("Theme"), 5, 2)
        form.addWidget(self.theme, 5, 3)
        form.addWidget(QLabel("Bank Account"), 6, 0)
        form.addWidget(self.bank_account, 6, 1, 1, 3)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        layout.addLayout(form)
        list_grid = QGridLayout()
        list_grid.setHorizontalSpacing(10)
        list_grid.setVerticalSpacing(8)
        for index, editor in enumerate(
            (self.areas, self.facilities, self.floors, self.property_types, self.measurement_units, self.expense_categories)
        ):
            list_grid.addWidget(editor, index // 2, index % 2)
            list_grid.setColumnStretch(index % 2, 1)
        layout.addLayout(list_grid)
        save = QPushButton("Save Settings")
        save.setObjectName("AccentButton")
        save.setFixedHeight(42)
        save.clicked.connect(self.save)
        layout.addWidget(save)

    def browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose Logo", "", "Images (*.png *.jpg *.jpeg *.ico)")
        if path:
            self.logo.setText(path)

    def refresh(self) -> None:
        self.company.setText(self.main.services.settings_get("company_name", self.main.company_name))
        self.address.setText(self.main.services.settings_get("company_address", ""))
        self.phone.setText(self.main.services.settings_get("company_phone", ""))
        self.email.setText(self.main.services.settings_get("company_email", ""))
        self.logo.setText(self.main.services.settings_get("company_logo", str(crm_logo_path())))
        self.currency.setText(self.main.services.settings_get("currency_symbol", "Rs."))
        self.default_commission.setText(self.main.services.settings_get("default_commission", ""))
        self.tax_rate.setText(self.main.services.settings_get("tax_rate", ""))
        self.bank_account.setText(self.main.services.settings_get("bank_account", ""))
        self.theme.setCurrentText(self.main.services.settings_get("phase1_theme", "Light"))
        self.areas.set_values(setting_lines(self.main.services, "phase1_areas", COMMON_AREAS))
        self.facilities.set_values(setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        self.floors.set_values(setting_lines(self.main.services, "phase1_floors", FLOOR_OPTIONS))
        self.property_types.set_values(setting_lines(self.main.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS))
        self.measurement_units.set_values(setting_lines(self.main.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS))
        self.expense_categories.set_values(setting_lines(self.main.services, "expense_categories", list(EXPENSE_CATEGORIES)))

    def save(self) -> None:
        self.main.services.settings_set("company_name", self.company.text().strip())
        self.main.services.settings_set("company_address", self.address.text().strip())
        self.main.services.settings_set("company_phone", self.phone.text().strip())
        self.main.services.settings_set("company_email", self.email.text().strip())
        self.main.services.settings_set("company_logo", self.logo.text().strip())
        self.main.services.settings_set("currency_symbol", self.currency.text().strip())
        self.main.services.settings_set("default_commission", self.default_commission.text().strip())
        self.main.services.settings_set("tax_rate", self.tax_rate.text().strip())
        self.main.services.settings_set("bank_account", self.bank_account.text().strip())
        self.main.services.settings_set("phase1_theme", self.theme.currentText())
        self.main.services.settings_set("phase1_areas", self.areas.values_text())
        self.main.services.settings_set("phase1_facilities", self.facilities.values_text())
        self.main.services.settings_set("phase1_floors", self.floors.values_text())
        self.main.services.settings_set("phase1_property_types", self.property_types.values_text())
        self.main.services.settings_set("phase1_measurement_units", self.measurement_units.values_text())
        self.main.services.settings_set("expense_categories", self.expense_categories.values_text())
        self.main.reload_settings()
        self.main.reload_dynamic_specs()
        self.main.refresh_all_pages()
        QMessageBox.information(self, "Settings", "Settings saved.")


class PhaseOneDesk(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        self.section_specs = phase1_section_specs(main)
        self.section_pages: dict[str, PhaseOneSectionPage] = {}
        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.home = self._home_page()
        self.stack.addWidget(self.home)
        for key, spec in self.section_specs.items():
            page = PhaseOneSectionPage(main, self, spec)
            self.section_pages[key] = page
            self.stack.addWidget(page)
        if is_admin_role(main.role):
            self.approvals = PhaseOneApprovalsPage(main, self)
            self.settings = PhaseOneSettingsPage(main, self)
            self.stack.addWidget(self.approvals)
            self.stack.addWidget(self.settings)
        self.show_home()

    def reload_specs(self) -> None:
        self.section_specs = phase1_section_specs(self.main)
        for key, page in self.section_pages.items():
            if key in self.section_specs:
                page.spec = self.section_specs[key]

    def refresh(self) -> None:
        self.reload_specs()
        self.refresh_sections()
        if hasattr(self, "settings"):
            self.settings.refresh()

    def refresh_sections(self) -> None:
        for page in self.section_pages.values():
            page.refresh()

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("QT_CRM Data Desk")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        cards = [
            ("Rent Requirement", "rent_req"),
            ("Rent Availability", "rent_av"),
            ("Sale Requirement", "sale_req"),
            ("Sale Availability", "sale_av"),
        ]
        for index, (label, key) in enumerate(cards):
            button = QPushButton(label)
            button.setObjectName("PhaseCard")
            button.setMinimumHeight(110)
            button.clicked.connect(lambda _checked=False, k=key: self.open_section(k))
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)

        search_box = QFrame()
        search_box.setObjectName("Panel")
        search_layout = QVBoxLayout(search_box)
        search_title = QLabel("Search")
        search_title.setObjectName("SectionTitle")
        search_layout.addWidget(search_title)
        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Client, broker, owner name, contact, location, rooms, floor, facilities")
        search_btn = QPushButton("Search")
        search_btn.setObjectName("AccentButton")
        search_btn.clicked.connect(self.run_search)
        row.addWidget(self.search_input, 1)
        row.addWidget(search_btn)
        search_layout.addLayout(row)
        self.search_results = QVBoxLayout()
        search_layout.addLayout(self.search_results)
        layout.addWidget(search_box, 1)

        if is_admin_role(self.main.role):
            admin_row = QHBoxLayout()
            approvals = QPushButton("Pending Approvals")
            approvals.clicked.connect(lambda: self.stack.setCurrentWidget(self.approvals))
            settings = QPushButton("Phase 1 Settings")
            settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings))
            admin_row.addWidget(approvals)
            admin_row.addWidget(settings)
            admin_row.addStretch(1)
            layout.addLayout(admin_row)
        return page

    def show_home(self) -> None:
        self.stack.setCurrentWidget(self.home)

    def open_section(self, key: str) -> None:
        page = self.section_pages[key]
        page.refresh()
        self.stack.setCurrentWidget(page)

    def _clear_search_results(self) -> None:
        while self.search_results.count():
            item = self.search_results.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def run_search(self) -> None:
        query = self.search_input.text().strip().lower()
        self._clear_search_results()
        if not query:
            return
        for spec in self.section_specs.values():
            columns = [col.key for col in spec.columns]
            text_fields = [field.key for field in spec.fields if not field.numeric]
            clauses = " OR ".join(f"LOWER(COALESCE({field},'')) LIKE ?" for field in text_fields)
            params = tuple(f"%{query}%" for _ in text_fields)
            rows = self.main.services.fetch_all(
                f"SELECT {', '.join(columns)} FROM {spec.table} WHERE COALESCE(is_deleted,0)=0 AND ({clauses}) ORDER BY id DESC LIMIT 50",
                params,
            )
            label = QLabel(f"{spec.title} ({len(rows)})")
            label.setObjectName("SectionTitle")
            self.search_results.addWidget(label)
            table = QTableWidget()
            table.setMaximumHeight(210)
            table.setColumnCount(min(6, len(spec.columns)))
            table.setHorizontalHeaderLabels([col.label for col in spec.columns[:6]])
            table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                for col_idx, col in enumerate(spec.columns[:6]):
                    value = row.get(col.key)
                    text = col.formatter(value, self.main.currency_symbol) if col.formatter else str(value or "")
                    table.setItem(row_idx, col_idx, QTableWidgetItem(text))
            table.horizontalHeader().setStretchLastSection(True)
            self.search_results.addWidget(table)

    def find_matches(self, requirement: dict, target: PhaseOneSectionSpec) -> list[dict]:
        rows = self.main.services.fetch_all(f"SELECT * FROM {target.table} WHERE COALESCE(is_deleted,0)=0 ORDER BY id DESC")
        scored = []
        for row in rows:
            score, reasons = self._match_score(requirement, row, target)
            if score > 0:
                scored.append({"score": min(score, 100), "reasons": reasons, "row": row})
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:50]

    def _match_score(self, req: dict, row: dict, target: PhaseOneSectionSpec) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        req_location = normalize_text(req.get("location"))
        row_location = normalize_text(row.get("location"))
        if req_location and row_location:
            if req_location == row_location:
                score += 45
                reasons.append("same location")
            elif self._nearby(req_location, row_location):
                score += 35
                reasons.append("nearby/similar location")
            elif req_location in row_location or row_location in req_location:
                score += 25
                reasons.append("similar location text")
        req_amount = safe_float(req.get("budget") or req.get("budget_max"))
        row_amount = safe_float(row.get(target.amount_key or "") if target.amount_key else 0)
        if req_amount and row_amount:
            if row_amount <= req_amount:
                score += 20
                reasons.append("price within budget")
            elif row_amount <= req_amount * 1.1:
                score += 12
                reasons.append("price near budget")
        if normalize_text(req.get("size")) and normalize_text(req.get("size")) == normalize_text(row.get("size")):
            score += 15
            reasons.append("matching rooms")
        if multi_option_overlap(req.get("floor"), row.get("floor"), FLOOR_OPTIONS):
            score += 10
            reasons.append("matching floor")
        req_facilities = parse_facilities(req.get("facilities"), setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        row_facilities = parse_facilities(row.get("facilities"), setting_lines(self.main.services, "phase1_facilities", FACILITY_OPTIONS))
        overlap = req_facilities & row_facilities
        if overlap:
            score += min(10, len(overlap) * 3)
            reasons.append(f"{len(overlap)} facilities matched")
        return score, reasons

    def _nearby(self, left: str, right: str) -> bool:
        groups = [
            {"gizri", "dha", "defence", "dha phase 4", "dha phase 5", "dha phase 6", "zamzama", "clifton", "boat basin", "sea view", "marina"},
            {"clifton", "clifton block 1", "clifton block 2", "clifton block 3", "clifton block 4", "clifton block 5", "clifton block 6", "clifton block 7", "clifton block 8", "clifton block 9", "boat basin"},
            {"pechs", "tariq road", "bahadurabad", "kda scheme"},
            {"north nazimabad", "nazimabad", "fb area", "hyderi", "water pump"},
        ]
        return any(left in group and right in group for group in groups)


class SummaryPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        refresh = QPushButton("Refresh Summary")
        refresh.setObjectName("AccentButton")
        refresh.clicked.connect(self.refresh)
        export = QPushButton("Export")
        export.clicked.connect(self.export)
        controls.addWidget(QLabel("Financial Summary"))
        controls.addStretch(1)
        controls.addWidget(refresh)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text, 1)
        self.refresh()

    def refresh(self) -> None:
        self.text.setPlainText(self.main.build_financial_text())

    def export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Financial Summary",
            str(OUTPUT_DIR / "financial_summary.txt"),
            "Text Files (*.txt)",
        )
        if path:
            Path(path).write_text(self.text.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "Exported", f"Saved to:\n{path}")