"""Record creation/editing dialog."""
from __future__ import annotations
from PySide6.QtCore import QDate, QEvent, Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QCheckBox, QPushButton, QDialogButtonBox, QMessageBox, QWidget, QSizePolicy
from typing import Any
from CRM.utils import safe_float, parse_qdate, parse_facilities, parse_multi_options, normalize_text, validate_form_value, is_date_key
from CRM.constants import DATE_DISPLAY_FORMAT, DATE_STORAGE_FORMAT, PHONE_FORM_KEYS, EMAIL_FORM_KEYS, FACILITY_OPTIONS

class RecordDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list[FieldSpec],
        data: dict | None = None,
        parent: QWidget | None = None,
        *,
        allow_save_new: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(860, 640)
        self.setMinimumSize(720, 520)
        self.widgets: dict[str, QWidget] = {}
        self.fields = fields
        self.save_and_new = False
        self.allow_save_new = allow_save_new
        data = data or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        layout.addWidget(heading)

        hint = QLabel("Required fields are marked with *. Use Tab to move quickly between fields.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        if self._has_property_fields():
            layout.addLayout(self._template_bar())

        buttons = QDialogButtonBox()
        primary_label = "Add" if title.startswith("Add ") else "Save"
        save = buttons.addButton(primary_label, QDialogButtonBox.AcceptRole)
        save.clicked.connect(self.accept)
        if allow_save_new:
            save_new_label = "Add && New" if title.startswith("Add ") else "Save && New"
            save_new = buttons.addButton(save_new_label, QDialogButtonBox.ActionRole)
            save_new.clicked.connect(self.accept_save_new)
        cancel = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        cancel.clicked.connect(self.reject)
        layout.addWidget(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 8, 0, 8)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        row = 0
        col_group = 0

        for spec in fields:
            raw_default = spec.default() if callable(spec.default) else spec.default
            value = data.get(spec.key, raw_default)
            widget = self._make_widget(spec, value)
            self.widgets[spec.key] = widget
            label = QLabel(spec.label)
            label.setObjectName("RequiredLabel" if spec.required else "FormLabel")
            if spec.kind in {"text", "facilities", "multiselect"}:
                if col_group:
                    row += 1
                    col_group = 0
                label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                grid.addWidget(label, row, 0)
                grid.addWidget(widget, row, 1, 1, 3)
                row += 1
                col_group = 0
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

    def _has_property_fields(self) -> bool:
        keys = {field.key for field in self.fields}
        return bool({"property_requires", "property_availability", "size", "floor"} & keys)

    def _template_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Quick fill"))
        templates = [
            ("Flat", {"property_requires": "flat", "property_availability": "flat", "size": "double-bed", "floor": "3rd"}),
            ("Shop", {"property_requires": "shop", "property_availability": "shop", "size": "ground floor", "floor": "Ground"}),
            ("House", {"property_requires": "house", "property_availability": "house", "size": "single story", "floor": "Ground"}),
            ("Office", {"property_requires": "office", "property_availability": "office", "size": "any floor", "floor": "1st"}),
            ("Plot", {"property_requires": "plot", "property_availability": "plot", "size": "", "floor": "-"}),
            ("Villa", {"property_requires": "villa", "property_availability": "villa", "size": "double story", "floor": "Ground"}),
        ]
        for label, values in templates:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, v=values: self.apply_template(v))
            bar.addWidget(button)
        bar.addStretch(1)
        return bar

    def apply_template(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            widget = self.widgets.get(key)
            if not widget:
                continue
            if isinstance(widget, QComboBox):
                idx = widget.findText(value)
                if idx < 0 and value:
                    widget.addItem(value)
                    idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                elif widget.isEditable():
                    widget.setEditText(value)
            elif hasattr(widget, "multi_boxes"):
                self._set_multiselect_widget_values(widget, value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)

    def _make_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        if spec.kind == "text":
            widget = QTextEdit()
            widget.setMinimumHeight(82)
            widget.setMaximumHeight(120)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            widget.setPlainText("" if value is None else str(value))
            return widget
        if spec.kind == "facilities":
            return self._make_facilities_widget(spec, value)
        if spec.kind == "multiselect":
            return self._make_multiselect_widget(spec, value)
        if spec.kind in {"combo", "combo_other", "autocomplete"}:
            widget = QComboBox()
            widget.addItems(spec.options)
            widget.setEditable(spec.kind != "combo")
            if value not in (None, ""):
                idx = widget.findText(str(value))
                if idx < 0:
                    widget.addItem(str(value))
                    idx = widget.findText(str(value))
                if spec.kind == "combo":
                    widget.setCurrentIndex(idx)
                elif idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setEditText(str(value))
            return widget
        if spec.kind == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
            if value:
                widget.setDate(parse_qdate(value))
            else:
                widget.setDate(QDate.currentDate())
            return widget
        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        if spec.numeric:
            widget.setPlaceholderText("0")
        elif is_date_key(spec.key):
            widget.setPlaceholderText("DD/MM/YYYY")
        elif spec.key in PHONE_FORM_KEYS:
            widget.setPlaceholderText("03000000000")
        elif spec.key in EMAIL_FORM_KEYS:
            widget.setPlaceholderText("name@example.com")
        return widget

    def _make_facilities_widget(self, spec: FieldSpec, value: Any) -> QWidget:
        frame = QFrame()
        frame.setObjectName("FacilitiesBox")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        options = spec.options or FACILITY_OPTIONS
        selected = parse_facilities(value, options)
        boxes: list[QRadioButton] = []
        for index, label in enumerate(options):
            checkbox = QRadioButton(label)
            checkbox.setObjectName("FacilityCheck")
            checkbox.setAutoExclusive(False)
            checkbox.setChecked(label in selected)
            checkbox.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            grid.addWidget(checkbox, index // 3, index % 3)
            boxes.append(checkbox)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        frame.facility_boxes = boxes
        return frame

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
        for label in selected:
            if normalize_text(label) not in {normalize_text(option) for option in options}:
                options.append(label)
        boxes: list[QCheckBox] = []
        columns = 4
        selected_keys = {normalize_text(label) for label in selected}
        for index, label in enumerate(options):
            checkbox = QCheckBox(label)
            checkbox.setObjectName("MultiSelectCheck")
            checkbox.setChecked(normalize_text(label) in selected_keys)
            checkbox.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            grid.addWidget(checkbox, index // columns, index % columns)
            boxes.append(checkbox)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        frame.multi_boxes = boxes
        return frame

    def _set_multiselect_widget_values(self, widget: QWidget, value: Any) -> None:
        selected = {normalize_text(label) for label in parse_multi_options(value)}
        for box in getattr(widget, "multi_boxes", []):
            box.setChecked(normalize_text(box.text()) in selected)

    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for spec in self.fields:
            value = self.raw_value(spec)
            if spec.numeric:
                value = safe_float(value)
            values[spec.key] = value
        return values

    def raw_value(self, spec: FieldSpec) -> str:
        widget = self.widgets[spec.key]
        if spec.kind == "facilities":
            boxes = getattr(widget, "facility_boxes", [])
            return ", ".join(box.text() for box in boxes if box.isChecked())
        if spec.kind == "multiselect":
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

    def validate(self) -> tuple[bool, str]:
        try:
            for spec in self.fields:
                raw = self.raw_value(spec)
                # For non-editable combos, build the full allowed set from the
                # widget's actual items (which includes any value added from DB).
                widget = self.widgets[spec.key]
                effective_options: list[str] | None = spec.options if spec.options else None
                if spec.kind == "combo" and isinstance(widget, QComboBox):
                    effective_options = [widget.itemText(i) for i in range(widget.count())]
                validate_form_value(
                    spec.key,
                    spec.label,
                    raw,
                    required=spec.required,
                    numeric=spec.numeric,
                    options=effective_options,
                    strict_options=(spec.kind == "combo"),
                )
        except ValueError as exc:
            return False, str(exc)
        return True, ""

    def accept(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required", message)
            return
        self.save_and_new = False
        super().accept()

    def accept_save_new(self) -> None:
        ok, message = self.validate()
        if not ok:
            QMessageBox.warning(self, "Required", message)
            return
        self.save_and_new = True
        super().accept()


