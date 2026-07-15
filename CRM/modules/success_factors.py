"""SuccessFactors module."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QDialog, QTabWidget, QHeaderView, QAbstractItemView, QDialogButtonBox, QMessageBox, QSizePolicy, QFileDialog
from typing import Any

# ─── CRM module imports ───
from CRM.constants import FLOOR_OPTIONS, FACILITY_OPTIONS, PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, COMMON_AREAS, OWNER_BROKER_OPTIONS, FAMILY_OPTIONS
from CRM.utils import safe_float, parse_py_date, parse_qdate, format_date_display
from CRM.models import FieldSpec, ColumnSpec
from CRM.services import CRMServices
from CRM.constants import *
from CRM.widgets.table import configure_multi_select_table, apply_responsive_table_layout, style_workflow_table_item
from CRM.dialogs.record import RecordDialog
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.modules.data_table import DataTablePage
from CRM.utils import *
from CRM.widgets import *
from CRM.dialogs import *

class SFEmployeeCentralPage(DataTablePage):
    """SF Employee Central."""
    pass


class SFRecruitingPage(DataTablePage):
    """SF Recruiting."""
    pass


class SFPerformancePage(DataTablePage):
    """SF Performance and Goals."""
    pass


class SFMustWinBattlesPage(DataTablePage):
    """SF Must Win Battles."""
    pass


class SFKPIsPage(DataTablePage):
    """SF KPIs."""
    pass


class SFLearningPage(DataTablePage):
    """SF Learning Management."""
    pass


class SFCompensationPage(DataTablePage):
    """SF Compensation."""
    pass


class SFOnboardingPage(DataTablePage):
    """SF Onboarding."""
    pass


class SFPositionsPage(DataTablePage):
    """SF Org Chart and Position Management."""
    pass


class SFDashboardPage(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("SuccessFactors Overview")
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

        def count(table: str) -> int:
            row = self.main.services.fetch_one(f"SELECT COUNT(*) AS c FROM {table}")
            return int(row["c"]) if row else 0

        metrics = [
            ("SF Employees", count("sf_employees"), "blue"),
            ("Open Positions", count("sf_positions"), "cyan"),
            ("Active Recruitments", count("sf_recruiting"), "royal"),
            ("Goals In Progress", count("sf_performance_goals"), "green"),
            ("Must Win Battles", count("sf_must_win_battles"), "slate"),
            ("KPIs Tracked", count("sf_kpis"), "sky"),
            ("Learning Assigned", count("sf_learning"), "sky"),
            ("Onboarding Tasks", count("sf_onboarding"), "slate"),
        ]
        for index, (label, value, tone) in enumerate(metrics):
            tile = self.main._dashboard_tile(label, value, tone)
            self.cards_layout.addWidget(tile, index // 3, index % 3)
            self.cards_layout.setColumnStretch(index % 3, 1)


def _sf_employee_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("SF Employee ID", "sf_employee_id"),
        FieldSpec("Full Name *", "full_name", required=True),
        FieldSpec("Email", "email"),
        FieldSpec("Department *", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"], required=True),
        FieldSpec("Job Title *", "job_title", required=True),
        FieldSpec("Manager", "manager_name"),
        FieldSpec("Hire Date", "hire_date", "date"),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Cost Center", "cost_center"),
        FieldSpec("Status", "employment_status", "combo", "Active", ["Active", "On Leave", "Terminated", "Suspended"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("sf_employee_id", "SF ID", width=110),
        ColumnSpec("full_name", "Name", width=170),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("job_title", "Job Title", width=150),
        ColumnSpec("manager_name", "Manager", width=140),
        ColumnSpec("hire_date", "Hire Date", d, 100),
        ColumnSpec("employment_status", "Status", width=100),
        ColumnSpec("location", "Location", width=140),
        ColumnSpec("cost_center", "Cost Center", width=110),
    ]
    insert = [
        "sf_employee_id", "full_name", "email", "department", "job_title",
        "manager_name", "hire_date", "location", "cost_center",
        "employment_status", "notes", "created_by", "created_at",
    ]
    update = [
        "sf_employee_id", "full_name", "email", "department", "job_title",
        "manager_name", "hire_date", "location", "cost_center",
        "employment_status", "notes",
    ]
    return TableSpec("SF Employee Central", "sf_employees", cols, fields, insert, update, permission="successfactors")


def _sf_recruiting_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Requisition ID", "job_requisition_id"),
        FieldSpec("Job Title *", "job_title", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Hiring Manager", "hiring_manager"),
        FieldSpec("Recruiter", "recruiter"),
        FieldSpec("Open Date", "open_date", "date"),
        FieldSpec("Close Date", "close_date", "date"),
        FieldSpec("Status", "status", "combo", "Open", ["Open", "On Hold", "Filled", "Cancelled"]),
        FieldSpec("Applications", "applications_count", numeric=True),
        FieldSpec("Shortlisted", "shortlisted_count", numeric=True),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("job_requisition_id", "Req ID", width=110),
        ColumnSpec("job_title", "Job Title", width=180),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("hiring_manager", "Hiring Mgr", width=140),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("open_date", "Open Date", d, 100),
        ColumnSpec("close_date", "Close Date", d, 100),
        ColumnSpec("applications_count", "Applications", width=110),
        ColumnSpec("shortlisted_count", "Shortlisted", width=100),
    ]
    insert = [
        "job_requisition_id", "job_title", "department", "location",
        "hiring_manager", "recruiter", "open_date", "close_date", "status",
        "applications_count", "shortlisted_count", "notes", "created_by", "created_at",
    ]
    update = [
        "job_requisition_id", "job_title", "department", "location",
        "hiring_manager", "recruiter", "open_date", "close_date", "status",
        "applications_count", "shortlisted_count", "notes",
    ]
    return TableSpec("SF Recruiting", "sf_recruiting", cols, fields, insert, update, permission="successfactors")


def _sf_performance_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Goal Title *", "goal_title", required=True),
        FieldSpec("Description", "goal_description", "text"),
        FieldSpec("Review Period", "review_period", "combo_other", options=["Q1", "Q2", "Q3", "Q4", "H1", "H2", "Annual"]),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Progress %", "progress_pct", numeric=True),
        FieldSpec("Status", "status", "combo", "In Progress", ["In Progress", "Completed", "On Hold", "Cancelled"]),
        FieldSpec("Rating", "rating", "combo", options=["", "Exceeds", "Meets", "Below", "N/A"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("goal_title", "Goal", width=220),
        ColumnSpec("review_period", "Period", width=90),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("progress_pct", "Progress", pct, 90),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("rating", "Rating", width=90),
    ]
    insert = [
        "employee_name", "goal_title", "goal_description", "review_period",
        "due_date", "progress_pct", "status", "rating", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "goal_title", "goal_description", "review_period",
        "due_date", "progress_pct", "status", "rating", "notes",
    ]
    return TableSpec("SF Performance & Goals", "sf_performance_goals", cols, fields, insert, update, permission="successfactors")


def _sf_must_win_battles_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("Battle Code", "battle_code", "entry", lambda: gen_id("MWB")),
        FieldSpec("Battle Title *", "battle_title", required=True),
        FieldSpec("Owner Name *", "owner_name", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Objective", "objective", "text"),
        FieldSpec("Start Date", "start_date", "date"),
        FieldSpec("End Date", "end_date", "date"),
        FieldSpec("Priority", "priority", "combo", "High", ["Low", "Medium", "High", "Critical"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "At Risk", "Won", "Lost", "On Hold"]),
        FieldSpec("Target Value", "target_value", numeric=True),
        FieldSpec("Current Value", "current_value", numeric=True),
        FieldSpec("Progress %", "progress_pct", numeric=True),
        FieldSpec("Business Impact", "business_impact", "combo_other", options=["Revenue", "Cost Saving", "Customer Growth", "Operational Excellence", "Compliance", "People"]),
        FieldSpec("Risks / Blockers", "risks", "text"),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("battle_code", "Code", width=110),
        ColumnSpec("battle_title", "Must Win Battle", width=220),
        ColumnSpec("owner_name", "Owner", width=150),
        ColumnSpec("department", "Department", width=120),
        ColumnSpec("start_date", "Start", d, 100),
        ColumnSpec("end_date", "End", d, 100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("priority", "Priority", width=90),
        ColumnSpec("progress_pct", "Progress", pct, 90),
        ColumnSpec("business_impact", "Impact", width=160),
    ]
    insert = [
        "battle_code", "battle_title", "owner_name", "department", "objective",
        "start_date", "end_date", "priority", "status", "target_value",
        "current_value", "progress_pct", "business_impact", "risks", "notes",
        "created_by", "created_at",
    ]
    update = [
        "battle_code", "battle_title", "owner_name", "department", "objective",
        "start_date", "end_date", "priority", "status", "target_value",
        "current_value", "progress_pct", "business_impact", "risks", "notes",
    ]
    return TableSpec("SF Must Win Battles", "sf_must_win_battles", cols, fields, insert, update, permission="successfactors")


def _sf_kpis_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    pct = lambda value, _symbol: f"{safe_float(value):.0f}%"
    fields = [
        FieldSpec("KPI Code", "kpi_code", "entry", lambda: gen_id("KPI")),
        FieldSpec("KPI Name *", "kpi_name", required=True),
        FieldSpec("Employee Name", "employee_name"),
        FieldSpec("Owner Name", "owner_name"),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Category", "category", "combo_other", options=["Revenue", "Sales", "Operations", "Customer", "People", "Compliance", "Quality"]),
        FieldSpec("Period", "period", "combo_other", options=["Q1", "Q2", "Q3", "Q4", "H1", "H2", "Annual", "Monthly"]),
        FieldSpec("Start Date", "start_date", "date"),
        FieldSpec("End Date", "end_date", "date"),
        FieldSpec("Target Value", "target_value", numeric=True),
        FieldSpec("Actual Value", "actual_value", numeric=True),
        FieldSpec("Unit", "unit", "combo_other", options=["Count", "PKR", "USD", "%", "Days", "Hours", "Score"]),
        FieldSpec("Weight %", "weight_pct", numeric=True),
        FieldSpec("Achievement %", "achievement_pct", numeric=True),
        FieldSpec("Status", "status", "combo", "On Track", ["Not Started", "On Track", "At Risk", "Off Track", "Completed"]),
        FieldSpec("Review Date", "review_date", "date"),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("kpi_code", "Code", width=110),
        ColumnSpec("kpi_name", "KPI", width=220),
        ColumnSpec("employee_name", "Employee", width=150),
        ColumnSpec("owner_name", "Owner", width=140),
        ColumnSpec("department", "Department", width=120),
        ColumnSpec("period", "Period", width=90),
        ColumnSpec("target_value", "Target", width=100),
        ColumnSpec("actual_value", "Actual", width=100),
        ColumnSpec("achievement_pct", "Achievement", pct, 105),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("review_date", "Review", d, 100),
    ]
    insert = [
        "kpi_code", "kpi_name", "employee_name", "owner_name", "department",
        "category", "period", "start_date", "end_date", "target_value",
        "actual_value", "unit", "weight_pct", "achievement_pct", "status",
        "review_date", "notes", "created_by", "created_at",
    ]
    update = [
        "kpi_code", "kpi_name", "employee_name", "owner_name", "department",
        "category", "period", "start_date", "end_date", "target_value",
        "actual_value", "unit", "weight_pct", "achievement_pct", "status",
        "review_date", "notes",
    ]
    return TableSpec("SF KPIs", "sf_kpis", cols, fields, insert, update, permission="successfactors")


def _sf_learning_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Course Title *", "course_title", required=True),
        FieldSpec("Course Code", "course_code"),
        FieldSpec("Category", "category", "combo_other", options=["Compliance", "Technical", "Soft Skills", "Leadership", "Safety", "Induction"]),
        FieldSpec("Instructor", "instructor"),
        FieldSpec("Assigned Date", "assigned_date", "date"),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Completion Date", "completion_date", "date"),
        FieldSpec("Status", "status", "combo", "Assigned", ["Assigned", "In Progress", "Completed", "Overdue", "Waived"]),
        FieldSpec("Score", "score", numeric=True),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=160),
        ColumnSpec("course_title", "Course", width=220),
        ColumnSpec("category", "Category", width=120),
        ColumnSpec("assigned_date", "Assigned", d, 100),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("completion_date", "Completed", d, 100),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("score", "Score", width=80),
    ]
    insert = [
        "employee_name", "course_title", "course_code", "category", "instructor",
        "assigned_date", "due_date", "completion_date", "status", "score", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "course_title", "course_code", "category", "instructor",
        "assigned_date", "due_date", "completion_date", "status", "score", "notes",
    ]
    return TableSpec("SF Learning (LMS)", "sf_learning", cols, fields, insert, update, permission="successfactors")


def _sf_compensation_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Base Salary *", "base_salary", numeric=True, required=True),
        FieldSpec("Bonus", "bonus", numeric=True),
        FieldSpec("Allowances", "allowances", numeric=True),
        FieldSpec("Total Compensation", "total_compensation", numeric=True),
        FieldSpec("Currency", "currency", "combo", "PKR", ["PKR", "USD", "AED", "GBP"]),
        FieldSpec("Effective Date", "effective_date", "date"),
        FieldSpec("Review Cycle", "review_cycle", "combo_other", options=["Annual", "Semi-Annual", "Quarterly"]),
        FieldSpec("Approved By", "approved_by"),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Pending", "Expired"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("base_salary", "Base Salary", m, 130),
        ColumnSpec("bonus", "Bonus", m, 110),
        ColumnSpec("allowances", "Allowances", m, 110),
        ColumnSpec("total_compensation", "Total", m, 130),
        ColumnSpec("currency", "Currency", width=80),
        ColumnSpec("effective_date", "Effective", d, 100),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = [
        "employee_name", "base_salary", "bonus", "allowances", "total_compensation",
        "currency", "effective_date", "review_cycle", "approved_by", "status", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "base_salary", "bonus", "allowances", "total_compensation",
        "currency", "effective_date", "review_cycle", "approved_by", "status", "notes",
    ]
    return TableSpec("SF Compensation", "sf_compensation", cols, fields, insert, update, permission="successfactors")


def _sf_onboarding_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Employee Name *", "employee_name", required=True),
        FieldSpec("Task Title *", "task_title", required=True),
        FieldSpec("Category", "task_category", "combo_other", options=["Documentation", "IT Setup", "Training", "Orientation", "Compliance", "Access"]),
        FieldSpec("Assigned To", "assigned_to"),
        FieldSpec("Due Date", "due_date", "date"),
        FieldSpec("Completion Date", "completion_date", "date"),
        FieldSpec("Status", "status", "combo", "Pending", ["Pending", "In Progress", "Completed", "Waived"]),
        FieldSpec("Priority", "priority", "combo", "Medium", ["Low", "Medium", "High", "Critical"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("employee_name", "Employee", width=170),
        ColumnSpec("task_title", "Task", width=220),
        ColumnSpec("task_category", "Category", width=130),
        ColumnSpec("assigned_to", "Assigned To", width=130),
        ColumnSpec("due_date", "Due Date", d, 100),
        ColumnSpec("status", "Status", width=110),
        ColumnSpec("priority", "Priority", width=90),
    ]
    insert = [
        "employee_name", "task_title", "task_category", "assigned_to",
        "due_date", "completion_date", "status", "priority", "notes",
        "created_by", "created_at",
    ]
    update = [
        "employee_name", "task_title", "task_category", "assigned_to",
        "due_date", "completion_date", "status", "priority", "notes",
    ]
    return TableSpec("SF Onboarding", "sf_onboarding", cols, fields, insert, update, permission="successfactors")


def _sf_positions_spec() -> TableSpec:
    fields = [
        FieldSpec("Position Code", "position_code", "entry", lambda: gen_id("POS")),
        FieldSpec("Position Title *", "position_title", required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Operations", "HR", "Finance", "IT", "Admin"]),
        FieldSpec("Location", "location", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Max Headcount", "headcount_max", numeric=True),
        FieldSpec("Current Headcount", "headcount_current", numeric=True),
        FieldSpec("Reports To", "reports_to"),
        FieldSpec("Status", "status", "combo", "Open", ["Open", "Filled", "Frozen", "Closed"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("position_code", "Code", width=110),
        ColumnSpec("position_title", "Title", width=200),
        ColumnSpec("department", "Department", width=130),
        ColumnSpec("location", "Location", width=140),
        ColumnSpec("headcount_max", "Max HC", width=80),
        ColumnSpec("headcount_current", "Current HC", width=90),
        ColumnSpec("reports_to", "Reports To", width=140),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = [
        "position_code", "position_title", "department", "location",
        "headcount_max", "headcount_current", "reports_to", "status",
        "created_by", "created_at",
    ]
    update = [
        "position_code", "position_title", "department", "location",
        "headcount_max", "headcount_current", "reports_to", "status",
    ]
    return TableSpec("SF Positions", "sf_positions", cols, fields, insert, update, permission="successfactors")


class SuccessFactorsModule(QWidget):
    def __init__(self, main: "ModernCRMWindow"):
        super().__init__()
        self.main = main
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("SAP SuccessFactors")
        heading.setObjectName("PageTitle")
        layout.addWidget(heading)

        tabs = QTabWidget()
        self.sf_dashboard = SFDashboardPage(main)
        self.employee_central = SFEmployeeCentralPage(main, _sf_employee_spec())
        self.recruiting = SFRecruitingPage(main, _sf_recruiting_spec())
        self.performance = SFPerformancePage(main, _sf_performance_spec())
        self.must_win_battles = SFMustWinBattlesPage(main, _sf_must_win_battles_spec())
        self.kpis = SFKPIsPage(main, _sf_kpis_spec())
        self.learning = SFLearningPage(main, _sf_learning_spec())
        self.compensation = SFCompensationPage(main, _sf_compensation_spec())
        self.onboarding = SFOnboardingPage(main, _sf_onboarding_spec())
        self.positions = SFPositionsPage(main, _sf_positions_spec())

        tabs.addTab(self.sf_dashboard, "Overview")
        tabs.addTab(self.employee_central, "Employee Central")
        tabs.addTab(self.recruiting, "Recruiting")
        tabs.addTab(self.performance, "Performance & Goals")
        tabs.addTab(self.must_win_battles, "Must Win Battles")
        tabs.addTab(self.kpis, "KPIs")
        tabs.addTab(self.learning, "Learning (LMS)")
        tabs.addTab(self.compensation, "Compensation")
        tabs.addTab(self.onboarding, "Onboarding")
        tabs.addTab(self.positions, "Positions")
        layout.addWidget(tabs, 1)

    def refresh(self) -> None:
        self.sf_dashboard.refresh()
        self.employee_central.refresh()
        self.recruiting.refresh()
        self.performance.refresh()
        self.must_win_battles.refresh()
        self.kpis.refresh()
        self.learning.refresh()
        self.compensation.refresh()
        self.onboarding.refresh()
        self.positions.refresh()


# Workflow Engine module

def _wf_workflows_spec() -> TableSpec:
    fields = [
        FieldSpec("Workflow Name *", "workflow_name", required=True),
        FieldSpec("Type", "workflow_type", "combo_other", options=["Approval", "Notification", "Automation", "Escalation", "Onboarding", "Custom"]),
        FieldSpec("Trigger Event", "trigger_event", "combo_other", options=["Manual", "Record Create", "Record Edit", "Record Delete", "Status Change", "Scheduled", "API Call"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Draft", "Paused", "Archived"]),
        FieldSpec("Version", "version", numeric=True),
        FieldSpec("Description", "description", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Name", width=220),
        ColumnSpec("workflow_type", "Type", width=130),
        ColumnSpec("trigger_event", "Trigger", width=150),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("version", "Version", width=70),
        ColumnSpec("description", "Description", width=240),
    ]
    insert = ["workflow_name", "workflow_type", "trigger_event", "status", "version", "description", "created_by", "created_at"]
    update = ["workflow_name", "workflow_type", "trigger_event", "status", "version", "description"]
    return TableSpec("Workflow Definitions", "wf_workflows", cols, fields, insert, update, permission="workflow")


def _wf_steps_spec() -> TableSpec:
    fields = [
        FieldSpec("Workflow ID", "workflow_id", numeric=True),
        FieldSpec("Step Name *", "step_name", required=True),
        FieldSpec("Step Order", "step_order", numeric=True),
        FieldSpec("Step Type", "step_type", "combo_other", options=["Approval", "Notification", "Auto-Action", "Conditional", "Wait", "End"]),
        FieldSpec("Assignee Role", "assignee_role", "combo_other", options=list(ROLE_PERMISSIONS.keys())),
        FieldSpec("Assignee Name", "assignee_name"),
        FieldSpec("SLA (Hours)", "sla_hours", numeric=True),
        FieldSpec("On Approve", "action_on_approve", "combo_other", options=["Next Step", "Close", "Notify", "Auto-Update", "Escalate"]),
        FieldSpec("On Reject", "action_on_reject", "combo_other", options=["Stop", "Return to Requester", "Notify", "Escalate"]),
        FieldSpec("Conditional", "is_conditional", "combo", "0", ["0", "1"]),
        FieldSpec("Condition Field", "condition_field"),
        FieldSpec("Condition Value", "condition_value"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_id", "WF ID", width=70),
        ColumnSpec("step_order", "Order", width=70),
        ColumnSpec("step_name", "Step", width=200),
        ColumnSpec("step_type", "Type", width=120),
        ColumnSpec("assignee_role", "Role", width=120),
        ColumnSpec("assignee_name", "Assignee", width=140),
        ColumnSpec("sla_hours", "SLA (hrs)", width=80),
        ColumnSpec("action_on_approve", "On Approve", width=120),
        ColumnSpec("action_on_reject", "On Reject", width=120),
    ]
    insert = [
        "workflow_id", "step_order", "step_name", "step_type", "assignee_role",
        "assignee_name", "sla_hours", "action_on_approve", "action_on_reject",
        "is_conditional", "condition_field", "condition_value", "created_by", "created_at",
    ]
    update = [
        "workflow_id", "step_order", "step_name", "step_type", "assignee_role",
        "assignee_name", "sla_hours", "action_on_approve", "action_on_reject",
        "is_conditional", "condition_field", "condition_value",
    ]
    return TableSpec("Workflow Steps", "wf_workflow_steps", cols, fields, insert, update, permission="workflow")


def _wf_instances_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("reference_table", "Source Table", width=140),
        ColumnSpec("reference_id", "Record ID", width=80),
        ColumnSpec("initiated_by", "Started By", width=130),
        ColumnSpec("initiated_at", "Started At", d, 110),
        ColumnSpec("current_step", "Step", width=70),
        ColumnSpec("current_assignee", "Assignee", width=130),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("due_at", "Due", d, 100),
        ColumnSpec("priority", "Priority", width=90),
    ]
    return TableSpec("Running Instances", "wf_instances", cols, [], [], [], permission="workflow")


def _wf_tasks_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Workflow Name", "workflow_name"),
        FieldSpec("Step Name", "step_name"),
        FieldSpec("Assigned To *", "assigned_to", required=True),
        FieldSpec("Assigned At", "assigned_at", "date"),
        FieldSpec("Due Date", "due_at", "date"),
        FieldSpec("Status", "status", "combo", "Pending", ["Pending", "Completed", "Rejected", "Cancelled"]),
        FieldSpec("Priority", "priority", "combo", "Normal", ["Low", "Normal", "High", "Critical"]),
        FieldSpec("Reference Table", "reference_table", "combo_other", options=["rent_requirements", "rent_availability", "sale_requirements", "sale_availability", "sf_employees", "sf_recruiting", "sf_onboarding", "clients"]),
        FieldSpec("Reference ID", "reference_id", numeric=True),
        FieldSpec("Comments", "comments", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("step_name", "Step", width=160),
        ColumnSpec("assigned_to", "Assigned To", width=140),
        ColumnSpec("assigned_at", "Assigned", d, 100),
        ColumnSpec("due_at", "Due", d, 100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("priority", "Priority", width=90),
        ColumnSpec("action_taken", "Action", width=110),
        ColumnSpec("reference_table", "Source", width=130),
    ]
    insert = [
        "instance_id", "workflow_name", "step_name", "assigned_to", "assigned_at",
        "due_at", "priority", "reference_table", "reference_id", "comments", "status",
    ]
    update = [
        "workflow_name", "step_name", "assigned_to", "due_at", "priority",
        "reference_table", "reference_id", "comments", "status", "action_taken", "completed_at",
    ]
    return TableSpec("Tasks", "wf_tasks", cols, fields, insert, update, permission="workflow")


def _wf_approvals_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("workflow_name", "Workflow", width=180),
        ColumnSpec("approval_type", "Type", width=120),
        ColumnSpec("requested_by", "Requested By", width=130),
        ColumnSpec("requested_at", "Requested At", d, 110),
        ColumnSpec("reviewed_by", "Reviewed By", width=130),
        ColumnSpec("reviewed_at", "Reviewed At", d, 110),
        ColumnSpec("decision", "Decision", width=100),
        ColumnSpec("status", "Status", width=100),
        ColumnSpec("comments", "Comments", width=200),
    ]
    return TableSpec("Approvals", "wf_approvals", cols, [], [], [], permission="workflow")


def _wf_notifications_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    fields = [
        FieldSpec("Recipient *", "recipient", required=True),
        FieldSpec("Subject *", "subject", required=True),
        FieldSpec("Body", "body", "text"),
        FieldSpec("Channel", "channel", "combo", "In-App", ["In-App", "Email", "SMS", "WhatsApp"]),
        FieldSpec("Status", "status", "combo", "Unread", ["Unread", "Read", "Sent", "Failed"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("recipient", "Recipient", width=150),
        ColumnSpec("subject", "Subject", width=220),
        ColumnSpec("channel", "Channel", width=100),
        ColumnSpec("sent_at", "Sent At", d, 110),
        ColumnSpec("status", "Status", width=90),
    ]
    insert = ["recipient", "subject", "body", "channel", "status", "created_at"]
    update = ["recipient", "subject", "body", "channel", "status", "read_at"]
    return TableSpec("Notifications", "wf_notifications", cols, fields, insert, update, permission="workflow")


def _wf_sla_spec() -> TableSpec:
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("instance_id", "Instance", width=90),
        ColumnSpec("task_id", "Task", width=80),
        ColumnSpec("sla_target_hours", "SLA Target(h)", width=110),
        ColumnSpec("actual_hours", "Actual (h)", width=100),
        ColumnSpec("breached", "Breached", width=90),
        ColumnSpec("logged_at", "Logged At", None, 110),
    ]
    return TableSpec("SLA Log", "wf_sla_log", cols, [], [], [], permission="workflow")


def _wf_audit_spec() -> TableSpec:
    d = lambda value, _symbol: format_date_display(value)
    cols = [
        ColumnSpec("id", "ID", width=60),
        ColumnSpec("action", "Action", width=160),
        ColumnSpec("performed_by", "By", width=130),
        ColumnSpec("performed_at", "At", d, 110),
        ColumnSpec("reference_table", "Table", width=140),
        ColumnSpec("reference_id", "Record ID", width=80),
        ColumnSpec("old_value", "Old Value", width=180),
        ColumnSpec("new_value", "New Value", width=180),
    ]
    return TableSpec("Audit Trail", "wf_audit_log", cols, [], [], [], permission="workflow")


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