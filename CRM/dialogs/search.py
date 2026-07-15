"""Global search dialog."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QWidget, QSizePolicy
from typing import Any

class SearchDialog(QDialog):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__(main)
        self.main = main
        self.rows: list[dict] = []
        self.display_columns: list[str] = []
        self.display_column_labels: dict[str, str] = {}
        self.table_column_cache: dict[str, list[str]] = {}
        self.available_sources = self.main.find_sources()
        self.setWindowTitle("Find")
        self.resize(1180, 640)
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Sort"))
        self.source_filter = QComboBox()
        self.source_filter.addItem("All", "")
        for label, table in self.available_sources:
            self.source_filter.addItem(label, table)
        self.source_filter.currentIndexChanged.connect(lambda _index: self.search() if self.query.text().strip() else None)
        bar.addWidget(self.source_filter)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Find by name, contact, property, location, budget, facilities, or remarks...")
        button = QPushButton("Find")
        button.setObjectName("AccentButton")
        button.clicked.connect(self.search)
        bar.addWidget(self.query, 1)
        bar.addWidget(button)
        layout.addLayout(bar)
        selection = QHBoxLayout()
        self.selection_label = QLabel("0 selected")
        self.selection_label.setObjectName("SelectionCount")
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all_rows)
        clear = QPushButton("Clear Selection")
        clear.clicked.connect(self.clear_selection)
        copy = QPushButton("Copy Selected")
        copy.clicked.connect(self.copy_selected_rows)
        print_voucher = QPushButton("Print Voucher")
        print_voucher.setObjectName("AccentButton")
        print_voucher.clicked.connect(self.print_voucher)
        save_pdf = QPushButton("Save Voucher PDF")
        save_pdf.clicked.connect(self.save_voucher_pdf)
        selection.addWidget(self.selection_label)
        selection.addStretch(1)
        selection.addWidget(select_all)
        selection.addWidget(clear)
        selection.addWidget(copy)
        selection.addWidget(print_voucher)
        selection.addWidget(save_pdf)
        layout.addLayout(selection)
        self.table = ExcelTableWidget()
        configure_multi_select_table(self.table)
        self.table.itemSelectionChanged.connect(self.update_selection_label)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.table, 1)
        self.query.returnPressed.connect(self.search)

    def search_sources(self) -> list[tuple[str, str]]:
        selected_table = self.source_filter.currentData()
        if selected_table:
            if any(table == selected_table for _label, table in self.available_sources):
                return [(self.source_label(selected_table), selected_table)]
            return []
        return list(self.available_sources)

    def table_columns(self, table: str) -> list[str]:
        if table not in self.table_column_cache:
            rows = self.main.services.fetch_all(f"PRAGMA table_info({table})")
            self.table_column_cache[table] = [
                row["name"]
                for row in rows
                if row.get("name") not in GLOBAL_SEARCH_HIDDEN_COLUMNS
            ]
        return self.table_column_cache[table]

    def source_label(self, table: str) -> str:
        return GLOBAL_SEARCH_SOURCE_LABELS.get(table, table.replace("_", " ").title())

    def field_label(self, key: str) -> str:
        if key in self.display_column_labels:
            return self.display_column_labels[key]
        if key == "_source":
            return "Type"
        if key == "_table":
            return "Table"
        return {
            "id": "Sr No.",
            "client_name": "Name",
            "contact": "Contact No.",
            "property_requires": "Property Required / Needed",
            "property_availability": "Property Available",
            "size": "Rooms",
            "measurement": "Measurement",
            "measurement_unit": "Size",
            "sq_ft": "Sq Ft",
            "sq_ft_yards": "Sq Ft / Yards",
            "cnic": "CNIC",
        }.get(key, key.replace("_", " ").title())

    def display_value(self, key: str, value: Any) -> str:
        if value in (None, ""):
            return ""
        if is_date_key(key):
            return format_date_display(value)
        if key in GLOBAL_SEARCH_MONEY_COLUMNS and is_valid_number_text(value):
            return money(value, self.main.currency_symbol)
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)

    def result_value(self, row: dict, aliases: tuple[str, ...], default: Any = "") -> Any:
        for key in aliases:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return default

    def normalize_search_row(self, source: str, table: str, row: dict) -> dict:
        normalized = {"_source": source, "_table": table, "_raw": row, "id": row.get("id")}
        columns = ["_source"]
        specs = FIND_RESULT_COLUMNS.get(table, [])
        if not specs:
            for key in self.table_columns(table):
                normalized[key] = row.get(key)
                if key not in columns:
                    columns.append(key)
            normalized["_columns"] = columns
            return normalized
        for key, _label, aliases, default in specs:
            normalized[key] = self.result_value(row, aliases, default)
            if key not in columns:
                columns.append(key)
        normalized["_columns"] = columns
        return normalized

    def display_schema(self, rows: list[dict]) -> tuple[list[str], dict[str, str]]:
        selected_table = self.source_filter.currentData()
        if selected_table:
            specs = FIND_RESULT_COLUMNS.get(selected_table, [])
            if specs:
                return [key for key, _label, _aliases, _default in specs], {
                    key: label for key, label, _aliases, _default in specs
                }
            columns = ["_source"] + self.table_columns(selected_table)
            return columns, {key: self.field_label(key) for key in columns}

        present: set[str] = set()
        for row in rows:
            present.update(row.get("_columns", []))
        columns = [key for key in FIND_ALL_COLUMN_ORDER if key in present]
        columns.extend(sorted(key for key in present if key not in columns and key not in GLOBAL_SEARCH_HIDDEN_COLUMNS))
        labels = {key: FIND_ALL_COLUMN_LABELS.get(key, self.field_label(key)) for key in columns}
        return columns, labels

    def search(self) -> None:
        term = self.query.text().strip().lower()
        if not term:
            return
        results: list[dict] = []
        for source, table in self.search_sources():
            columns = self.table_columns(table)
            if not columns:
                continue
            source_text = f"{source} {table.replace('_', ' ')}".lower()
            if term in source_text:
                sql = f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50"
                params: tuple[Any, ...] = ()
            else:
                where = " OR ".join(f"LOWER(CAST(COALESCE(\"{col}\", '') AS TEXT)) LIKE ?" for col in columns)
                sql = f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 50"
                params = tuple([f"%{term}%"] * len(columns))
            for row in self.main.services.fetch_all(sql, params):
                results.append(self.normalize_search_row(source, table, row))
        results.sort(
            key=lambda row: (
                FIND_SOURCE_ORDER.get(str(row.get("_table") or ""), 99),
                -safe_int(row.get("id")),
            )
        )
        self.rows = results
        self.display_columns, self.display_column_labels = self.display_schema(results)
        headers = [self.field_label(key) for key in self.display_columns]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(results))
        for r, row in enumerate(results):
            for c, key in enumerate(self.display_columns):
                item = QTableWidgetItem(self.display_value(key, row.get(key)))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()):
            self.table.setColumnWidth(col, min(max(self.table.columnWidth(col), 90), 230))
        self.update_selection_label()

    def selected_indexes(self) -> list[int]:
        return selected_table_row_indexes(self.table, len(self.rows))

    def selected_rows(self) -> list[dict]:
        return [self.rows[index] for index in self.selected_indexes()]

    def select_all_rows(self) -> None:
        select_all_table_rows(self.table)
        self.update_selection_label()

    def clear_selection(self) -> None:
        clear_table_selection(self.table)
        self.update_selection_label()

    def update_selection_label(self) -> None:
        self.selection_label.setText(f"{len(self.selected_indexes())} of {len(self.rows)} selected")

    def copy_selected_rows(self) -> None:
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "Select", "Select one or more search results first.")
            return
        if self.display_columns:
            keys = self.display_columns
        else:
            keys, labels = self.display_schema(rows)
            self.display_column_labels.update(labels)
        lines = ["\t".join(self.field_label(key) for key in keys)]
        for row in rows:
            lines.append("\t".join(self.display_value(key, row.get(key)) for key in keys))
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"{len(rows)} selected result(s) copied to clipboard.")

    def voucher_rows(self) -> list[dict]:
        rows = self.selected_rows()
        if rows:
            return rows
        if self.rows:
            return self.rows
        QMessageBox.information(self, "Find", "Find records first, then print or save the voucher.")
        return []

    def voucher_html(self, rows: list[dict]) -> str:
        query = html.escape(self.query.text().strip() or "All visible results")
        generated_at = datetime.now().strftime(PY_DATE_DISPLAY_FORMAT + " %I:%M %p")
        user_name = html.escape(self.main.current_user.get("full_name") or self.main.current_user.get("username") or "")
        company = html.escape(self.main.company_name)
        body_parts = [
            "<html><head><style>",
            """
            @page { size: legal landscape; margin: 7mm; }
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; color: #111827; margin: 0; font-size: 9.5pt; }
            .voucher { border: 2px solid #111827; padding: 12px; margin: 0 0 10px 0; page-break-inside: avoid; page-break-after: always; width: 100%; }
            .voucher:last-child { page-break-after: auto; }
            .top { display: table; width: 100%; border-bottom: 2px solid #111827; padding-bottom: 10px; margin-bottom: 14px; }
            .brand { display: table-cell; vertical-align: top; }
            .brand h1 { margin: 0; font-size: 18px; letter-spacing: 0; }
            .brand p { margin: 4px 0 0 0; color: #475569; font-size: 9pt; }
            .stamp { display: table-cell; text-align: right; vertical-align: top; font-size: 9pt; color: #475569; }
            .stamp strong { display: block; color: #2563eb; font-size: 13pt; margin-bottom: 4px; }
            .summary { width: 100%; border-collapse: collapse; margin-bottom: 10px; table-layout: fixed; }
            .summary td { border: 1px solid #cbd5e1; padding: 5px 7px; font-size: 9pt; overflow-wrap: anywhere; word-break: break-word; }
            .summary .label { width: 17%; background: #f1f5f9; font-weight: bold; color: #334155; }
            .fields { width: 100%; border-collapse: collapse; table-layout: fixed; }
            .fields th { background: #eaf2ff; color: #0f172a; border: 1px solid #bfdbfe; padding: 5px; text-align: left; font-size: 9pt; }
            .fields td { border: 1px solid #dbe3ef; padding: 5px; vertical-align: top; font-size: 8.7pt; overflow-wrap: anywhere; word-break: break-word; }
            .field-name { width: 18%; font-weight: bold; background: #f8fafc; color: #334155; }
            .footer { margin-top: 10px; font-size: 8pt; color: #64748b; text-align: center; }
            """,
            "</style></head><body>",
        ]
        for index, row in enumerate(rows, start=1):
            source = html.escape(str(row.get("_source") or self.source_label(str(row.get("_table") or ""))))
            record_id = html.escape(str(row.get("id") or ""))
            status = html.escape(str(row.get("approval_status") or row.get("status") or row.get("workflow_stage") or ""))
            body_parts.append("<div class='voucher'>")
            body_parts.append(
                f"<div class='top'><div class='brand'><h1>{company}</h1>"
                f"<p>Find Voucher</p></div>"
                f"<div class='stamp'><strong>{source}</strong>Voucher #{index:03d}<br>{generated_at}</div></div>"
            )
            body_parts.append("<table class='summary'>")
            body_parts.append(
                f"<tr><td class='label'>Search</td><td>{query}</td>"
                f"<td class='label'>Record ID</td><td>{record_id}</td></tr>"
                f"<tr><td class='label'>Printed By</td><td>{user_name}</td>"
                f"<td class='label'>Status</td><td>{status or '-'}</td></tr>"
            )
            body_parts.append("</table>")
            body_parts.append("<table class='fields'><tr><th>Field</th><th>Value</th><th>Field</th><th>Value</th></tr>")
            columns = [col for col in row.get("_columns", []) if col not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
            if "_source" not in columns:
                columns = ["_source"] + columns
            cells: list[tuple[str, str]] = []
            for key in columns:
                value = row.get(key)
                display = self.display_value(key, value) or "-"
                cells.append((self.field_label(key), display))
            for offset in range(0, len(cells), 2):
                left = cells[offset]
                right = cells[offset + 1] if offset + 1 < len(cells) else ("", "")
                body_parts.append(
                    "<tr>"
                    f"<td class='field-name'>{html.escape(left[0])}</td><td>{html.escape(left[1])}</td>"
                    f"<td class='field-name'>{html.escape(right[0])}</td><td>{html.escape(right[1])}</td>"
                    "</tr>"
                )
            body_parts.append("</table>")
            body_parts.append("<div class='footer'>Generated from Real Estate CRM find. Verify record before deal finalization.</div>")
            body_parts.append("</div>")
        body_parts.append("</body></html>")
        return "".join(body_parts)

    def print_voucher(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Find Voucher")
        if dialog.exec() == QDialog.Accepted:
            doc.print_(printer)

    def save_voucher_pdf(self) -> None:
        rows = self.voucher_rows()
        if not rows:
            return
        default_name = f"find_voucher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Find Voucher PDF",
            str(OUTPUT_DIR / default_name),
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        doc = QTextDocument()
        doc.setHtml(self.voucher_html(rows))
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        configure_legal_landscape_printer(printer)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc.print_(printer)
        QMessageBox.information(self, "Saved", f"Voucher PDF saved:\n{path}")


# SuccessFactors module

