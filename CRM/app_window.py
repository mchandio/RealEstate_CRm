"""ModernCRMWindow - Main application window."""
from __future__ import annotations
from PySide6.QtCore import QDate, Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QKeySequence, QPageLayout, QPageSize, QPainter, QPen, QPixmap, QShortcut, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QStackedWidget, QTabWidget, QFrame, QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QDialog, QHeaderView, QAbstractItemView, QMessageBox, QSizePolicy, QFileDialog, QProgressBar, QListWidget, QListWidgetItem, QDialogButtonBox
from typing import Any, Callable
from datetime import datetime
import os
import subprocess
import sys

from crm_core import DB_PATH
from crm_core.reports import ReportService
from crm_core.intelligence import IntelligenceService
from crm_core.constants import normalize_availability_status, has_permission, CLOSED_AVAILABILITY_ARCHIVES
from CRM.constants import DEAL_TABLES, GLOBAL_SEARCH_SOURCE_LABELS, GLOBAL_SEARCH_MONEY_COLUMNS, GLOBAL_SEARCH_HIDDEN_COLUMNS, LOCAL_SERVICE_PORT, LAN_WEB_PORT, LAN_WEB_ENABLED, LAN_WEB_HOST, PY_DATE_STORAGE_FORMAT, DATE_STORAGE_FORMAT, DATE_DISPLAY_FORMAT, SF_TABLES, WF_TABLES, PHASE1_TABLES, READ_ONLY_API_TABLES, PARENT_CHILD_TABLES, LONG_TEXT_COLUMN_KEYS, BACKUP_DIR, OUTPUT_DIR, FIND_SOURCE_PERMISSIONS, GLOBAL_SEARCH_SOURCES, FIND_SOURCE_ORDER, FIND_RESULT_COLUMNS, FIND_ALL_COLUMN_ORDER, FIND_ALL_COLUMN_LABELS, DATE_FORM_KEYS, PHONE_FORM_KEYS, EMAIL_FORM_KEYS, CNIC_FORM_KEYS, PERCENT_FORM_KEYS, DEAL_STAGES, COMMON_AREAS, FACILITY_OPTIONS, FLOOR_OPTIONS, PROPERTY_TYPE_OPTIONS, MEASUREMENT_UNIT_OPTIONS, EXPENSE_CATEGORIES, crm_app_icon, crm_logo_path, is_admin_role
from CRM.utils import money, format_date_display, setting_lines, safe_float, gen_id, quote_identifier, allowed_find_sources
from CRM.modules import DealModule, FinancialModule, EmployeesModule, SuccessFactorsModule, WorkflowModule, ReportsModule, AIInsightsModule, UsersModule, SettingsModule, DataTablePage, PhaseOneDesk
from CRM.models import ColumnSpec, TableSpec, FieldSpec
from CRM.dialogs.login import LoginDialog
from CRM.dialogs.startup import StartupDialog
from CRM.dialogs.search import SearchDialog
from CRM.api import DesktopServer, LanServer, AppContext
from CRM.widgets.dashboard import DashboardWidget
from CRM.modules.property_sync import PropertySyncService
from CRM.modules.report_helpers import (
    build_financial_text,
    generic_report as _generic_report,
    attendance_report as _attendance_report,
    get_report_for_kind,
)

