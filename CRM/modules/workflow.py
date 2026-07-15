"""Workflow module."""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget, QScrollArea, QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy
from typing import Any

# ─── CRM module imports ───
from CRM.utils import safe_float, quote_identifier, money, format_date_display, gen_id
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.constants import ROLE_PERMISSIONS, FLOOR_OPTIONS, FACILITY_OPTIONS, PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, COMMON_AREAS
from CRM.modules.data_table import DataTablePage
from CRM.modules.success_factors import _wf_workflows_spec, _wf_steps_spec, _wf_instances_spec, _wf_tasks_spec, _wf_approvals_spec, _wf_notifications_spec, _wf_sla_spec, _wf_audit_spec

class WFDashboardPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Workflow Overview")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)
        self.cards_layout = QGridLayout()
        layout.addLayout(self.cards_layout)
        layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def count(table: str, where: str = "") -> int:
            sql = f"SELECT COUNT(*) AS c FROM {table}"
            if where:
                sql += f" WHERE {where}"
            row = self.main.services.fetch_one(sql)
            return int(row["c"]) if row else 0

        metrics = [
            ("Workflows Defined", count("wf_workflows", "status='Active'"), "blue"),
            ("Running Instances", count("wf_instances", "status='Running'"), "cyan"),
            ("Pending Tasks", count("wf_tasks", "status='Pending'"), "royal"),
            ("Pending Approvals", count("wf_approvals", "status='Pending'"), "green"),
            ("SLA Breaches", count("wf_sla_log", "breached=1"), "slate"),
            ("Unread Notifs", count("wf_notifications", "status='Unread'"), "sky"),
        ]
        for index, (label, value, tone) in enumerate(metrics):
            tile = self.main._dashboard_tile(label, value, tone)
            self.cards_layout.addWidget(tile, index // 3, index % 3)
            self.cards_layout.setColumnStretch(index % 3, 1)


class WorkflowModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Workflow Engine")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        tabs = QTabWidget()
        self.wf_dashboard = WFDashboardPage(main)
        self.workflows = DataTablePage(main, _wf_workflows_spec())
        self.steps = DataTablePage(main, _wf_steps_spec())
        self.instances = DataTablePage(main, _wf_instances_spec())
        self.tasks = DataTablePage(main, _wf_tasks_spec())
        self.approvals = DataTablePage(main, _wf_approvals_spec())
        self.notifications = DataTablePage(main, _wf_notifications_spec())
        self.sla_log = DataTablePage(main, _wf_sla_spec())
        self.audit_log = DataTablePage(main, _wf_audit_spec())

        tabs.addTab(self.wf_dashboard, "Overview")
        tabs.addTab(self.workflows, "Workflow Definitions")
        tabs.addTab(self.steps, "Workflow Steps")
        tabs.addTab(self.instances, "Running Instances")
        tabs.addTab(self.tasks, "Tasks")
        tabs.addTab(self.approvals, "Approvals")
        tabs.addTab(self.notifications, "Notifications")
        tabs.addTab(self.sla_log, "SLA Log")
        tabs.addTab(self.audit_log, "Audit Trail")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        for page in (
            self.wf_dashboard,
            self.workflows,
            self.steps,
            self.instances,
            self.tasks,
            self.approvals,
            self.notifications,
            self.sla_log,
            self.audit_log,
        ):
            if hasattr(page, "refresh"):
                page.refresh()