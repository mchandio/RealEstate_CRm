"""Dashboard rendering widget extracted from ModernCRMWindow.

Provides DashboardWidget that encapsulates all dashboard rendering logic,
separating it from the main window class.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from crm_core.constants import CLOSED_AVAILABILITY_ARCHIVES

from CRM.constants import DEAL_TABLES
from CRM.widgets.charts import DashboardBarChart, DashboardDonut, DashboardLineChart


class DashboardWidget(QWidget):
    """Encapsulates all dashboard rendering logic.

    This widget receives a reference to the host application (ModernCRMWindow)
    to access services, settings, and report data. All dashboard-specific
    rendering helpers are contained here.
    """

    def __init__(self, host: Any) -> None:
        super().__init__()
        self.host = host
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QFrame()
        body.setObjectName("DashboardReportSurface")
        body.setStyleSheet(
            "#DashboardReportSurface { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop:0 #e2f1ff, stop:0.58 #f4f9ff, stop:1 #d5ebff); "
            "border: 1px solid #bdd6f4; border-radius: 12px; }"
        )
        self.dashboard_layout = QVBoxLayout(body)
        self.dashboard_layout.setContentsMargins(30, 28, 30, 34)
        self.dashboard_layout.setSpacing(18)
        scroll.setWidget(body)
        layout.addWidget(scroll)

    # ── Data helpers ──────────────────────────────────────────────────

    def _active_where(self, table: str) -> str:
        columns = self.host.services.table_columns(table)
        clauses = []
        if "is_deleted" in columns:
            clauses.append("COALESCE(is_deleted, 0)=0")
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(table)
        if closed_rule and "status" in columns:
            clauses.append(f"LOWER(COALESCE(status,''))<>LOWER('{closed_rule[0]}')")
        return "WHERE " + " AND ".join(clauses) if clauses else ""

    def _count(self, table: str) -> int:
        where = self._active_where(table)
        row = self.host.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} {where}")
        return int(row["count"]) if row else 0

    def _pending_approvals(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.host.services.table_columns(table)
            if "approval_status" not in columns:
                continue
            where = self._active_where(table)
            connector = " AND " if where else "WHERE "
            row = self.host.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {where}{connector}approval_status='Pending'"
            )
            total += int(row["count"]) if row else 0
        if self.host.services.table_columns("pending_approvals"):
            row = self.host.services.fetch_one("SELECT COUNT(*) AS count FROM pending_approvals WHERE status='Pending'")
            total += int(row["count"]) if row else 0
        return total

    def _location_label(self, value: Any) -> str:
        text = " ".join(str(value or "").strip().split())
        if not text:
            return "Unspecified"
        upper = text.upper()
        if "GIZRI" in upper:
            return "Gizri"
        if "DHA" in upper or "DEFENCE" in upper:
            return "DHA"
        if "CLIFTON" in upper:
            return "Clifton"
        if "PECHS" in upper:
            return "PECHS"
        if "NORTH" in upper and "NAZIM" in upper:
            return "North Nazim"
        if "BAHRIA" in upper:
            return "Bahria"
        return text[:18]

    def _location_buckets(self) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        mapping = (
            ("rent_requirements", "rent_requirements"),
            ("rent_availability", "rent_availability"),
            ("sale_requirements", "sale_requirements"),
            ("sale_availability", "sale_availability"),
        )
        for table, key in mapping:
            where = self._active_where(table)
            rows = self.host.services.fetch_all(
                f"SELECT COALESCE(location, '') AS location, COUNT(*) AS total FROM {table} {where} GROUP BY COALESCE(location, '')"
            )
            for row in rows:
                label = self._location_label(row.get("location"))
                bucket = buckets.setdefault(label, {
                    "location": label,
                    "rent_requirements": 0,
                    "rent_availability": 0,
                    "sale_requirements": 0,
                    "sale_availability": 0,
                })
                bucket[key] += int(row.get("total") or 0)
        ranked = sorted(
            buckets.values(),
            key=lambda item: item["rent_requirements"] + item["rent_availability"] + item["sale_requirements"] + item["sale_availability"],
            reverse=True,
        )
        return ranked[:6] or [{"location": "No Data", "rent_requirements": 0, "rent_availability": 0}]

    def _client_segments(self, total: int) -> list[dict[str, Any]]:
        if total <= 0:
            return [
                {"label": "Active Searchers", "value": 0, "percent": 0, "color": "#1976d2"},
                {"label": "Long-Term Leads", "value": 0, "percent": 0, "color": "#43a047"},
                {"label": "Past Clients", "value": 0, "percent": 0, "color": "#007c91"},
            ]
        active = self.host.services.fetch_one(
            """SELECT COUNT(*) AS count FROM clients
               WHERE LOWER(COALESCE(status,''))='active'
                 AND LOWER(COALESCE(client_type,'')) IN ('tenant', 'buyer', 'investor')"""
        )
        long_term = self.host.services.fetch_one(
            """SELECT COUNT(*) AS count FROM clients
               WHERE LOWER(COALESCE(client_type,'')) IN ('owner', 'seller', 'broker')"""
        )
        active_count = int(active["count"]) if active else 0
        long_count = int(long_term["count"]) if long_term else 0
        if active_count + long_count > total:
            long_count = max(total - active_count, 0)
        past_count = max(total - active_count - long_count, 0)
        rows = [
            ("Active Searchers", active_count, "#1976d2"),
            ("Long-Term Leads", long_count, "#43a047"),
            ("Past Clients", past_count, "#007c91"),
        ]
        return [
            {"label": label, "value": value, "percent": round((value / total) * 100), "color": color}
            for label, value, color in rows
        ]

    def _closed_count(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.host.services.table_columns(table)
            clauses = []
            if "workflow_stage" in columns:
                clauses.append("LOWER(COALESCE(workflow_stage,''))='deal done'")
            if "status" in columns:
                clauses.append("LOWER(COALESCE(status,'')) IN ('rented', 'sold')")
            if not clauses:
                continue
            active_where = self._active_where(table)
            connector = " AND " if active_where else "WHERE "
            row = self.host.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {active_where}{connector}({' OR '.join(clauses)})"
            )
            total += int(row["count"]) if row else 0
        for table in ("rented_properties", "sold_properties"):
            if self.host.services.table_columns(table):
                row = self.host.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                total += int(row["count"]) if row else 0
        return total

    def _summary_data(self) -> dict[str, Any]:
        data = self.host.report_service.dashboard_summary(
            generated_by=self.host.current_user.get("full_name") or self.host.current_user.get("username") or "CRM User",
            generated_role=self.host.role,
        )
        clients = int(data.get("clients") or 0)
        operation_colors = {"blue": "#0e82b1", "orange": "#ff9818", "green": "#43a047"}
        return {
            "kpis": [
                ("Rent Requirements", int(data.get("rent_requirements") or 0), "blue"),
                ("Rent Availability", int(data.get("rent_available") or 0), "cyan"),
                ("Sale Requirements", int(data.get("sale_requirements") or 0), "silver"),
                ("Sale Availability", int(data.get("sale_available") or 0), "green"),
                ("Rented Done", int(data.get("rented_done") or 0), "royal"),
                ("Sold Done", int(data.get("sold_done") or 0), "sky"),
                ("Properties", int(data.get("properties") or 0), "royal"),
                ("Clients", clients, "sky"),
                ("Employee", int(data.get("employees") or 0), "slate"),
            ],
            "pending": int(data.get("pending_approvals") or 0),
            "locations": data.get("demand_supply") or [],
            "segments": data.get("client_segments") or [],
            "clients": clients,
            "roadmap": data.get("roadmap") or [],
            "operations": [
                (
                    str(row.get("label") or ""),
                    str(row.get("value") or ""),
                    operation_colors.get(str(row.get("tone") or "blue"), "#0e82b1"),
                )
                for row in data.get("operations", [])
            ],
        }

    # ── UI helpers ────────────────────────────────────────────────────

    def _label(self, text: str, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, color: str = "#17345c") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", size, weight))
        label.setStyleSheet(f"color: {color};")
        return label

    def _tile(self, title: str, value: Any, tone: str) -> QFrame:
        colors = {
            "blue": ("#1f7ee7", "#0569c9", "#ffffff"),
            "cyan": ("#3cb7f2", "#218bd6", "#ffffff"),
            "silver": ("#cbd5e1", "#a9b5c4", "#0b2b50"),
            "green": ("#2ca84f", "#0d7a38", "#ffffff"),
            "royal": ("#217ae4", "#115fcd", "#ffffff"),
            "sky": ("#55b5e9", "#2d94d3", "#ffffff"),
            "slate": ("#c7d0dc", "#aab5c1", "#0b2b50"),
        }
        top, bottom, text_color = colors.get(tone, colors["blue"])
        frame = QFrame()
        frame.setMinimumHeight(104)
        frame.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {top}, stop:1 {bottom}); "
            "border-radius: 8px; border: 1px solid #dbeafe; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(6)
        value_label = self._label(f"{int(value):,}" if isinstance(value, int) else str(value), 26, QFont.Weight.Black, text_color)
        title_label = self._label(title, 9, QFont.Weight.Black, text_color)
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return frame

    def _panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setStyleSheet(
            "#DashboardPanel { background: #f8fbff; border: 1px solid #b8d1ef; "
            "border-radius: 10px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        heading = self._label(title, 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        return panel, layout

    def _legend_item(self, text: str, color: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QFrame()
        dot.setFixedSize(18, 12)
        dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
        label = self._label(text, 8, QFont.Weight.Bold, "#15457f")
        layout.addWidget(dot)
        layout.addWidget(label)
        return widget

    def _approval_card(self, pending: int) -> QFrame:
        frame = QFrame()
        frame.setMinimumHeight(202)
        frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ff9f16, stop:1 #ec7900); "
            "border-radius: 10px; border: 1px solid #ffd08a; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 24)
        value = self._label(f"{pending:,}", 38, QFont.Weight.Black, "#ffffff")
        title = self._label("Pending Approvals", 17, QFont.Weight.Black, "#ffffff")
        note = self._label("Needs Admin Review", 11, QFont.Weight.Bold, "#ffffff")
        layout.addStretch(1)
        layout.addWidget(value)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch(1)
        return frame

    def _demand_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._panel("Rent Demand vs. Supply")
        layout.addWidget(DashboardBarChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._legend_item("Rent Requirements", "#1976d2"))
        legend.addSpacing(20)
        legend.addWidget(self._legend_item("Rent Availability", "#21964b"))
        layout.addLayout(legend)
        return panel

    def _segments_panel(self, total: int, segments: list[dict[str, Any]], operations: list[tuple[str, str, str]]) -> QFrame:
        panel, layout = self._panel("")
        layout.takeAt(0).widget().deleteLater()
        top = QHBoxLayout()
        top.setSpacing(24)
        top.addWidget(DashboardDonut(total, segments), 0, Qt.AlignmentFlag.AlignCenter)
        right = QVBoxLayout()
        heading = self._label("Client Segments", 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(heading)
        for row in segments:
            item = QHBoxLayout()
            dot = QFrame()
            dot.setFixedSize(24, 24)
            dot.setStyleSheet(f"background: {row.get('color')}; border-radius: 12px;")
            item.addWidget(dot)
            item.addWidget(self._label(str(row.get("label") or ""), 10, QFont.Weight.Normal, "#0f3768"), 1)
            item.addWidget(self._label(f"{int(row.get('percent') or 0)}%", 11, QFont.Weight.Black, "#1976d2"))
            right.addLayout(item)
        top.addLayout(right, 1)
        layout.addLayout(top)
        table = QFrame()
        table.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #c7dcf3; border-radius: 8px; }")
        table_layout = QVBoxLayout(table)
        table_layout.setContentsMargins(12, 8, 12, 8)
        table_layout.setSpacing(6)
        for label, value, color in operations:
            row = QHBoxLayout()
            square = QFrame()
            square.setFixedSize(24, 24)
            square.setStyleSheet(f"background: {color}; border-radius: 3px;")
            row.addWidget(square)
            row.addWidget(self._label(label, 9, QFont.Weight.Normal, "#163f79"), 1)
            row.addWidget(self._label(value, 10, QFont.Weight.Black, "#0f7fe6"))
            table_layout.addLayout(row)
        layout.addWidget(table)
        return panel

    def _roadmap_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._panel("30 / 90 / 180 Day Roadmap")
        layout.addWidget(DashboardLineChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._legend_item("Response Time", "#1976d2"))
        legend.addWidget(self._legend_item("Approvals Cleared", "#ef7d00"))
        legend.addWidget(self._legend_item("Conversion", "#3b9629"))
        layout.addLayout(legend)
        return panel

    # ── Main refresh ──────────────────────────────────────────────────

    def refresh(self) -> None:
        """Rebuild the entire dashboard content."""
        # Clear existing content
        while self.dashboard_layout.count():
            item = self.dashboard_layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        data = self._summary_data()

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 0, 18, 4)
        title = self._label(f"{self.host.company_name} Report Summary", 27, QFont.Weight.Black, "#245ca9")
        user_line = f"{self.host.current_user.get('full_name') or self.host.current_user.get('username') or 'CRM User'}, {self.host.role}"
        subtitle = self._label(user_line, 13, QFont.Weight.Normal, "#315784")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.dashboard_layout.addWidget(header)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)
        for index, (label, value, tone) in enumerate(data["kpis"]):
            kpi_grid.addWidget(self._tile(label, value, tone), 0, index)
            kpi_grid.setColumnStretch(index, 1)
        self.dashboard_layout.addLayout(kpi_grid)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self._approval_card(data["pending"]), 3)
        top_row.addWidget(self._demand_panel(data["locations"]), 8)
        self.dashboard_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        bottom_row.addWidget(self._segments_panel(data["clients"], data["segments"], data["operations"]), 1)
        bottom_row.addWidget(self._roadmap_panel(data["roadmap"]), 1)
        self.dashboard_layout.addLayout(bottom_row)
        self.dashboard_layout.addStretch(1)

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
            widget = item.widget()
            if widget:
                widget.deleteLater()