class ModernCRMWindow(QMainWindow):
    def __init__(
        self,
        services: CRMServices,
        current_user: dict,
        startup_progress: Callable[[int, str], None] | None = None,
    ):
        super().__init__()
        self.services = services
        self.current_user = current_user
        self._startup_progress = startup_progress
        self.role = current_user.get("role", "Staff")
        self.pages: dict[str, QWidget] = {}
        self.last_report: ReportResult | None = None
        self._desktop_server = DesktopServer()
        self._lan_server = LanServer()
        self._property_sync = PropertySyncService(self)
        self._dashboard_widget: DashboardWidget | None = None
        self.local_ip = self._get_local_ip()
        self.local_service_url = f"http://{self.local_ip}:{LOCAL_SERVICE_PORT}"
        self.browser_service_url = f"http://{self.local_ip}:{LAN_WEB_PORT}"
        self._report_startup(55, "Reading company settings")
        self.reload_settings()
        self.setWindowTitle(f"Real Estate CRM - {current_user.get('full_name') or current_user.get('username')} ({self.role})")
        self.setWindowIcon(crm_app_icon())
        self.resize(1360, 840)
        self.setMinimumSize(1000, 660)
        self._report_startup(62, "Preparing CRM tables")
        self._build_specs()
        self._report_startup(68, "Building workspace")
        self._build_ui()
        self._report_startup(88, "Starting desktop API")
        self._desktop_server.start(self)
        self._report_startup(90, "Starting browser server")
        self._lan_server.start(self._set_browser_server_status)
        self._report_startup(94, "Syncing clients")
        synced_contacts = self.sync_all_deal_contacts()
        self._report_startup(96, "Refreshing dashboard")
        self.refresh_dashboard()
        self.update_status_bar(f"CRM data refreshed; synced {synced_contacts} deal records")

    def _report_startup(self, value: int, message: str) -> None:
        if self._startup_progress:
            self._startup_progress(value, message)

    def reload_settings(self) -> None:
        self.company_name = self.services.settings_get("company_name", "Real Estate Management")
        self.currency_symbol = self.services.settings_get("currency_symbol", "Rs.")
        self.theme_name = self.services.settings_get("phase1_theme", "Light")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_APP_STYLE if self.theme_name == "Dark" else APP_STYLE)
        self.report_service = ReportService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)
        self.intelligence_service = IntelligenceService(DB_PATH, currency_symbol=self.currency_symbol, company_name=self.company_name)

    def reload_dynamic_specs(self) -> None:
        self._build_specs()

        phase_page = self.pages.get("phase1")
        if isinstance(phase_page, PhaseOneDesk):
            phase_page.reload_specs()

        rent_page = self.pages.get("rent")
        if isinstance(rent_page, DealModule):
            rent_page.requirement_spec = self.specs["rent_req"]
            rent_page.availability_spec = self.specs["rent_av"]
            rent_page.closed_spec = self.specs["rented"]
            rent_page.requirements.spec = self.specs["rent_req"]
            rent_page.availability.spec = self.specs["rent_av"]
            if rent_page.closed:
                rent_page.closed.spec = self.specs["rented"]

        sale_page = self.pages.get("sale")
        if isinstance(sale_page, DealModule):
            sale_page.requirement_spec = self.specs["sale_req"]
            sale_page.availability_spec = self.specs["sale_av"]
            sale_page.closed_spec = self.specs["sold"]
            sale_page.requirements.spec = self.specs["sale_req"]
            sale_page.availability.spec = self.specs["sale_av"]
            if sale_page.closed:
                sale_page.closed.spec = self.specs["sold"]

        financials = self.pages.get("financials")
        if isinstance(financials, FinancialModule):
            financials.income.spec = self.specs["income"]
            financials.expenses.spec = self.specs["expenses"]

    def _build_specs(self) -> None:
        m = lambda value, symbol: money(value, symbol)
        d = lambda value, _symbol: format_date_display(value)
        option_sets = {
            "areas": setting_lines(self.services, "phase1_areas", COMMON_AREAS),
            "facilities": setting_lines(self.services, "phase1_facilities", FACILITY_OPTIONS),
            "floors": setting_lines(self.services, "phase1_floors", FLOOR_OPTIONS),
            "property_types": setting_lines(self.services, "phase1_property_types", PROPERTY_TYPE_OPTIONS),
            "measurement_units": setting_lines(self.services, "phase1_measurement_units", MEASUREMENT_UNIT_OPTIONS),
        }
        self.specs = {
            "rent_req": TableSpec(
                "Rent Requirements",
                "rent_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Required/Needed", width=180),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget", option_sets),
                deal_insert_columns("client_name", "property_requires", "budget"),
                deal_update_columns("client_name", "property_requires", "budget"),
                permission="rent",
                deal_table=True,
            ),
            "rent_av": TableSpec(
                "Rent Availability",
                "rent_availability",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("status", "Availability", width=120),
                    ColumnSpec("property_availability", "Property Available", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("monthly_rent", "Rent", m, 115), ColumnSpec("deposit", "Deposit", m, 115),
                    ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "monthly_rent", option_sets),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                owner_broker_availability_update_columns("owner_name", "property_availability", "monthly_rent") + ["deposit", "maintenance_charge"],
                deal_table=True,
            ),
            "rented": TableSpec(
                "Rented Properties",
                "rented_properties",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("closed_at", "Rented Date", d, 110),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Rented", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("monthly_rent", "Rent", m, 115), ColumnSpec("deposit", "Deposit", m, 115),
                    ColumnSpec("maintenance_charge", "Maintenance", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("building_name", "Building Name", width=160),
                    ColumnSpec("closed_status", "Status", width=110), ColumnSpec("archived_by", "Archived By", width=120),
                    ColumnSpec("source_id", "Source ID", width=90),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                [],
                [],
                [],
                permission="rent",
                order_by="closed_at DESC, id DESC",
            ),
            "sale_req": TableSpec(
                "Sale Requirements",
                "sale_requirements",
                [
                    ColumnSpec("id", "Sr No.", width=70), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("client_name", "Name", width=150),
                    ColumnSpec("client_status", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact No.", width=120),
                    ColumnSpec("property_requires", "Property Required/Needed", width=180),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("budget", "Budget", m, 115), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                deal_fields("client_name", "property_requires", "budget", option_sets),
                deal_insert_columns("client_name", "property_requires", "budget"),
                deal_update_columns("client_name", "property_requires", "budget"),
                permission="sale",
                deal_table=True,
            ),
            "sale_av": TableSpec(
                "Sale Availability",
                "sale_availability",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("date", "Date", d, 96),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("status", "Availability", width=120),
                    ColumnSpec("property_availability", "Property Available", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("demand", "Demand", m, 120), ColumnSpec("floor", "Floor", width=90),
                    ColumnSpec("location", "Location", width=150), ColumnSpec("facilities", "Facilities", width=220),
                    ColumnSpec("workflow_stage", "Workflow", width=120),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                owner_broker_availability_fields("owner_name", "property_availability", "demand", option_sets),
                owner_broker_availability_insert_columns("owner_name", "property_availability", "demand"),
                owner_broker_availability_update_columns("owner_name", "property_availability", "demand"),
                permission="sale",
                deal_table=True,
            ),
            "sold": TableSpec(
                "Sold Properties",
                "sold_properties",
                [
                    ColumnSpec("id", "ID", width=64), ColumnSpec("closed_at", "Sold Date", d, 110),
                    ColumnSpec("owner_name", "Name", width=150),
                    ColumnSpec("client_broker", "Owner/Broker", width=120),
                    ColumnSpec("contact", "Contact", width=120),
                    ColumnSpec("property_availability", "Property Sold", width=170),
                    ColumnSpec("size", "Rooms", width=110), ColumnSpec("measurement", "Measurement", width=120),
                    ColumnSpec("measurement_unit", "Size", width=90),
                    ColumnSpec("demand", "Demand", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
                    ColumnSpec("floor", "Floor", width=90), ColumnSpec("location", "Location", width=150),
                    ColumnSpec("building_name", "Building Name", width=160),
                    ColumnSpec("closed_status", "Status", width=110), ColumnSpec("archived_by", "Archived By", width=120),
                    ColumnSpec("source_id", "Source ID", width=90),
                    ColumnSpec("remarks", "Remarks", width=240),
                ],
                [],
                [],
                [],
                permission="sale",
                order_by="closed_at DESC, id DESC",
            ),
            "properties": property_spec(),
            "clients": client_spec(),
            "broker_contacts": broker_contact_spec(),
            "income": income_spec(),
            "expenses": expense_spec(self.services.expense_categories()),
            "employees": employee_spec(),
            "salary": salary_spec(),
        }

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 12, 12, 12)
        side.setSpacing(10)

        brand_card = QFrame()
        brand_card.setObjectName("BrandCard")
        brand_layout = QHBoxLayout(brand_card)
        brand_layout.setContentsMargins(10, 10, 10, 10)
        brand_layout.setSpacing(8)
        logo = QLabel()
        logo.setObjectName("LogoImage")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(44, 44)
        logo_pixmap = QPixmap(str(crm_logo_path()))
        if logo_pixmap.isNull():
            logo.setObjectName("LogoBadge")
            logo.setText("RE")
        else:
            logo.setPixmap(
                logo_pixmap.scaled(
                    44,
                    44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        brand_layout.addWidget(logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand = QLabel("Real Estate CRM")
        brand.setObjectName("Brand")
        brand_subtitle = QLabel("Property operations")
        brand_subtitle.setObjectName("SidebarSubtle")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_subtitle)
        brand_layout.addLayout(brand_text, 1)
        side.addWidget(brand_card)

        user_card = QFrame()
        user_card.setObjectName("UserCard")
        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(14, 12, 14, 12)
        user_layout.setSpacing(4)
        user_name = QLabel(str(self.current_user.get("full_name") or self.current_user.get("username") or "User"))
        user_name.setObjectName("SidebarUserName")
        user_role = QLabel(str(self.role))
        user_role.setObjectName("RolePill")
        user_layout.addWidget(user_name)
        user_layout.addWidget(user_role, alignment=Qt.AlignLeft)
        side.addWidget(user_card)

        nav_shell = QFrame()
        nav_shell.setObjectName("NavShell")
        nav_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.nav_shell = nav_shell
        self.nav_layout = QVBoxLayout(nav_shell)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        self.nav_buttons: dict[str, NavItem] = {}
        self.nav_keys: list[str] = []
        self._nav_section_count = 0

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("SidebarNavScroll")
        self.nav_scroll = nav_scroll
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        nav_scroll.setWidget(nav_shell)
        side.addWidget(nav_scroll, 1)

        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 12, 12, 12)
        footer_layout.setSpacing(8)
        status_row = QHBoxLayout()
        dot = QLabel("")
        dot.setObjectName("StatusDot")
        status_row.addWidget(dot)
        api_status = QLabel("Browser server starting")
        api_status.setObjectName("SidebarStatusText")
        self.sidebar_server_status = api_status
        status_row.addWidget(api_status)
        status_row.addStretch(1)
        footer_layout.addLayout(status_row)
        api_label = QLabel(self.browser_service_url)
        api_label.setObjectName("SidebarSubtle")
        api_label.setWordWrap(True)
        self.sidebar_server_url_label = api_label
        footer_layout.addWidget(api_label)
        logout = QPushButton("Logout")
        logout.setObjectName("SidebarLogout")
        logout.clicked.connect(self.logout)
        footer_layout.addWidget(logout)
        side.addWidget(footer)
        outer.addWidget(sidebar)

        content = QFrame()
        content.setObjectName("Content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 12, 18, 14)
        content_layout.setSpacing(10)

        top = QHBoxLayout()
        self.page_title = QLabel(self.company_name)
        self.page_title.setObjectName("TopTitle")
        search = QPushButton("Find")
        search.clicked.connect(self.open_search)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_all_pages)
        top.addWidget(self.page_title)
        top.addStretch(1)
        top.addWidget(search)
        top.addWidget(refresh)
        content_layout.addLayout(top)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        outer.addWidget(content, 1)
        self._build_pages()
        self._build_menu()
        self._build_status_bar()
        self.setStyleSheet(APP_STYLE)
        self.update_status_bar("Ready")

    def _build_menu(self) -> None:
        self.menuBar().clear()
        self._menus: list[Any] = []

        def menu(label: str) -> Any:
            created = self.menuBar().addMenu(label)
            self._menus.append(created)
            return created

        def action(label: str, slot: Callable, shortcut: str | None = None, tip: str | None = None) -> QAction:
            act = QAction(label, self)
            if shortcut:
                act.setShortcut(shortcut)
            if tip:
                act.setStatusTip(tip)
            act.triggered.connect(lambda _checked=False, callback=slot: callback())
            return act

        def add_page_action(menu: Any, key: str, shortcut: str | None = None) -> None:
            button = self.nav_buttons.get(key)
            if not button:
                return
            label = button.text_label.text()
            menu.addAction(action(label, lambda page_key=key: self.switch_page(page_key), shortcut, f"Open {label}"))

        def add_separator_if_needed(menu: Any) -> None:
            if not menu.isEmpty():
                menu.addSeparator()

        def add_deal_action(menu: Any, label: str, page_key: str, side: str, shortcut: str | None = None) -> None:
            module = self.pages.get(page_key)
            if not isinstance(module, DealModule):
                return
            spec = module.requirement_spec if side == "requirements" else module.availability_spec
            if self.can_edit(spec.permission):
                menu.addAction(
                    action(
                        label,
                        lambda key=page_key, tab=side: self.add_deal_record(key, tab),
                        shortcut,
                        f"Create {label.lower()}",
                    )
                )

        def add_record_action(menu: Any, label: str, page_key: str, shortcut: str | None = None) -> None:
            page = self.pages.get(page_key)
            if isinstance(page, DataTablePage) and self.can_edit(page.spec.permission):
                menu.addAction(
                    action(
                        label,
                        lambda key=page_key: self.add_table_record(key),
                        shortcut,
                        f"Create {label.lower()}",
                    )
                )

        file_menu = menu("File")
        new_menu = file_menu.addMenu("New")
        self._menus.append(new_menu)

        def new_submenu(label: str) -> Any:
            submenu = new_menu.addMenu(label)
            self._menus.append(submenu)
            return submenu

        rent_new_menu = new_submenu("Rent")
        add_deal_action(rent_new_menu, "Requirement", "rent", "requirements", "Ctrl+N")
        add_deal_action(rent_new_menu, "Availability", "rent", "availability", "Ctrl+Shift+N")
        sale_new_menu = new_submenu("Sale")
        add_deal_action(sale_new_menu, "Requirement", "sale", "requirements", "Ctrl+Alt+N")
        add_deal_action(sale_new_menu, "Availability", "sale", "availability", "Ctrl+Alt+A")
        records_new_menu = new_submenu("Records")
        add_record_action(records_new_menu, "Property", "properties", "Ctrl+Shift+P")
        add_record_action(records_new_menu, "Client", "clients", "Ctrl+Shift+C")
        add_record_action(records_new_menu, "Broker Contact", "broker_contacts", None)
        for submenu in (rent_new_menu, sale_new_menu, records_new_menu):
            if submenu.isEmpty():
                new_menu.removeAction(submenu.menuAction())
        if new_menu.isEmpty():
            file_menu.removeAction(new_menu.menuAction())
        add_separator_if_needed(file_menu)
        file_menu.addAction(action("Export All Tables", self.export_all_tables, "Ctrl+E", "Export every CRM table to CSV files"))
        file_menu.addAction(action("Backup Database", self.backup_database, "Ctrl+B", "Create a SQLite database backup"))
        file_menu.addSeparator()
        file_menu.addAction(action("Restart", self.restart_app, "Ctrl+Shift+R", "Restart the CRM"))
        file_menu.addAction(action("Logout", self.logout, "Ctrl+L", "Return to login"))
        file_menu.addAction(action("Exit", self.close, "Ctrl+Q", "Close the CRM"))

        view_menu = menu("View")
        for index, key in enumerate(self.nav_keys[:9], start=1):
            add_page_action(view_menu, key, f"Ctrl+{index}")
        if len(self.nav_keys) > 9:
            add_page_action(view_menu, self.nav_keys[9], "Ctrl+0")
        view_menu.addSeparator()
        view_menu.addAction(action("Full Screen", self.showFullScreen, "F11", "Switch to full screen"))
        view_menu.addAction(action("Exit Full Screen", self.showNormal, "Shift+F11", "Exit full screen"))

        dealings_menu = menu("Dealings")
        add_page_action(dealings_menu, "rent")
        add_page_action(dealings_menu, "sale")

        records_menu = menu("Records")
        for group in (("properties", "clients", "broker_contacts"), ("financials", "employees"), ("users", "settings")):
            available = [key for key in group if key in self.nav_buttons]
            if not available:
                continue
            add_separator_if_needed(records_menu)
            for key in available:
                add_page_action(records_menu, key)
        if records_menu.isEmpty():
            empty = QAction("No record pages available", self)
            empty.setEnabled(False)
            records_menu.addAction(empty)

        reports_menu = menu("Reports")
        reports_menu.addAction(action("Rent Report", lambda: self.preview_named_report("rent"), "Ctrl+Shift+1", "Preview rent report"))
        reports_menu.addAction(action("Sale Report", lambda: self.preview_named_report("sale"), "Ctrl+Shift+2", "Preview sale report"))
        reports_menu.addAction(action("Combined Report", lambda: self.preview_named_report("both"), "Ctrl+Shift+3", "Preview combined report"))
        add_separator_if_needed(reports_menu)
        for report_key, label in (
            ("properties", "Property Report"),
            ("clients", "Client Report"),
        ):
            reports_menu.addAction(action(label, lambda key=report_key: self.preview_named_report(key), None, f"Preview {label.lower()}"))
        operations_report_added = False
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            if not operations_report_added:
                add_separator_if_needed(reports_menu)
                operations_report_added = True
            reports_menu.addAction(action("Financial Summary", lambda: self.preview_named_report("financial"), "Ctrl+Shift+4", "Preview financial summary"))
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            if not operations_report_added:
                add_separator_if_needed(reports_menu)
                operations_report_added = True
            reports_menu.addAction(action("Employee Report", lambda: self.preview_named_report("employees"), None, "Preview employee report"))
            reports_menu.addAction(action("Attendance Report", lambda: self.preview_named_report("attendance"), None, "Preview attendance report"))

        if "successfactors" in self.nav_buttons:
            sf_menu = menu("SuccessFactors")
            add_page_action(sf_menu, "successfactors")
            sf_menu.addSeparator()
            for label, tab_hint in [
                ("Employee Central", "Employee Central"),
                ("Recruiting", "Recruiting"),
                ("Performance", "Performance & Goals"),
                ("Must Win Battles", "Must Win Battles"),
                ("KPIs", "KPIs"),
                ("Learning (LMS)", "Learning (LMS)"),
                ("Compensation", "Compensation"),
                ("Onboarding", "Onboarding"),
                ("Positions", "Positions"),
            ]:
                sf_menu.addAction(
                    action(
                        label,
                        lambda hint=tab_hint: (
                            self.switch_page("successfactors"),
                            self.update_status_bar(f"SuccessFactors -> {hint}"),
                        ),
                    )
                )

        if "workflow" in self.nav_buttons:
            wf_menu = menu("Workflow")
            add_page_action(wf_menu, "workflow")
            wf_menu.addSeparator()
            for label in [
                "Workflow Definitions", "Workflow Steps",
                "Running Instances", "Tasks",
                "Approvals", "Notifications", "SLA Log", "Audit Trail",
            ]:
                wf_menu.addAction(
                    action(
                        label,
                        lambda lbl=label: (
                            self.switch_page("workflow"),
                            self.update_status_bar(f"Workflow -> {lbl}"),
                        ),
                    )
                )

        tools_menu = menu("Tools")
        tools_menu.addAction(action("Find", self.open_search, "Ctrl+F", "Find records across rent and sale dealings"))
        tools_menu.addAction(action("Refresh", self.refresh_all_pages, "F5", "Reload CRM data"))
        tools_menu.addSeparator()
        tools_menu.addAction(action("Ecosystem Health", self.show_ecosystem_health, None, "Audit Desktop, Web, database, settings, and backups"))
        tools_menu.addAction(action("Server Health", self.show_api_health, "Ctrl+H", "Show LAN browser server details"))

        help_menu = menu("Help")
        help_menu.addAction(action("User Guide", self.show_user_guide, "F1", "Open the user guide"))
        help_menu.addAction(action("Roles && Permissions", self.show_roles_info, None, "Show role permissions"))
        help_menu.addSeparator()
        help_menu.addAction(action("Developer Info", self.show_developer_info, None, "Show developer information"))
        help_menu.addAction(action("About", self.show_about, None, "About this CRM"))

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setObjectName("AppStatusBar")
        bar.setSizeGripEnabled(True)
        self.status_page_label = QLabel()
        self.status_user_label = QLabel()
        self.status_counts_label = QLabel()
        self.status_db_label = QLabel()
        self.status_api_label = QLabel()
        for label in (
            self.status_page_label,
            self.status_user_label,
            self.status_counts_label,
            self.status_db_label,
            self.status_api_label,
        ):
            label.setObjectName("StatusBarLabel")
        bar.addPermanentWidget(self.status_page_label)
        bar.addPermanentWidget(self.status_user_label)
        bar.addPermanentWidget(self.status_counts_label, 1)
        bar.addPermanentWidget(self.status_db_label)
        bar.addPermanentWidget(self.status_api_label)

    def update_status_bar(self, message: str | None = None) -> None:
        if message:
            self.statusBar().showMessage(message, 4500)
        if not hasattr(self, "status_page_label"):
            return
        current = self.stack.currentWidget() if hasattr(self, "stack") else None
        current_key = next((key for key, widget in self.pages.items() if widget is current), "")
        current_label = self.nav_buttons[current_key].text_label.text() if current_key in self.nav_buttons else "Ready"
        self.status_page_label.setText(f"Page: {current_label}")
        username = self.current_user.get("full_name") or self.current_user.get("username") or "User"
        self.status_user_label.setText(f"User: {username} ({self.role})")
        try:
            counts = [
                f"Rent Req: {self.count('rent_requirements')}",
                f"Rent Av: {self.count('rent_availability')}",
                f"Sale Req: {self.count('sale_requirements')}",
                f"Sale Av: {self.count('sale_availability')}",
            ]
            self.status_counts_label.setText(" | ".join(counts))
        except Exception:
            self.status_counts_label.setText("Counts unavailable")
        try:
            size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
            self.status_db_label.setText(f"DB: {size_mb:.1f} MB")
        except Exception:
            self.status_db_label.setText("DB: -")
        self.status_api_label.setText(f"Web: {self.local_ip}:{LAN_WEB_PORT}")

    def add_deal_record(self, page_key: str, side: str) -> None:
        module = self.pages.get(page_key)
        if not isinstance(module, DealModule):
            QMessageBox.information(self, "Unavailable", "That dealings page is not available for this user.")
            return
        self.switch_page(page_key)
        table_page = module.requirements if side == "requirements" else module.availability
        if not self.can_edit(table_page.spec.permission):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to add this record.")
            return
        table_page.add_record()
        self.update_status_bar(f"{table_page.spec.title} ready")

    def add_table_record(self, page_key: str) -> None:
        page = self.pages.get(page_key)
        if not isinstance(page, DataTablePage):
            QMessageBox.information(self, "Unavailable", "That record page is not available.")
            return
        if not self.can_edit(page.spec.permission):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to add this record.")
            return
        self.switch_page(page_key)
        page.add_record()
        self.update_status_bar(f"{page.spec.title} ready")

    def _get_local_ip(self) -> str:
        """Get the local IP address for network access."""
        from CRM.api.desktop_server import get_local_ip
        return get_local_ip()

    def is_staff_restricted(self) -> bool:
        username = str(self.current_user.get("username", "")).strip().lower()
        role = str(self.role or "").strip().lower()
        return role == "staff" or username in {"staff", "staf"}

    def find_sources(self) -> list[tuple[str, str]]:
        return allowed_find_sources(self.role, staff_restricted=self.is_staff_restricted())

    def api_allowed_tables(self) -> set[str]:
        staff_tables = set(DEAL_TABLES)
        all_tables = {
            "rent_requirements", "rent_availability",
            "sale_requirements", "sale_availability",
            "income_transactions", "expense_transactions",
            "clients", "broker_contacts", "properties", "employees", "attendance", "salary_payments",
        }
        if has_permission(self.role, "successfactors") or has_permission(self.role, "sf_view"):
            all_tables.update(SF_TABLES)
        if has_permission(self.role, "workflow") or has_permission(self.role, "wf_view"):
            all_tables.update(WF_TABLES)
        allowed = set(staff_tables if self.is_staff_restricted() else all_tables)
        if self.is_staff_restricted() and (has_permission(self.role, "workflow") or has_permission(self.role, "wf_view")):
            allowed.update({"wf_instances", "wf_tasks", "wf_approvals", "wf_notifications", "wf_sla_log", "wf_audit_log"})
        return allowed

    def api_can_write_table(self, table: str) -> bool:
        if table in READ_ONLY_API_TABLES:
            return False
        if table in PHASE1_TABLES:
            if table.startswith("rent"):
                return has_permission(self.role, "rent")
            if table.startswith("sale"):
                return has_permission(self.role, "sale")
        if table in SF_TABLES:
            return has_permission(self.role, "successfactors")
        if table in WF_TABLES:
            return has_permission(self.role, "workflow")
        permission_map = {
            "income_transactions": "financial",
            "expense_transactions": "financial",
            "clients": "clients",
            "broker_contacts": "clients",
            "properties": "properties",
            "employees": "employees",
            "attendance": "employees",
            "salary_payments": "employees",
        }
        permission = permission_map.get(table)
        return bool(permission and has_permission(self.role, permission))

    def child_reference_summary(self, table: str, row_id: int) -> list[str]:
        references: list[str] = []
        for child_table, child_column in PARENT_CHILD_TABLES.get(table, ()):
            columns = self.services.table_columns(child_table)
            if child_column not in columns:
                continue
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {quote_identifier(child_table)} WHERE {quote_identifier(child_column)}=?",
                (row_id,),
            )
            count = int(row["count"]) if row else 0
            if count:
                references.append(f"{child_table}: {count}")
        return references

    def can_delete_record(self, table: str, row_id: int) -> tuple[bool, str]:
        references = self.child_reference_summary(table, row_id)
        if references:
            return False, "Cannot delete because related records exist: " + "; ".join(references)
        return True, ""

    def _set_browser_server_status(self, status: str, url: str | None = None) -> None:
        """Update the browser server status in the sidebar."""
        if hasattr(self, "sidebar_server_status"):
            self.sidebar_server_status.setText(status)
        if url is not None and hasattr(self, "sidebar_server_url_label"):
            self.sidebar_server_url_label.setText(url)

    def _nav_abbreviation(self, key: str, label: str) -> str:
        abbreviations = {
            "phase1": "QT",
            "dashboard": "DB",
            "rent": "RN",
            "sale": "SL",
            "properties": "PR",
            "clients": "CL",
            "broker_contacts": "BC",
            "financials": "FI",
            "employees": "EM",
            "reports": "RP",
            "ai": "AI",
            "users": "US",
            "settings": "ST",
            "successfactors": "SF",
            "workflow": "WF",
        }
        return abbreviations.get(key, label[:2].upper())

    def _add_page(self, key: str, label: str, widget: QWidget) -> None:
        self.pages[key] = widget
        self.stack.addWidget(widget)
        button = NavItem(key, label, self._nav_abbreviation(key, label))
        button.clicked.connect(self.switch_page)
        self.nav_buttons[key] = button
        self.nav_keys.append(key)
        self.nav_layout.addWidget(button)

    def _add_nav_section(self, label: str) -> None:
        if self._nav_section_count:
            separator = QFrame()
            separator.setObjectName("NavSeparator")
            separator.setFixedHeight(1)
            self.nav_layout.addWidget(separator)
        section = QLabel(label.upper())
        section.setObjectName("NavSection")
        section.setFixedHeight(24)
        section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.nav_layout.addWidget(section)
        self._nav_section_count += 1

    def _build_pages(self) -> None:
        self._add_nav_section("QT CRM")
        self._report_startup(69, "Loading QT_CRM data desk")
        self._add_page("phase1", "QT_CRM Desk", PhaseOneDesk(self))
        if not self.is_staff_restricted():
            self._add_nav_section("Overview")
            self._report_startup(70, "Loading dashboard")
            self._add_page("dashboard", "Dashboard", self._dashboard_page())
        deal_pages = []
        if has_permission(self.role, "rent") or has_permission(self.role, "rent_view"):
            deal_pages.append("rent")
        if has_permission(self.role, "sale") or has_permission(self.role, "sale_view"):
            deal_pages.append("sale")
        if deal_pages:
            self._add_nav_section("Deal desk")
            if "rent" in deal_pages:
                self._report_startup(74, "Loading rent dealings")
                self._add_page("rent", "Rent Dealings", DealModule(self, "Rent Dealings", self.specs["rent_req"], self.specs["rent_av"], self.specs["rented"], "Rented"))
            if "sale" in deal_pages:
                self._report_startup(78, "Loading sale dealings")
                self._add_page("sale", "Sale Dealings", DealModule(self, "Sale Dealings", self.specs["sale_req"], self.specs["sale_av"], self.specs["sold"], "Sold"))
        record_pages = []
        if has_permission(self.role, "properties"):
            record_pages.append("properties")
        if has_permission(self.role, "clients"):
            record_pages.append("clients")
            record_pages.append("broker_contacts")
        if record_pages:
            self._add_nav_section("Records")
            if "properties" in record_pages:
                self._report_startup(82, "Loading property records")
                self._add_page("properties", "Properties", DataTablePage(self, self.specs["properties"]))
            if "clients" in record_pages:
                self._report_startup(84, "Loading client records")
                self._add_page("clients", "Clients", DataTablePage(self, self.specs["clients"]))
            if "broker_contacts" in record_pages:
                self._report_startup(84, "Loading broker contact records")
                self._add_page("broker_contacts", "Broker Contact List", DataTablePage(self, self.specs["broker_contacts"]))
        operation_keys = []
        if has_permission(self.role, "financial") or has_permission(self.role, "financial_view"):
            operation_keys.append("financials")
        if has_permission(self.role, "employees") or has_permission(self.role, "employees_view"):
            operation_keys.append("employees")
        if has_permission(self.role, "successfactors") or has_permission(self.role, "sf_view"):
            operation_keys.append("successfactors")
        if has_permission(self.role, "workflow") or has_permission(self.role, "wf_view"):
            operation_keys.append("workflow")
        if has_permission(self.role, "reports"):
            operation_keys.append("reports")
        if operation_keys:
            self._add_nav_section("Operations")
        if "financials" in operation_keys:
            self._report_startup(86, "Loading financials")
            self._add_page("financials", "Financials", FinancialModule(self, self.specs["income"], self.specs["expenses"]))
        if "employees" in operation_keys:
            self._report_startup(87, "Loading employees")
            self._add_page("employees", "Employees", EmployeesModule(self, self.specs["employees"], self.specs["salary"]))
        if "successfactors" in operation_keys:
            self._report_startup(89, "Loading SuccessFactors")
            self._add_page("successfactors", "SuccessFactors", SuccessFactorsModule(self))
        if "workflow" in operation_keys:
            self._report_startup(89, "Loading Workflow Engine")
            self._add_page("workflow", "Workflow Engine", WorkflowModule(self))
        if "reports" in operation_keys:
            self._report_startup(88, "Loading reports")
            self._add_page("reports", "Reports", ReportsModule(self))
        if has_permission(self.role, "ai"):
            self._add_nav_section("Intelligence")
            self._report_startup(89, "Loading AI insights")
            self._add_page("ai", "AI Insights", AIInsightsModule(self))
        if self.role in ("Super Admin", "Admin"):
            self._add_nav_section("Admin")
            self._report_startup(89, "Loading user administration")
            self._add_page("users", "Users", UsersModule(self))
        if has_permission(self.role, "settings"):
            self._report_startup(89, "Loading settings")
            self._add_page("settings", "Settings", SettingsModule(self))
        self.nav_layout.addStretch(1)
        self.nav_shell.setMinimumHeight(self.nav_layout.sizeHint().height())
        if self.nav_keys:
            self.switch_page(self.nav_keys[0])

    def _dashboard_page(self) -> QWidget:
        self._dashboard_widget = DashboardWidget(self)
        return self._dashboard_widget

    def _nav_changed(self, row: int) -> None:
        if row >= 0:
            self.stack.setCurrentIndex(row)

    def switch_page(self, key: str) -> None:
        widget = self.pages.get(key)
        if not widget:
            return
        self.stack.setCurrentWidget(widget)
        for nav_key, button in self.nav_buttons.items():
            button.setChecked(nav_key == key)
        self.update_status_bar()

    def can_edit(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    def _owner_broker_type(self, value: Any, default: str) -> str:
        text = str(value or "").strip().lower()
        if text in {"b", "broker"}:
            return "Broker"
        if text in {"o", "owner"}:
            return "Owner"
        return default

    def _deal_client_contacts(self, table: str, row: dict) -> list[dict[str, str]]:
        contacts: list[dict[str, str]] = []
        if table in {"rent_requirements", "sale_requirements"}:
            default_type = "Tenant" if table.startswith("rent") else "Buyer"
            contacts.append({
                "name": str(row.get("client_name") or "").strip(),
                "phone": str(row.get("contact_phone") or row.get("contact") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_status"), default_type),
            })
        elif table in {"rent_availability", "sale_availability"}:
            contacts.append({
                "name": str(row.get("owner_name") or "").strip(),
                "phone": str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_broker"), "Owner"),
            })
        for key in ("broker", "preferred_broker", "posted_by_broker", "posted_by", "client_broker"):
            broker = str(row.get(key) or "").strip()
            if broker and broker.lower() not in {"o", "b", "owner", "broker", "direct", "client"}:
                contacts.append({"name": broker, "phone": "", "email": "", "type": "Broker"})
        return contacts

    def upsert_client_from_deal(self, table: str, row: dict) -> None:
        self._property_sync.upsert_client_from_deal(table, row)

    def _property_match(self, row: dict, title: str, property_type: str) -> dict | None:
        location = str(row.get("location") or "").strip()
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip()
        floor = str(row.get("floor") or row.get("floor_no") or "").strip()
        if owner_contact and location:
            params: list[Any] = [owner_contact, location]
            where = [
                "owner_contact=?",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            if floor:
                floor_where = where + ["LOWER(COALESCE(floor,''))=LOWER(?)"]
                found = self.services.fetch_one(
                    f"SELECT id FROM properties WHERE {' AND '.join(floor_where)} LIMIT 1",
                    tuple(params + [floor]),
                )
                if found:
                    return found
            found = self.services.fetch_one(
                f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1",
                tuple(params),
            )
            if found:
                return found
        if owner_name and location:
            params = [owner_name, location]
            where = [
                "LOWER(COALESCE(owner_name,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if title and location:
            params = [title, location]
            where = [
                "LOWER(COALESCE(title,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if owner_contact and not location:
            return self.services.fetch_one("SELECT id FROM properties WHERE owner_contact=? LIMIT 1", (owner_contact,))
        return None

    def availability_property_status(self, table: str, row: dict) -> str:
        try:
            status = normalize_availability_status(row.get("status"), "Available")
        except ValueError:
            status = str(row.get("status") or "Available").strip()
        stage = str(row.get("workflow_stage") or "").strip()
        if stage == "Pending" and status == "Available":
            return "Pending"
        if table == "rent_availability" and status == "Sold":
            return "Available"
        if table == "sale_availability" and status == "Rented":
            return "Available"
        return status

    def sync_property_from_availability(self, table: str, row: dict, status: str) -> int | None:
        return self._property_sync.sync_property_from_availability(table, row, status)

    def archive_closed_availability(self, table: str, record_id: int, archived_by: str | None = None) -> bool:
        return self._property_sync.archive_closed_availability(table, record_id, archived_by)

    def log_audit(
        self,
        action: str,
        reference_table: str,
        reference_id: int | None,
        old_value: str = "",
        new_value: str = "",
    ) -> None:
        self.services.execute(
            """INSERT INTO wf_audit_log
               (action, performed_by, performed_at,
                reference_table, reference_id, old_value, new_value)
               VALUES (?,?,?,?,?,?,?)""",
            (
                action,
                str(self.current_user.get("username") or "system"),
                datetime.now().isoformat(timespec="seconds"),
                reference_table,
                reference_id,
                old_value,
                new_value,
            ),
        )

    def after_record_saved(self, table: str, row_id: int | None) -> None:
        if row_id:
            self.log_audit("save", table, row_id)
        if table not in DEAL_TABLES or not row_id:
            return
        row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not row:
            return
        self.sync_phase1_aliases(table, row)
        row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,)) or row
        self.upsert_client_from_deal(table, row)
        if table in {"rent_availability", "sale_availability"}:
            self.sync_property_from_availability(table, row, self.availability_property_status(table, row))
            self.archive_closed_availability(table, int(row_id))

    def sync_phase1_aliases(self, table: str, row: dict) -> None:
        self._property_sync.sync_phase1_aliases(table, row)

    def sync_all_deal_contacts(self) -> int:
        return self._property_sync.sync_all_deal_contacts()

    def update_deal_workflow_status(self, table: str, record_id: int, status: str) -> tuple[dict, int | None]:
        columns = self.services.table_columns(table)
        now = datetime.now()
        final_status = status in {"Rented", "Sold"}
        stage = "Pending" if status == "Pending" else "Deal Done" if final_status else "Contacted"
        probability = 60.0 if status == "Pending" else 100.0 if final_status else 25.0
        assignments: list[str] = []
        params: list[Any] = []
        if "workflow_stage" in columns:
            assignments.append("workflow_stage=?")
            params.append(stage)
        if "priority" in columns:
            assignments.append("priority=?")
            params.append("High" if status == "Pending" else "Medium")
        if "deal_probability" in columns:
            assignments.append("deal_probability=?")
            params.append(probability)
        if "last_contacted" in columns:
            assignments.append("last_contacted=?")
            params.append(now.strftime(PY_DATE_STORAGE_FORMAT))
        if "status" in columns and (status == "Pending" or final_status):
            assignments.append("status=?")
            params.append(normalize_availability_status(status))
        if final_status and "closed_at" in columns:
            assignments.append("closed_at=COALESCE(closed_at, ?)")
            params.append(now)
        if assignments:
            params.append(record_id)
            self.services.execute(f"UPDATE {table} SET {', '.join(assignments)} WHERE id=?", tuple(params))
        full = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (record_id,)) or {"id": record_id}
        property_id: int | None = None
        if table in {"rent_availability", "sale_availability"}:
            property_id = self.sync_property_from_availability(table, full, self.availability_property_status(table, full))
            self.archive_closed_availability(table, record_id)
        self.upsert_client_from_deal(table, full)
        return full, property_id

    def mark_records_workflow(self, page: DataTablePage, table: str, status: str) -> None:
        if self.role == "Viewer":
            QMessageBox.warning(self, "Access Denied", "Viewer users cannot change workflow status.")
            return
        if status in {"Rented", "Sold"} and table not in {"rent_availability", "sale_availability"}:
            return
        row = page.require_single_row(f"marking as {status.lower()}")
        if not row:
            return
        ask = QMessageBox.question(self, status, f"Mark {table.replace('_', ' ')} #{row['id']} as {status}?")
        if ask != QMessageBox.Yes:
            return
        _full, property_id = self.update_deal_workflow_status(table, int(row["id"]), status)
        page.refresh()
        module = self.pages.get("rent" if table.startswith("rent") else "sale")
        if isinstance(module, DealModule) and module.closed:
            module.closed.refresh()
        self.refresh_dashboard()
        message = f"Record #{row['id']} marked {status}"
        if property_id:
            message += f" and synced to property #{property_id}"
        QMessageBox.information(self, status, message)
        self.update_status_bar(message)

    def mark_availability_closed(self, page: DataTablePage, table: str, status: str) -> None:
        self.mark_records_workflow(page, table, status)

    def refresh_all_pages(self) -> None:
        self.reload_settings()
        self.reload_dynamic_specs()
        if "dashboard" in self.pages:
            self.refresh_dashboard()
        errors: list[str] = []
        for widget in self.pages.values():
            if hasattr(widget, "refresh"):
                try:
                    widget.refresh()
                except Exception as exc:
                    errors.append(f"{widget.__class__.__name__}: {exc}")
        if errors:
            QMessageBox.warning(
                self,
                "Refresh Issues",
                "Some CRM pages could not refresh:\n\n" + "\n".join(errors[:6]),
            )
            self.update_status_bar("Refresh completed with issues")
        else:
            self.update_status_bar("CRM data refreshed")

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout:
                self._clear_layout(child_layout)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _dashboard_active_where(self, table: str) -> str:
        columns = self.services.table_columns(table)
        clauses = []
        if "is_deleted" in columns:
            clauses.append("COALESCE(is_deleted, 0)=0")
        closed_rule = CLOSED_AVAILABILITY_ARCHIVES.get(table)
        if closed_rule and "status" in columns:
            clauses.append(f"LOWER(COALESCE(status,''))<>LOWER('{closed_rule[0]}')")
        return "WHERE " + " AND ".join(clauses) if clauses else ""

    def _dashboard_count(self, table: str) -> int:
        where = self._dashboard_active_where(table)
        row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table} {where}")
        return int(row["count"]) if row else 0

    def _dashboard_pending_approvals(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.services.table_columns(table)
            if "approval_status" not in columns:
                continue
            where = self._dashboard_active_where(table)
            connector = " AND " if where else "WHERE "
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {where}{connector}approval_status='Pending'"
            )
            total += int(row["count"]) if row else 0
        if self.services.table_columns("pending_approvals"):
            row = self.services.fetch_one("SELECT COUNT(*) AS count FROM pending_approvals WHERE status='Pending'")
            total += int(row["count"]) if row else 0
        return total

    def _dashboard_location_label(self, value: Any) -> str:
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

    def _dashboard_location_buckets(self) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        mapping = (
            ("rent_requirements", "rent_requirements"),
            ("rent_availability", "rent_availability"),
            ("sale_requirements", "sale_requirements"),
            ("sale_availability", "sale_availability"),
        )
        for table, key in mapping:
            where = self._dashboard_active_where(table)
            rows = self.services.fetch_all(
                f"SELECT COALESCE(location, '') AS location, COUNT(*) AS total FROM {table} {where} GROUP BY COALESCE(location, '')"
            )
            for row in rows:
                label = self._dashboard_location_label(row.get("location"))
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

    def _dashboard_client_segments(self, total: int) -> list[dict[str, Any]]:
        if total <= 0:
            return [
                {"label": "Active Searchers", "value": 0, "percent": 0, "color": "#1976d2"},
                {"label": "Long-Term Leads", "value": 0, "percent": 0, "color": "#43a047"},
                {"label": "Past Clients", "value": 0, "percent": 0, "color": "#007c91"},
            ]
        active = self.services.fetch_one(
            """SELECT COUNT(*) AS count FROM clients
               WHERE LOWER(COALESCE(status,''))='active'
                 AND LOWER(COALESCE(client_type,'')) IN ('tenant', 'buyer', 'investor')"""
        )
        long_term = self.services.fetch_one(
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

    def _dashboard_closed_count(self) -> int:
        total = 0
        for table in DEAL_TABLES:
            columns = self.services.table_columns(table)
            clauses = []
            if "workflow_stage" in columns:
                clauses.append("LOWER(COALESCE(workflow_stage,''))='deal done'")
            if "status" in columns:
                clauses.append("LOWER(COALESCE(status,'')) IN ('rented', 'sold')")
            if not clauses:
                continue
            active_where = self._dashboard_active_where(table)
            connector = " AND " if active_where else "WHERE "
            row = self.services.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} {active_where}{connector}({' OR '.join(clauses)})"
            )
            total += int(row["count"]) if row else 0
        for table in ("rented_properties", "sold_properties"):
            if self.services.table_columns(table):
                row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                total += int(row["count"]) if row else 0
        return total

    def _dashboard_summary_data(self) -> dict[str, Any]:
        data = self.report_service.dashboard_summary(
            generated_by=self.current_user.get("full_name") or self.current_user.get("username") or "CRM User",
            generated_role=self.role,
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

    def _dashboard_label(self, text: str, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, color: str = "#17345c") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", size, weight))
        label.setStyleSheet(f"color: {color};")
        return label

    def _dashboard_tile(self, title: str, value: Any, tone: str) -> QFrame:
        colors = {
            "blue": ("#1f7ee7", "#0569c9", "#ffffff"),
            "cyan": ("#3cb7f2", "#218bd6", "#ffffff"),
            "silver": ("#cbd5e1", "#a9b5c4", "#0b2b50"),
            "green": ("#2ca84f", "#0d7a38", "#ffffff"),
            "royal": ("#217ae4", "#115fcd", "#ffffff"),
            "sky": ("#55b5e9", "#2d94d3", "#ffffff"),
            "slate": ("#c7d0dc", "#aab5c1", "#0b2b50"),
        }
        top, bottom, text = colors.get(tone, colors["blue"])
        frame = QFrame()
        frame.setMinimumHeight(104)
        frame.setStyleSheet(
            f"QFrame {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {top}, stop:1 {bottom}); "
            "border-radius: 8px; border: 1px solid #dbeafe; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(6)
        value_label = self._dashboard_label(f"{int(value):,}" if isinstance(value, int) else str(value), 26, QFont.Weight.Black, text)
        title_label = self._dashboard_label(title, 9, QFont.Weight.Black, text)
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return frame

    def _dashboard_panel(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setStyleSheet(
            "#DashboardPanel { background: #f8fbff; border: 1px solid #b8d1ef; "
            "border-radius: 10px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        heading = self._dashboard_label(title, 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)
        return panel, layout

    def _dashboard_legend_item(self, text: str, color: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QFrame()
        dot.setFixedSize(18, 12)
        dot.setStyleSheet(f"background: {color}; border-radius: 2px;")
        label = self._dashboard_label(text, 8, QFont.Weight.Bold, "#15457f")
        layout.addWidget(dot)
        layout.addWidget(label)
        return widget

    def _dashboard_approval_card(self, pending: int) -> QFrame:
        frame = QFrame()
        frame.setMinimumHeight(202)
        frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ff9f16, stop:1 #ec7900); "
            "border-radius: 10px; border: 1px solid #ffd08a; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 24, 28, 24)
        value = self._dashboard_label(f"{pending:,}", 38, QFont.Weight.Black, "#ffffff")
        title = self._dashboard_label("Pending Approvals", 17, QFont.Weight.Black, "#ffffff")
        note = self._dashboard_label("Needs Admin Review", 11, QFont.Weight.Bold, "#ffffff")
        layout.addStretch(1)
        layout.addWidget(value)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addStretch(1)
        return frame

    def _dashboard_demand_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._dashboard_panel("Rent Demand vs. Supply")
        layout.addWidget(DashboardBarChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._dashboard_legend_item("Rent Requirements", "#1976d2"))
        legend.addSpacing(20)
        legend.addWidget(self._dashboard_legend_item("Rent Availability", "#21964b"))
        layout.addLayout(legend)
        return panel

    def _dashboard_segments_panel(self, total: int, segments: list[dict[str, Any]], operations: list[tuple[str, str, str]]) -> QFrame:
        panel, layout = self._dashboard_panel("")
        layout.takeAt(0).widget().deleteLater()
        top = QHBoxLayout()
        top.setSpacing(24)
        top.addWidget(DashboardDonut(total, segments), 0, Qt.AlignmentFlag.AlignCenter)
        right = QVBoxLayout()
        heading = self._dashboard_label("Client Segments", 12, QFont.Weight.Black, "#0f4387")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(heading)
        for row in segments:
            item = QHBoxLayout()
            dot = QFrame()
            dot.setFixedSize(24, 24)
            dot.setStyleSheet(f"background: {row.get('color')}; border-radius: 12px;")
            item.addWidget(dot)
            item.addWidget(self._dashboard_label(str(row.get("label") or ""), 10, QFont.Weight.Normal, "#0f3768"), 1)
            item.addWidget(self._dashboard_label(f"{int(row.get('percent') or 0)}%", 11, QFont.Weight.Black, "#1976d2"))
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
            row.addWidget(self._dashboard_label(label, 9, QFont.Weight.Normal, "#163f79"), 1)
            row.addWidget(self._dashboard_label(value, 10, QFont.Weight.Black, "#0f7fe6"))
            table_layout.addLayout(row)
        layout.addWidget(table)
        return panel

    def _dashboard_roadmap_panel(self, rows: list[dict[str, Any]]) -> QFrame:
        panel, layout = self._dashboard_panel("30 / 90 / 180 Day Roadmap")
        layout.addWidget(DashboardLineChart(rows), 1)
        legend = QHBoxLayout()
        legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        legend.addWidget(self._dashboard_legend_item("Response Time", "#1976d2"))
        legend.addWidget(self._dashboard_legend_item("Approvals Cleared", "#ef7d00"))
        legend.addWidget(self._dashboard_legend_item("Conversion", "#3b9629"))
        layout.addLayout(legend)
        return panel

    def refresh_dashboard(self) -> None:
        if "dashboard" not in self.pages:
            return
        if self._dashboard_widget:
            self._dashboard_widget.refresh()
        data = self._dashboard_summary_data()

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 0, 18, 4)
        title = self._dashboard_label(f"{self.company_name} Report Summary", 27, QFont.Weight.Black, "#245ca9")
        user_line = f"{self.current_user.get('full_name') or self.current_user.get('username') or 'CRM User'}, {self.role}"
        subtitle = self._dashboard_label(user_line, 13, QFont.Weight.Normal, "#315784")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.dashboard_layout.addWidget(header)

        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(12)
        kpi_grid.setVerticalSpacing(12)
        for index, (label, value, tone) in enumerate(data["kpis"]):
            kpi_grid.addWidget(self._dashboard_tile(label, value, tone), 0, index)
            kpi_grid.setColumnStretch(index, 1)
        self.dashboard_layout.addLayout(kpi_grid)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.addWidget(self._dashboard_approval_card(data["pending"]), 3)
        top_row.addWidget(self._dashboard_demand_panel(data["locations"]), 8)
        self.dashboard_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        bottom_row.addWidget(self._dashboard_segments_panel(data["clients"], data["segments"], data["operations"]), 1)
        bottom_row.addWidget(self._dashboard_roadmap_panel(data["roadmap"]), 1)
        self.dashboard_layout.addLayout(bottom_row)
        self.dashboard_layout.addStretch(1)

    def count(self, table: str) -> int:
        row = self.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
        return int(row["count"]) if row else 0

    def sum_value(self, table: str, column: str) -> float:
        row = self.services.fetch_one(f"SELECT SUM({column}) AS total FROM {table}")
        return safe_float(row["total"]) if row else 0

    def ai_match(self, page: DataTablePage, table: str) -> None:
        row = page.require_single_row("AI matching")
        if not row:
            return
        text = self.ai_match_text(table, row["id"])
        dialog = QDialog(self)
        dialog.setWindowTitle("AI Smart Match")
        dialog.resize(760, 460)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setFont(QFont("Consolas", 10))
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def ai_match_text(self, table: str, row_id: int) -> str:
        try:
            return self.intelligence_service.match_report(table, row_id)
        except Exception as exc:
            fallback_header = f"Local AI match unavailable: {exc}\nUsing basic matching fallback.\n\n"
        target = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row_id,))
        if not target:
            return "No record found."
        if table == "rent_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, monthly_rent AS amount, property_availability AS type
                   FROM rent_availability
                   WHERE COALESCE(is_deleted,0)=0
                     AND LOWER(COALESCE(status,''))<>'rented'
                     AND (LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?))
                   ORDER BY ABS(COALESCE(monthly_rent,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_requires") or "", target.get("budget") or 0),
            )
        elif table == "sale_requirements":
            rows = self.services.fetch_all(
                """SELECT id, owner_name AS name, location, demand AS amount, property_availability AS type
                   FROM sale_availability
                   WHERE COALESCE(is_deleted,0)=0
                     AND LOWER(COALESCE(status,''))<>'sold'
                     AND (LOWER(location)=LOWER(?) OR LOWER(property_availability)=LOWER(?))
                   ORDER BY ABS(COALESCE(demand,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_requires") or "", target.get("budget") or 0),
            )
        elif table == "rent_availability":
            rows = self.services.fetch_all(
                """SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
                   FROM rent_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_availability") or "", target.get("monthly_rent") or 0),
            )
        else:
            rows = self.services.fetch_all(
                """SELECT id, client_name AS name, location, budget AS amount, property_requires AS type
                   FROM sale_requirements
                   WHERE LOWER(location)=LOWER(?) OR LOWER(property_requires)=LOWER(?)
                   ORDER BY ABS(COALESCE(budget,0)-COALESCE(?,0)) ASC LIMIT 10""",
                (target.get("location") or "", target.get("property_availability") or "", target.get("demand") or 0),
            )
        lines = [f"Smart matches for {table} #{row_id}", "-" * 72]
        for item in rows:
            lines.append(
                f"#{item['id']:<4} {str(item.get('name') or '-')[:24]:<24} "
                f"{str(item.get('location') or '-')[:18]:<18} {str(item.get('type') or '-')[:15]:<15} "
                f"{money(item.get('amount'), self.currency_symbol):>12}"
            )
        result = "\n".join(lines) if rows else "No close matches found."
        return fallback_header + result

    def pipeline_counts(self) -> dict[str, int]:
        counts = {stage: 0 for stage in DEAL_STAGES}
        for table in DEAL_TABLES:
            rows = self.services.fetch_all(
                f"""SELECT COALESCE(NULLIF(workflow_stage,''), 'Lead') AS stage, COUNT(*) AS count
                    FROM {table}
                    GROUP BY COALESCE(NULLIF(workflow_stage,''), 'Lead')"""
            )
            for row in rows:
                stage = row.get("stage") if row.get("stage") in DEAL_STAGES else "Lead"
                counts[stage] = counts.get(stage, 0) + int(row.get("count") or 0)
        return counts

    def pipeline_rows(self, stage: str | None = None) -> list[dict]:
        datasets = [
            ("Rent Req", "rent_requirements", "client_name", "property_requires", "budget"),
            ("Rent Av", "rent_availability", "owner_name", "property_availability", "monthly_rent"),
            ("Sale Req", "sale_requirements", "client_name", "property_requires", "budget"),
            ("Sale Av", "sale_availability", "owner_name", "property_availability", "demand"),
        ]
        rows: list[dict] = []
        for source, table, name_col, type_col, amount_col in datasets:
            where = ""
            params: tuple[Any, ...] = ()
            if stage:
                where = "WHERE COALESCE(NULLIF(workflow_stage,''), 'Lead')=?"
                params = (stage,)
            for row in self.services.fetch_all(
                f"""SELECT id, {name_col} AS name, location, {type_col} AS property_type,
                           {amount_col} AS amount, workflow_stage, priority, expected_close_value
                    FROM {table}
                    {where}
                    ORDER BY id DESC LIMIT 20"""
                ,
                params,
            ):
                rows.append({
                    "source": source,
                    "id": row["id"],
                    "name": row.get("name") or "",
                    "location": row.get("location") or "",
                    "stage": row.get("workflow_stage") or "Lead",
                    "priority": row.get("priority") or "Medium",
                    "amount": row.get("expected_close_value") or row.get("amount") or 0,
                })
        return rows[:40]

    def open_report(self, kind: str) -> None:
        reports = self.pages.get("reports")
        if isinstance(reports, ReportsModule):
            self.switch_page("reports")
            reports.report_type.setCurrentText("Rent" if kind == "rent" else "Sale")
            reports.generate(kind)
        else:
            self.preview_report(kind)

    def preview_report(self, kind: str) -> None:
        if kind == "sale":
            result = self.report_service.sale_report()
        elif kind == "both":
            result = self.report_service.dealings_report()
        else:
            result = self.report_service.rent_report()
        self.last_report = result
        self.update_status_bar(f"{result.title} generated")
        ReportPreviewDialog(result, self).exec()

    def preview_named_report(self, kind: str) -> None:
        normalized = kind.strip().lower()
        if normalized in {"rent", "sale", "both", "rent + sale"}:
            self.preview_report("both" if normalized in {"both", "rent + sale"} else normalized)
            return
        if normalized == "financial":
            result = ReportResult("Financial Summary", self.financial_text(), filename_slug="financial_summary")
        elif normalized == "properties":
            result = ReportResult("Property Report", self.generic_report("properties", "PROPERTY REPORT"), filename_slug="property_report")
        elif normalized == "clients":
            result = ReportResult("Client Report", self.generic_report("clients", "CLIENT REPORT"), filename_slug="client_report")
        elif normalized == "employees":
            result = ReportResult("Employee Report", self.generic_report("employees", "EMPLOYEE REPORT"), filename_slug="employee_report")
        else:
            result = ReportResult("Attendance Report", self.attendance_report(), filename_slug="attendance_report")
        self.last_report = result
        self.update_status_bar(f"{result.title} generated")
        ReportPreviewDialog(result, self).exec()

    def open_search(self) -> None:
        self.update_status_bar("Find opened")
        SearchDialog(self).exec()
        self.update_status_bar("Find closed")

    def _rows_in_date_range(
        self,
        table: str,
        date_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        rows = self.services.fetch_all(f"SELECT * FROM {table} ORDER BY {date_key} DESC, id DESC")
        start = parse_py_date(start_date)
        end = parse_py_date(end_date)
        if not start and not end:
            return rows
        filtered: list[dict] = []
        for row in rows:
            row_date = parse_py_date(row.get(date_key))
            if not row_date:
                continue
            if start and row_date.date() < start.date():
                continue
            if end and row_date.date() > end.date():
                continue
            filtered.append(row)
        return filtered

    def _period_label(self, start_date: str | None = None, end_date: str | None = None) -> str:
        start = format_date_display(start_date) if parse_py_date(start_date) else "Beginning"
        end = format_date_display(end_date) if parse_py_date(end_date) else "Today"
        if start == "Beginning" and end == "Today":
            return "All records"
        return f"{start} to {end}"

    def build_financial_text(self, start_date: str | None = None, end_date: str | None = None) -> str:
        return build_financial_text(
            self.services, self.company_name, self.currency_symbol,
            start_date, end_date,
        )

    def financial_text(self, start_date: str | None = None, end_date: str | None = None) -> str:
        if start_date or end_date:
            return self.build_financial_text(start_date, end_date)
        page = self.pages.get("financials")
        if isinstance(page, FinancialModule):
            page.summary.refresh()
            return page.summary.text.toPlainText()
        return self.build_financial_text()

    def generic_report(self, table: str, title: str) -> str:
        return _generic_report(self.services, table, title)

    def attendance_report(self) -> str:
        return _attendance_report(self.services)

    def export_all_tables(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        base, _ = QFileDialog.getSaveFileName(
            self,
            "Export All Tables",
            str(OUTPUT_DIR / f"crm_export_{datetime.now().strftime('%Y%m%d')}.csv"),
            "CSV Files (*.csv)",
        )
        if not base:
            return
        stem, ext = os.path.splitext(base)
        tables = [
            "rent_requirements", "rent_availability", "sale_requirements", "sale_availability",
            "income_transactions", "expense_transactions", "employees", "clients", "broker_contacts", "properties",
            "attendance", "salary_payments", "users",
        ]
        for table in tables:
            rows = self.services.fetch_all(f"SELECT * FROM {table}")
            if not rows:
                continue
            with open(f"{stem}_{table}{ext}", "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        QMessageBox.information(self, "Exported", f"Tables exported with prefix:\n{stem}")
        self.update_status_bar("All tables exported")

    def backup_database(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            str(OUTPUT_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"),
            "SQLite DB (*.db)",
        )
        if not path:
            return
        with sqlite3.connect(DB_PATH, timeout=30) as source, sqlite3.connect(path) as destination:
            source.execute("PRAGMA busy_timeout=30000")
            source.backup(destination, pages=100, sleep=0.001)
        QMessageBox.information(self, "Backup", f"Database backed up to:\n{path}")
        self.update_status_bar("Database backup saved")

    def auto_backup_on_close(self) -> Path | None:
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = BACKUP_DIR / f"auto_close_backup_{stamp}.db"
            with sqlite3.connect(DB_PATH, timeout=30) as source, sqlite3.connect(destination) as backup:
                source.execute("PRAGMA busy_timeout=30000")
                source.backup(backup, pages=100, sleep=0.001)
            backups = sorted(BACKUP_DIR.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
            for old_backup in backups[30:]:
                try:
                    old_backup.unlink()
                except OSError:
                    pass
            return destination
        except Exception as exc:
            print(f"Auto backup on close failed: {exc}")
            return None

    def show_ecosystem_health(self) -> None:
        try:
            report = format_ecosystem_report(collect_ecosystem_health(DB_PATH))
        except Exception as exc:
            report = f"QT_CRM ECOSYSTEM HEALTH\n========================\nStatus: Error\n\n{exc}"
        self.show_text_dialog("QT_CRM Ecosystem Health", report, width=860, height=620)

    def show_api_health(self) -> None:
        QMessageBox.information(
            self,
            "Server Health",
            f"Browser login for client computers:\n{self.browser_service_url}\n\n"
            f"Status: {self._lan_web_status}\n"
            f"Host binding: {LAN_WEB_HOST}:{LAN_WEB_PORT}\n\n"
            f"Desktop internal API:\n{self.local_service_url}\n\n"
            "Client users should open the browser login URL on the office network.",
        )

    def show_text_dialog(self, title: str, text: str, *, width: int = 760, height: int = 560) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setWordWrapMode(preview.wordWrapMode())
        preview.setPlainText(text)
        layout.addWidget(preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_user_guide(self) -> None:
        self.show_text_dialog(
            "User Guide",
            """PROFESSIONAL REAL ESTATE CRM - QT USER GUIDE
===============================================

DASHBOARD
  - View key totals and income/expense totals.

RENT AND SALE DEALINGS
  - Add requirements and available properties.
  - Edit records, run smart matching, and generate reports.

PROPERTIES AND CLIENTS
  - Maintain portfolio and contact records.
  - Use Details or Copy Row for quick review/sharing.

FINANCIALS
  - Record income and expense transactions.
  - Review and export profit/loss summary.

EMPLOYEES
  - Maintain employee records.
  - Mark attendance and process salary payments.

REPORTS
  - Generate rent, sale, combined, financial, property, client, employee, and attendance reports.
  - Export TXT, CSV, or PDF.

MENUS AND SHORTCUTS
  - File > New creates the main rent/sale records without hunting through tabs.
  - Ctrl+F opens Find, F5 refreshes, Ctrl+E exports all tables, Ctrl+B backs up the database.
  - Ctrl+1 through Ctrl+9 jump between visible CRM sections.
  - F11 opens full screen; Shift+F11 returns to normal view.

REQUIRED FIELDS
  - Deal forms require date, name, client/broker, contact, property, size, amount, and location.
  - Required labels are marked with * and checked before saving.

AI INSIGHTS
  - Run local pandas/numpy analysis for lead scoring, NLP keywords, matching, price guidance, and forecasts.
  - AI features stay offline on the local SQLite database.

LAN SERVER
  - Keep this main/server computer running while other users work.
  - Client computers open the browser login URL shown in Tools > Server Health.
  - The browser portal listens on port 6090 by default.

SECURITY
  - Role-based access controls remain active.
  - Admin roles can manage users, settings, backup, and delete records.
""",
        )

    def show_roles_info(self) -> None:
        lines = [
            "ROLE-BASED ACCESS CONTROL",
            "=" * 72,
            "Feature            Super Admin  Admin   Manager   Staff   Viewer",
            "-" * 72,
            "Dashboard          Yes          Yes     Yes       Yes     Yes",
            "Rent/Sale Deals    Full         Full    Full      Add/Edit View",
            "Find Rent/Sale     Yes          Yes     Yes       Yes     Yes",
            "Properties         Full         Full    Full      No      No",
            "Clients            Full         Full    Full      No      No",
            "Financials         Full         Full    Full      No      No",
            "Employees          Full         Full    Full      View    View",
            "Reports            Yes          Yes     Yes       Yes     Yes",
            "AI Insights         Yes          Yes     Yes       No      No",
            "Settings           Yes          Yes     No        No      No",
            "User Management    Yes          Yes     No        No      No",
            "Delete Records     Yes          Yes     No        No      No",
            "Backup/Export      Yes          Yes     No        No      No",
            "",
            "Permissions configured in qt_crm_app.py:",
        ]
        for role, permissions in ROLE_PERMISSIONS.items():
            lines.append(f"{role:<12}: {', '.join(permissions)}")
        self.show_text_dialog("Roles & Permissions", "\n".join(lines), width=780, height=560)

    def show_developer_info(self) -> None:
        QMessageBox.information(
            self,
            "Developer Info",
            "Developer: Muhammad Siddique\n"
            "Email: info@msxhan.online\n\n"
            "Application: Professional Real Estate CRM\n"
            "UI Framework: Python + PySide6/Qt",
        )

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            f"Professional Real Estate CRM\n"
            f"Version: Qt Migration\n\n"
            f"Built with Python and PySide6\n"
            f"Database: SQLite\n"
            f"DB File: {DB_PATH}\n"
            f"Browser Login: {self.browser_service_url}\n"
            f"Desktop API: {self.local_service_url}\n\n"
            f"Developer: Muhammad Siddique\n"
            f"Email: info@msxhan.online\n\n"
            f"Company: {self.company_name}\n"
            f"User: {self.current_user.get('full_name')} ({self.role})\n"
            f"Year: {datetime.now().year}",
        )

    def restart_app(self) -> None:
        self._lan_server.stop()
        self._desktop_server.stop()
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(Path(__file__).resolve().parent))
        QApplication.quit()

    def logout(self) -> None:
        if QMessageBox.question(self, "Logout", "Logout and return to the login screen?") != QMessageBox.Yes:
            return
        self.restart_app()

    def closeEvent(self, event: Any) -> None:
        self.auto_backup_on_close()
        self._lan_server.stop()
        self._desktop_server.stop()
        super().closeEvent(event)


def deal_common_fields(
    name_key: str,
    property_key: str,
    amount_key: str,
    *,
    name_label: str | None = None,
    option_sets: dict[str, list[str]] | None = None,
) -> list[FieldSpec]:
    option_sets = option_sets or {}
    areas = option_sets.get("areas", COMMON_AREAS)
    facilities = option_sets.get("facilities", FACILITY_OPTIONS)
    floors = option_sets.get("floors", FLOOR_OPTIONS)
    property_types = option_sets.get("property_types", PROPERTY_TYPE_OPTIONS)
    measurement_units = option_sets.get("measurement_units", MEASUREMENT_UNIT_OPTIONS)
    name_label = name_label or ("Name *" if name_key == "client_name" else "Owner Name *")
    property_label = "Property Required / Needed" if "requires" in property_key else "Property Available"
    amount_label = "Budget" if amount_key == "budget" else ("Rent" if amount_key == "monthly_rent" else "Demand")
    return [
        FieldSpec("Date *", "date", "date", required=True),
        FieldSpec(name_label, name_key, required=True),
        FieldSpec("Contact *", "contact", required=True),
        FieldSpec(f"{property_label} *", property_key, "combo", options=property_types, required=True),
        FieldSpec("Rooms *", "size", "combo_other", options=["1 BED", "2 BED", "3 BED", "4 BED", "2-3 BED", "3 BED DD", "Studio", "Shop", "Office"], required=True),
        FieldSpec("Measurement", "measurement", numeric=True),
        FieldSpec("Size", "measurement_unit", "combo", "Sq Ft", measurement_units),
        FieldSpec(f"{amount_label} (Rs.) *", amount_key, numeric=True, required=True),
        FieldSpec("Floor", "floor", "multiselect", options=floors),
        FieldSpec("Location *", "location", "autocomplete", options=areas, required=True),
        FieldSpec("Facilities", "facilities", "facilities", options=facilities),
        FieldSpec("Bachelor / Family", "bachelor_family", "combo_other", options=FAMILY_OPTIONS),
        FieldSpec("Remarks", "remarks", "text"),
    ]


def deal_fields(name_key: str, property_key: str, amount_key: str, option_sets: dict[str, list[str]] | None = None) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, option_sets=option_sets)
    fields.insert(2, FieldSpec("Client/Broker/Owner *", "client_status", "combo", "Client", OWNER_BROKER_OPTIONS, required=True))
    return fields


def availability_fields(name_key: str, property_key: str, amount_key: str, option_sets: dict[str, list[str]] | None = None) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, option_sets=option_sets)
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields


def owner_broker_availability_fields(
    name_key: str,
    property_key: str,
    amount_key: str,
    option_sets: dict[str, list[str]] | None = None,
) -> list[FieldSpec]:
    fields = deal_common_fields(name_key, property_key, amount_key, name_label="Name *", option_sets=option_sets)
    fields.insert(2, FieldSpec("Client/Broker/Owner *", "client_broker", "combo", "Owner", OWNER_BROKER_OPTIONS, required=True))
    if amount_key == "monthly_rent":
        idx = next(i for i, field in enumerate(fields) if field.key == "floor") + 1
        fields.insert(idx, FieldSpec("Deposit", "deposit", numeric=True))
        fields.insert(idx + 1, FieldSpec("Maintenance", "maintenance_charge", numeric=True))
    return fields


def deal_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def deal_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "client_status", "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks",
    ]


def availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks", "created_by", "created_at",
    ]


def availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    return [
        "date", name_key, "contact", property_key, "size", "measurement", "measurement_unit", amount_key,
        "floor", "location", "facilities",
        "bachelor_family", "remarks",
    ]


def owner_broker_availability_insert_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    columns = availability_insert_columns(name_key, property_key, amount_key)
    columns.insert(columns.index("bachelor_family"), "client_broker")
    return columns


def owner_broker_availability_update_columns(name_key: str, property_key: str, amount_key: str) -> list[str]:
    columns = availability_update_columns(name_key, property_key, amount_key)
    columns.insert(columns.index("bachelor_family"), "client_broker")
    return columns


def property_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Property Code", "property_code", "entry", lambda: gen_id("PROP")),
        FieldSpec("Title *", "title", required=True),
        FieldSpec("Type", "property_type", "combo", options=["Apartment", "House", "Villa", "Studio", "Shop", "Office", "Warehouse", "Plot"]),
        FieldSpec("Status", "status", "combo", "Available", ["Available", "Rented", "Sold", "Reserved"]),
        FieldSpec("Owner Name", "owner_name"),
        FieldSpec("Owner Contact", "owner_contact"),
        FieldSpec("Location *", "location", "autocomplete", options=COMMON_AREAS, required=True),
        FieldSpec("Area", "area"),
        FieldSpec("Floor", "floor", "multiselect", options=FLOOR_OPTIONS),
        FieldSpec("Monthly Rent", "monthly_rent", numeric=True),
        FieldSpec("Sale Price", "sale_price", numeric=True),
        FieldSpec("Maintenance", "maintenance_charge", numeric=True),
        FieldSpec("Facilities", "facilities", "facilities", options=FACILITY_OPTIONS),
        FieldSpec("Description", "description", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("property_code", "Code", width=110),
        ColumnSpec("title", "Title", width=180), ColumnSpec("property_type", "Type", width=110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("owner_name", "Owner", width=150),
        ColumnSpec("location", "Location", width=160), ColumnSpec("monthly_rent", "Rent", m, 110),
        ColumnSpec("sale_price", "Sale Price", m, 120), ColumnSpec("maintenance_charge", "Maintenance", m, 120),
        ColumnSpec("facilities", "Facilities", width=220), ColumnSpec("description", "Description", width=240),
    ]
    insert = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description", "created_at"]
    update = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description"]
    return TableSpec("Properties", "properties", cols, fields, insert, update, permission="properties")


def client_spec() -> TableSpec:
    fields = [
        FieldSpec("Client Name *", "client_name", required=True),
        FieldSpec("Phone", "phone"),
        FieldSpec("Email", "email"),
        FieldSpec("Address", "address", "text"),
        FieldSpec("Client Type", "client_type", "combo", "Tenant", ["Tenant", "Buyer", "Seller", "Investor", "Other"]),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Inactive"]),
        FieldSpec("Notes", "notes", "text"),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("client_name", "Name", width=180),
        ColumnSpec("phone", "Phone", width=130),
        ColumnSpec("email", "Email", width=180), ColumnSpec("client_type", "Type", width=110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("address", "Address", width=220),
        ColumnSpec("notes", "Notes", width=240),
    ]
    insert = ["client_name", "phone", "email", "address", "client_type", "status", "notes", "created_at"]
    update = ["client_name", "phone", "email", "address", "client_type", "status", "notes"]
    return TableSpec("Clients", "clients", cols, fields, insert, update, permission="clients")


def broker_contact_spec() -> TableSpec:
    fields = [
        FieldSpec("Name *", "name", required=True),
        FieldSpec("Contact *", "contact", required=True),
        FieldSpec("Area", "area", "autocomplete", options=COMMON_AREAS),
        FieldSpec("Office Address", "office_address", "text"),
        FieldSpec("Home Address", "home_address", "text"),
        FieldSpec("Remarks", "remarks", "text"),
    ]
    cols = [
        ColumnSpec("id", "Sr. No", width=80),
        ColumnSpec("name", "Name", width=180),
        ColumnSpec("contact", "Contact", width=140),
        ColumnSpec("area", "Area", width=170),
        ColumnSpec("office_address", "Office Address", width=240),
        ColumnSpec("home_address", "Home Address", width=240),
        ColumnSpec("remarks", "Remarks", width=260),
    ]
    insert = ["name", "contact", "area", "office_address", "home_address", "remarks", "created_at"]
    update = ["name", "contact", "area", "office_address", "home_address", "remarks"]
    return TableSpec(
        "Broker Contact List",
        "broker_contacts",
        cols,
        fields,
        insert,
        update,
        permission="clients",
        order_by="area ASC, name ASC, id DESC",
    )


def income_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    fields = [
        FieldSpec("Date *", "transaction_date", "date", required=True),
        FieldSpec("Income Type *", "income_type", "combo", options=["Rent", "Deposit", "Maintenance", "Commission", "Utility", "Advance", "Other"], required=True),
        FieldSpec("Amount *", "amount", numeric=True, required=True),
        FieldSpec("Client Name", "tenant_name"),
        FieldSpec("Description", "description"),
        FieldSpec("Receipt No", "receipt_no", "entry", lambda: gen_id("RCP")),
        FieldSpec("Payment Method", "payment_method", "combo", "Cash", ["Cash", "Cheque", "Bank Transfer", "Online"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("transaction_date", "Date", format_date_display, 100),
        ColumnSpec("income_type", "Type", width=130), ColumnSpec("amount", "Amount", m, 120),
        ColumnSpec("tenant_name", "Client", width=150), ColumnSpec("description", "Description", width=220),
        ColumnSpec("receipt_no", "Receipt No", width=120), ColumnSpec("payment_method", "Method", width=120),
    ]
    insert = ["transaction_date", "income_type", "amount", "tenant_name", "description", "receipt_no", "payment_method", "created_by", "created_at"]
    update = ["transaction_date", "income_type", "amount", "tenant_name", "description", "receipt_no", "payment_method"]
    return TableSpec("Income", "income_transactions", cols, fields, insert, update, permission="financial")


def expense_spec(categories: list[str] | None = None) -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    category_options = categories or list(EXPENSE_CATEGORIES)
    fields = [
        FieldSpec("Date *", "transaction_date", "date", required=True),
        FieldSpec("Category *", "expense_category", "combo", options=category_options, required=True),
        FieldSpec("Amount *", "amount", numeric=True, required=True),
        FieldSpec("Vendor Name", "vendor_name"),
        FieldSpec("Description", "description"),
        FieldSpec("Invoice No", "invoice_no", "entry", lambda: gen_id("INV")),
        FieldSpec("Payment Method", "payment_method", "combo", "Cash", ["Cash", "Cheque", "Bank Transfer", "Online"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("transaction_date", "Date", format_date_display, 100),
        ColumnSpec("expense_category", "Category", width=130), ColumnSpec("amount", "Amount", m, 120),
        ColumnSpec("vendor_name", "Vendor", width=150), ColumnSpec("description", "Description", width=220),
        ColumnSpec("invoice_no", "Invoice No", width=120), ColumnSpec("payment_method", "Method", width=120),
    ]
    insert = ["transaction_date", "expense_category", "amount", "vendor_name", "description", "invoice_no", "payment_method", "created_by", "created_at"]
    update = ["transaction_date", "expense_category", "amount", "vendor_name", "description", "invoice_no", "payment_method"]
    return TableSpec("Expenses", "expense_transactions", cols, fields, insert, update, permission="financial")


def employee_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    pct = lambda value, _symbol: f"{safe_float(value):.1f}%"
    fields = [
        FieldSpec("Employee ID", "employee_id", "entry", lambda: gen_id("EMP")),
        FieldSpec("Full Name *", "full_name", required=True),
        FieldSpec("Phone", "phone"),
        FieldSpec("Email", "email"),
        FieldSpec("Position *", "position", "combo_other", options=["Agent", "Manager", "Broker", "Admin", "Staff", "Driver", "Security", "Cleaner"], required=True),
        FieldSpec("Department", "department", "combo_other", options=["Sales", "Rentals", "Administration", "Finance", "Operations"]),
        FieldSpec("Hire Date", "hire_date", "date"),
        FieldSpec("Base Salary *", "base_salary", numeric=True, required=True),
        FieldSpec("Commission %", "commission_rate", "entry", "5.0", numeric=True),
        FieldSpec("Address", "address", "text"),
        FieldSpec("Notes", "notes", "text"),
        FieldSpec("Status", "status", "combo", "Active", ["Active", "Inactive", "On Leave", "Terminated"]),
    ]
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("employee_id", "Emp ID", width=110),
        ColumnSpec("full_name", "Name", width=170), ColumnSpec("position", "Position", width=130),
        ColumnSpec("department", "Department", width=130), ColumnSpec("phone", "Phone", width=130),
        ColumnSpec("base_salary", "Salary", m, 120), ColumnSpec("commission_rate", "Commission", pct, 110),
        ColumnSpec("status", "Status", width=100), ColumnSpec("notes", "Notes", width=220),
    ]
    insert = ["employee_id", "full_name", "phone", "email", "position", "department", "hire_date", "base_salary", "commission_rate", "address", "notes", "status", "created_at"]
    update = ["employee_id", "full_name", "phone", "email", "position", "department", "hire_date", "base_salary", "commission_rate", "address", "notes", "status"]
    return TableSpec("Employees", "employees", cols, fields, insert, update, permission="employees")


def salary_spec() -> TableSpec:
    m = lambda value, symbol: money(value, symbol)
    cols = [
        ColumnSpec("id", "ID", width=64), ColumnSpec("full_name", "Employee", width=170),
        ColumnSpec("month", "Month", width=110), ColumnSpec("year", "Year", width=80),
        ColumnSpec("base_salary", "Base Salary", m, 120), ColumnSpec("bonus", "Bonus", m, 110),
        ColumnSpec("deductions", "Deductions", m, 120), ColumnSpec("net_salary", "Net Salary", m, 120),
        ColumnSpec("payment_method", "Method", width=120),
    ]
    return TableSpec("Salary History", "salary_payments", cols, [], [], [], permission="employees")


APP_STYLE = """
QMainWindow { background: #eef2f7; }
QStatusBar#AppStatusBar {
    background: #f8fafc;
    color: #475569;
    border-top: 1px solid #cbd5e1;
}
QMenuBar {
    background: #ffffff;
    color: #102033;
    border-bottom: 1px solid #d9e2ef;
    padding: 5px 12px;
    font-weight: 700;
}
QMenuBar::item {
    background: transparent;
    border-radius: 6px;
    padding: 7px 11px;
}
QMenuBar::item:selected {
    background: #eef6ff;
    color: #1d4ed8;
}
QMenuBar::item:pressed {
    background: #dbeafe;
}
QMenu {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    border-radius: 6px;
    padding: 8px 24px 8px 12px;
}
QMenu::item:selected {
    background: #eef6ff;
    color: #1d4ed8;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 6px 4px;
}
QLabel#StatusBarLabel {
    color: #334155;
    padding: 0 8px;
    font-size: 11px;
}
#Sidebar {
    background: #101827;
    border: none;
}
#BrandCard {
    background: #172338;
    border: 1px solid #263650;
    border-radius: 10px;
}
#LogoBadge {
    background: #2563eb;
    color: #ffffff;
    border-radius: 8px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
    font-size: 15px;
    font-weight: 900;
}
#LogoImage {
    background: transparent;
    border: none;
}
#Brand {
    color: #ffffff;
    font-size: 19px;
    font-weight: 900;
}
#SidebarSubtle {
    color: #91a4c0;
    font-size: 12px;
}
#SidebarStatusText {
    color: #dbeafe;
    font-size: 12px;
    font-weight: 800;
}
#UserCard {
    background: #0f172a;
    border: 1px solid #263650;
    border-radius: 10px;
}
#SidebarUserName {
    color: #ffffff;
    font-size: 14px;
    font-weight: 800;
}
#RolePill {
    background: #e0f2fe;
    color: #075985;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 800;
}
#NavShell {
    background: transparent;
    border: none;
}
QScrollArea#SidebarNavScroll {
    background: transparent;
    border: none;
}
QScrollArea#SidebarNavScroll QScrollBar:vertical {
    background: #0f172a;
    border: none;
    border-radius: 4px;
    width: 8px;
    margin: 4px 0 4px 0;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 34px;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollArea#SidebarNavScroll QScrollBar::add-line:vertical,
QScrollArea#SidebarNavScroll QScrollBar::sub-line:vertical {
    height: 0;
}
#NavSeparator {
    background: #22324c;
    border: none;
    min-height: 1px;
    max-height: 1px;
    margin: 8px 8px 5px 8px;
}
#NavSection {
    color: #7f93b2;
    font-size: 10px;
    font-weight: 900;
    padding: 8px 8px 2px 8px;
}
QFrame#NavItem {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
}
QFrame#NavItem:hover {
    background: #18243a;
    border-color: #2b3d5a;
}
QFrame#NavItem[active="true"] {
    background: #2563eb;
    border-color: #3b82f6;
}
QFrame#NavItem:hover QLabel#NavText {
    color: #ffffff;
}
QFrame#NavItem:hover QLabel#NavIcon {
    background: #263956;
}
#NavIndicator {
    background: transparent;
    border-radius: 2px;
}
#NavIndicator[active="true"] {
    background: #bfdbfe;
}
QLabel#NavIcon {
    background: #1e2b42;
    color: #dbeafe;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 900;
}
QLabel#NavIcon[active="true"] {
    background: #dbeafe;
    color: #1d4ed8;
}
QLabel#NavText {
    color: #dbeafe;
    font-size: 13px;
    font-weight: 800;
}
QLabel#NavText[active="true"] {
    color: #ffffff;
}
#SidebarFooter {
    background: #0f172a;
    border: 1px solid #263650;
    border-radius: 10px;
}
#StatusDot {
    background: #22c55e;
    border-radius: 5px;
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
}
#SidebarLogout {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    padding: 9px 12px;
    font-weight: 800;
}
#SidebarLogout:hover {
    background: #eff6ff;
    border-color: #93c5fd;
}
#Content { background: #eef2f7; }
#TopTitle { color: #0f172a; font-size: 18px; font-weight: 800; }
#PageTitle { color: #0f172a; font-size: 24px; font-weight: 800; }
#SectionTitle { color: #0f172a; font-size: 17px; font-weight: 800; }
#PhaseCard {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 22px;
    font-weight: 900;
    padding: 18px;
    text-align: left;
}
#PhaseCard:hover {
    background: #eff6ff;
    border-color: #2563eb;
}
#MetricCard, #Panel {
    background: white;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#SettingsListEditor {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#SettingsListTitle {
    color: #0f172a;
    font-size: 14px;
    font-weight: 900;
}
#SettingsCount {
    background: #e0f2fe;
    color: #075985;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 900;
}
#ReportShell {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 10px;
}
#ReportControls {
    background: #f8fbff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
}
#ReportQuickButton, #ReportQuickButtonActive {
    min-height: 48px;
    font-size: 14px;
    font-weight: 900;
    text-align: left;
}
#ReportQuickButtonActive {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
#ReportQuickButtonActive:hover {
    background: #1d4ed8;
}
#ReportPreview {
    background: #ffffff;
    border: 1px solid #d9e2ef;
    border-radius: 8px;
    padding: 0;
}
#MetricTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
}
#MetricValue { color: #0f172a; font-size: 27px; font-weight: 900; }
#MetricNote { color: #64748b; font-size: 12px; }
#LoginTitle { color: #0f172a; font-size: 28px; font-weight: 900; }
#StartupDialog {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
}
#StartupTitle {
    color: #0f172a;
    font-size: 22px;
    font-weight: 900;
}
QProgressBar {
    background: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    color: #0f172a;
    font-weight: 800;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 5px;
}
#MutedText { color: #64748b; }
#SelectionCount {
    color: #64748b;
    font-size: 12px;
    font-weight: 800;
}
QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px;
    selection-background-color: #dbeafe;
}
QListWidget {
    color: #0f172a;
    alternate-background-color: #f8fafc;
    outline: none;
}
QListWidget::item {
    min-height: 24px;
    padding: 5px 7px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
QTableWidget { padding: 0; gridline-color: #e2e8f0; }
QTableWidget::item {
    color: #0f172a;
    padding: 5px;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #334155;
    border: none;
    border-bottom: 1px solid #d9e2ef;
    padding: 8px;
    font-weight: 800;
}
QPushButton {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 13px;
    min-height: 20px;
    font-size: 13px;
    font-weight: 750;
}
QPushButton:hover {
    background: #f8fafc;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background: #e2e8f0;
    border-color: #64748b;
}
QPushButton:focus {
    border-color: #2563eb;
}
QPushButton:disabled {
    background: #f1f5f9;
    color: #94a3b8;
    border-color: #d8e1ea;
}
#AccentButton {
    background: #2563eb;
    color: white;
    border: 1px solid #2563eb;
}
#AccentButton:hover { background: #1d4ed8; }
#AccentButton:pressed { background: #1e40af; }
#AccentButton:disabled {
    background: #bfdbfe;
    color: #f8fafc;
    border-color: #bfdbfe;
}
#WarningButton {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #f59e0b;
}
#WarningButton:hover { background: #fde68a; }
#WarningButton:pressed { background: #fcd34d; }
#DangerButton {
    background: #dc2626;
    color: white;
    border: 1px solid #dc2626;
}
#DangerButton:hover { background: #b91c1c; }
#DangerButton:pressed { background: #991b1b; }
#DangerButton:disabled {
    background: #fecaca;
    color: #fff7f7;
    border-color: #fecaca;
}
#FacilitiesBox, #MultiSelectBox {
    background: #f8fafc;
    border: 1px solid #d9e2ef;
    border-radius: 6px;
}
QLabel#FormGroupTitle {
    color: #0f172a;
    background: #eef6ff;
    border: 1px solid #d9e2ef;
    border-radius: 6px;
    padding: 7px 10px;
    font-weight: 900;
}
QRadioButton#FacilityCheck {
    background: #e5e7eb;
    color: #0f172a;
    border-radius: 2px;
    padding: 4px 7px;
    font-weight: 700;
    spacing: 6px;
}
QRadioButton#FacilityCheck:hover {
    background: #dbeafe;
}
QRadioButton#FacilityCheck::indicator {
    width: 14px;
    height: 14px;
}
QCheckBox#MultiSelectCheck {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 8px;
    font-weight: 700;
    spacing: 7px;
}
QCheckBox#MultiSelectCheck:hover {
    background: #eef6ff;
    border-color: #93c5fd;
}
QCheckBox#MultiSelectCheck::indicator {
    width: 15px;
    height: 15px;
}
QTabWidget::pane {
    border: 1px solid #d9e2ef;
    background: #ffffff;
    border-radius: 8px;
}
QTabBar::tab {
    background: #f8fafc;
    padding: 9px 14px;
    border: 1px solid #d9e2ef;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #2563eb;
    font-weight: 800;
}
"""


DARK_APP_STYLE = APP_STYLE + """
QMainWindow, #Content { background: #0f172a; }
QMenuBar {
    background: #0f172a;
    color: #e5e7eb;
    border-bottom-color: #334155;
}
QMenuBar::item:selected {
    background: #1f2937;
    color: #bfdbfe;
}
QMenuBar::item:pressed {
    background: #172554;
}
QMenu {
    background: #111827;
    color: #e5e7eb;
    border-color: #334155;
}
QMenu::item:selected {
    background: #172554;
    color: #bfdbfe;
}
QMenu::separator {
    background: #334155;
}
#PageTitle, #SectionTitle, #TopTitle, QLabel#FormLabel, QLabel#RequiredLabel {
    color: #e5e7eb;
}
QLabel#FormGroupTitle {
    color: #e5e7eb;
    background: #172554;
    border-color: #334155;
}
#Panel, #MetricCard, QTabWidget::pane {
    background: #111827;
    border-color: #334155;
}
#SettingsListEditor {
    background: #111827;
    border-color: #334155;
}
#SettingsListTitle {
    color: #e5e7eb;
}
#SettingsCount {
    background: #172554;
    color: #bfdbfe;
}
#ReportShell, #ReportControls, #ReportPreview {
    background: #111827;
    border-color: #334155;
}
#ReportQuickButton {
    background: #1f2937;
    color: #e5e7eb;
    border-color: #475569;
}
#ReportQuickButtonActive {
    background: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}
QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QDateEdit {
    background: #111827;
    color: #e5e7eb;
    border-color: #334155;
}
QListWidget {
    alternate-background-color: #0f172a;
}
QListWidget::item:selected {
    background: #1e40af;
    color: #f8fafc;
}
QTableWidget::item { color: #e5e7eb; }
QHeaderView::section {
    background: #1f2937;
    color: #e5e7eb;
    border-bottom-color: #334155;
}
QPushButton {
    background: #1f2937;
    color: #e5e7eb;
    border-color: #475569;
}
QPushButton:hover {
    background: #334155;
    border-color: #64748b;
}
QPushButton:pressed {
    background: #0f172a;
    border-color: #94a3b8;
}
QPushButton:disabled {
    background: #111827;
    color: #64748b;
    border-color: #253044;
}
#AccentButton {
    background: #2563eb;
    color: #ffffff;
    border-color: #3b82f6;
}
#AccentButton:hover { background: #1d4ed8; }
#AccentButton:pressed { background: #1e40af; }
#WarningButton {
    background: #422006;
    color: #facc15;
    border-color: #854d0e;
}
#WarningButton:hover { background: #713f12; }
#WarningButton:pressed { background: #854d0e; }
#DangerButton {
    background: #991b1b;
    color: #ffffff;
    border-color: #b91c1c;
}
#DangerButton:hover { background: #7f1d1d; }
#DangerButton:pressed { background: #450a0a; }
#PhaseCard {
    background: #111827;
    color: #f8fafc;
    border-color: #334155;
}
#PhaseCard:hover {
    background: #172554;
    border-color: #60a5fa;
}
#MutedText, #SelectionCount, #MetricNote, #MetricTitle {
    color: #cbd5e1;
}
"""


try:
    from qt_crm_premium_style import APP_STYLE as PREMIUM_APP_STYLE, DARK_APP_STYLE as PREMIUM_DARK_APP_STYLE
except Exception as exc:
    print(f"Premium Qt theme unavailable, using built-in theme: {exc}")
else:
    APP_STYLE = PREMIUM_APP_STYLE
    DARK_APP_STYLE = PREMIUM_DARK_APP_STYLE

# ─── CRM module imports ───
from CRM.constants import *
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.database import ensure_database, ensure_qt_schema
from CRM.utils import *
from CRM.widgets.table import (
    ExcelTableWidget, configure_multi_select_table, configure_table_for_readability,
    responsive_table_columns, apply_responsive_table_layout,
    style_workflow_table_item, selected_table_row_indexes,
    select_all_table_rows, clear_table_selection,
)
from CRM.widgets.charts import DashboardBarChart, DashboardDonut, DashboardLineChart
from CRM.widgets.cards import MetricCard, NavItem
from CRM.widgets.delegates import WrappingItemDelegate
from CRM.dialogs.login import LoginDialog
from CRM.dialogs.startup import StartupDialog
from CRM.dialogs.record import RecordDialog
from CRM.dialogs.comment import CommentDialog
from CRM.dialogs.search import SearchDialog
from CRM.dialogs.report_preview import ReportPreviewDialog
from CRM.modules.data_table import DataTablePage
from CRM.modules.deals import DealModule
from CRM.modules.phase_one import (
    PhaseOneSectionSpec, PhaseOneForm, PhaseOneSectionPage,
    PhaseOneApprovalsPage, PhaseOneSettingsPage, PhaseOneDesk,
    SummaryPage, MatchResultsDialog, ImportPreviewDialog, SettingsListEditor,
)
from CRM.modules.financial import FinancialModule
from CRM.modules.attendance import AttendancePage
from CRM.modules.salary import SalaryPage
from CRM.modules.employees import EmployeesModule
from CRM.modules.reports import ReportsModule
from CRM.modules.ai_insights import AIInsightsModule
from CRM.modules.users import UsersModule
from CRM.modules.settings import SettingsModule
from CRM.modules.success_factors import (
    SFEmployeeCentralPage, SFRecruitingPage, SFPerformancePage,
    SFMustWinBattlesPage, SFKPIsPage, SFLearningPage,
    SFCompensationPage, SFOnboardingPage, SFPositionsPage,
    SFDashboardPage, SuccessFactorsModule,
)
from CRM.modules.workflow import WFDashboardPage, WorkflowModule

