"""
Premium Qt Desktop Stylesheet for Real Estate CRM
Drop-in replacement for APP_STYLE and DARK_APP_STYLE in qt_crm_app.py
"""

# ── LIGHT THEME ─────────────────────────────────────────────────────────────
APP_STYLE = """
/* ═══════════════════════════════════════════════════════════════════════════
   REAL ESTATE CRM  —  Premium Light Theme
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Root / Window ── */
QMainWindow {
    background: #f1f5f9;
}
QWidget {
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: #0f172a;
}

/* ── Status Bar ── */
QStatusBar#AppStatusBar {
    background: #ffffff;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding: 2px 6px;
    font-size: 11.5px;
}
QLabel#StatusBarLabel {
    color: #475569;
    padding: 0 10px;
    font-size: 11px;
    font-weight: 500;
}

/* ══════════════════════════ SIDEBAR ══════════════════════════════════════ */
#Sidebar {
    background: #0a0f1e;
    border-right: 1px solid #0f172a;
}

/* Brand card */
#BrandCard {
    background: #131d30;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    margin: 2px;
}
#LogoBadge {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #c9a84c,stop:1 #f0c96a);
    color: #0a0f1e;
    border-radius: 9px;
    min-width: 38px; max-width: 38px;
    min-height: 38px; max-height: 38px;
    font-size: 14px;
    font-weight: 900;
    qproperty-alignment: AlignCenter;
}
#LogoImage {
    background: transparent;
    border: none;
}
#Brand {
    color: #ffffff;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: -0.3px;
}
#SidebarSubtle {
    color: rgba(255,255,255,0.32);
    font-size: 11px;
}

/* User card */
#UserCard {
    background: #0d1525;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 11px;
}
#SidebarUserName {
    color: rgba(255,255,255,0.92);
    font-size: 13px;
    font-weight: 700;
}
#RolePill {
    background: rgba(201,168,76,0.18);
    color: #f0c96a;
    border-radius: 7px;
    padding: 3px 10px;
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.2px;
}

/* Sidebar scroll area */
QScrollArea#SidebarNavScroll {
    background: transparent;
    border: none;
}
QScrollArea#SidebarNavScroll QWidget {
    background: transparent;
}
QScrollArea#SidebarNavScroll QScrollBar:vertical {
    background: transparent;
    border: none;
    width: 5px;
    margin: 4px 0;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.15);
    border-radius: 3px;
    min-height: 28px;
}
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical:hover {
    background: rgba(255,255,255,0.28);
}
QScrollArea#SidebarNavScroll QScrollBar::add-line:vertical,
QScrollArea#SidebarNavScroll QScrollBar::sub-line:vertical { height: 0; }

/* Nav shell */
#NavShell { background: transparent; }

/* Nav divider */
#NavSeparator {
    background: rgba(255,255,255,0.07);
    min-height: 1px;
    max-height: 1px;
    margin: 7px 10px 4px 10px;
}

/* Nav section labels */
#NavSection {
    color: rgba(255,255,255,0.22);
    font-size: 9.5px;
    font-weight: 900;
    letter-spacing: 1.3px;
    padding: 10px 10px 3px 10px;
}

/* Nav items */
QFrame#NavItem {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
}
QFrame#NavItem:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(255,255,255,0.08);
}
QFrame#NavItem[active="true"] {
    background: rgba(201,168,76,0.14);
    border: 1px solid rgba(201,168,76,0.22);
}
#NavIndicator { background: transparent; border-radius: 2px; }
#NavIndicator[active="true"] { background: #c9a84c; }

QLabel#NavIcon {
    background: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.4);
    border-radius: 7px;
    font-size: 11px;
    font-weight: 800;
    qproperty-alignment: AlignCenter;
}
QLabel#NavIcon[active="true"] {
    background: rgba(201,168,76,0.2);
    color: #c9a84c;
}
QLabel#NavText {
    color: rgba(255,255,255,0.48);
    font-size: 13px;
    font-weight: 600;
}
QLabel#NavText[active="true"] {
    color: #f0c96a;
    font-weight: 700;
}
QFrame#NavItem:hover QLabel#NavText { color: rgba(255,255,255,0.82); }
QFrame#NavItem:hover QLabel#NavIcon {
    background: rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.75);
}

/* Sidebar footer */
#SidebarFooter {
    background: #0d1525;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
}
#SidebarStatusText {
    color: #93c5fd;
    font-size: 11px;
    font-weight: 700;
}
#StatusDot {
    background: #22c55e;
    border-radius: 5px;
    min-width: 9px; max-width: 9px;
    min-height: 9px; max-height: 9px;
}
#SidebarLogout {
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.62);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 700;
    font-size: 12.5px;
}
#SidebarLogout:hover {
    background: rgba(255,255,255,0.12);
    color: #ffffff;
    border-color: rgba(255,255,255,0.22);
}

/* ══════════════════════════ CONTENT AREA ═════════════════════════════════ */
#Content {
    background: #f1f5f9;
}
#TopTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.4px;
}
#PageTitle {
    color: #0f172a;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
}
#SectionTitle {
    color: #0f172a;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
}
#MutedText {
    color: #64748b;
    font-size: 12.5px;
}
#SelectionCount {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
    background: #e2e8f0;
    border-radius: 7px;
    padding: 3px 10px;
}
#DialogTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -0.3px;
}

/* ══════════════════════════ METRIC CARDS ═════════════════════════════════ */
#MetricCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}
#MetricTitle {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
#MetricValue {
    color: #0f172a;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.8px;
}
#MetricNote {
    color: #94a3b8;
    font-size: 11.5px;
}

/* ══════════════════════════ PANELS ═══════════════════════════════════════ */
#Panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}
#PhaseCard {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    font-size: 20px;
    font-weight: 800;
    padding: 20px;
    text-align: left;
}
#PhaseCard:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: #1d4ed8;
}
#PhaseCard:pressed {
    background: #dbeafe;
}

/* ══════════════════════════ FORM ELEMENTS ════════════════════════════════ */
QLabel#FormLabel {
    color: #374151;
    font-size: 12.5px;
    font-weight: 600;
}
QLabel#RequiredLabel {
    color: #1d4ed8;
    font-size: 12.5px;
    font-weight: 700;
}
QLabel#FormGroupTitle {
    color: #1e3a5f;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 800;
    font-size: 12.5px;
}
QLineEdit, QTextEdit, QDateEdit {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 11px;
    color: #0f172a;
    font-size: 13px;
    selection-background-color: #dbeafe;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
    border-color: #3b82f6;
    background: #fafcff;
}
QLineEdit:hover, QTextEdit:hover, QDateEdit:hover {
    border-color: #94a3b8;
}
QComboBox {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 11px;
    color: #0f172a;
    font-size: 13px;
    selection-background-color: #dbeafe;
}
QComboBox:focus { border-color: #3b82f6; }
QComboBox:hover { border-color: #94a3b8; }
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
    padding: 4px;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    padding: 7px 10px;
    border-radius: 5px;
    min-height: 24px;
}

/* ══════════════════════════ TABLE ════════════════════════════════════════ */
QTableWidget {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    gridline-color: #e9eef5;
    alternate-background-color: #f8fafc;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
    outline: 0;
    padding: 0;
    font-size: 13px;
}
QTableWidget::item {
    color: #0f172a;
    padding: 10px 12px;
    min-height: 38px;
    border: none;
}
QTableWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
QTableWidget::item:hover {
    background: #f0f7ff;
}
QHeaderView::section {
    background: #f1f5f9;
    color: #334155;
    border: none;
    border-bottom: 2px solid #cbd5e1;
    border-right: 1px solid #e2e8f0;
    padding: 11px 14px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QHeaderView::section:first { border-top-left-radius: 10px; }
QHeaderView::section:last { border-top-right-radius: 10px; border-right: none; }
QHeaderView::section:hover {
    background: #f1f5f9;
    color: #1e3a5f;
}
QTableWidget QScrollBar:vertical {
    background: #f8fafc;
    border: none;
    width: 8px;
    margin: 4px 0;
    border-radius: 4px;
}
QTableWidget QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 28px;
}
QTableWidget QScrollBar::handle:vertical:hover { background: #94a3b8; }
QTableWidget QScrollBar::add-line:vertical,
QTableWidget QScrollBar::sub-line:vertical { height: 0; }
QTableWidget QScrollBar:horizontal {
    background: #f8fafc;
    border: none;
    height: 8px;
    margin: 0 4px;
    border-radius: 4px;
}
QTableWidget QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 28px;
}
QTableWidget QScrollBar::handle:horizontal:hover { background: #94a3b8; }
QTableWidget QScrollBar::add-line:horizontal,
QTableWidget QScrollBar::sub-line:horizontal { width: 0; }
QTableWidget QScrollBar::corner { background: #f8fafc; }

/* ══════════════════════════ BUTTONS ══════════════════════════════════════ */
QPushButton {
    background: #ffffff;
    color: #334155;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 12.5px;
}
QPushButton:hover {
    background: #f8fafc;
    border-color: #94a3b8;
    color: #0f172a;
}
QPushButton:pressed {
    background: #f1f5f9;
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
    color: #ffffff;
    border: 1.5px solid #2563eb;
}
#AccentButton:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
#AccentButton:pressed { background: #1e40af; }
#AccentButton:disabled {
    background: #bfdbfe;
    color: #f8fafc;
    border-color: #bfdbfe;
}
#WarningButton {
    background: #fffbeb;
    color: #b45309;
    border: 1.5px solid #fcd34d;
}
#WarningButton:hover {
    background: #fef3c7;
    border-color: #f59e0b;
}
#WarningButton:pressed {
    background: #fde68a;
    border-color: #d97706;
}
#DangerButton {
    background: #fee2e2;
    color: #b91c1c;
    border: 1.5px solid #fca5a5;
}
#DangerButton:hover {
    background: #dc2626;
    color: #ffffff;
    border-color: #dc2626;
}
#DangerButton:pressed {
    background: #991b1b;
    color: #ffffff;
    border-color: #991b1b;
}
#DangerButton:disabled {
    background: #fee2e2;
    color: #fca5a5;
    border-color: #fecaca;
}

/* ══════════════════════════ FACILITIES BOX ═══════════════════════════════ */
#FacilitiesBox {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    padding: 4px;
}
QRadioButton#FacilityCheck {
    background: #ffffff;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 5px 10px;
    font-weight: 600;
    font-size: 12px;
    spacing: 7px;
}
QRadioButton#FacilityCheck:hover {
    background: #eff6ff;
    border-color: #93c5fd;
    color: #1d4ed8;
}
QRadioButton#FacilityCheck:checked {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #1d4ed8;
    font-weight: 800;
}
QRadioButton#FacilityCheck::indicator { width: 0; height: 0; }

/* ══════════════════════════ TABS ═════════════════════════════════════════ */
QTabWidget::pane {
    border: 1.5px solid #e2e8f0;
    background: #ffffff;
    border-radius: 12px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 10px 18px;
    border: none;
    border-bottom: 2.5px solid transparent;
    font-weight: 700;
    font-size: 13px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #2563eb;
    border-bottom-color: #2563eb;
    background: transparent;
}
QTabBar::tab:hover:!selected { color: #374151; }

/* ══════════════════════════ PROGRESS ════════════════════════════════════ */
QProgressBar {
    background: #e2e8f0;
    border: none;
    border-radius: 7px;
    color: #0f172a;
    font-weight: 800;
    font-size: 11px;
    min-height: 16px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563eb,stop:1 #0ea5b0);
    border-radius: 6px;
}

/* ══════════════════════════ SCROLL BARS ══════════════════════════════════ */
QScrollBar:vertical {
    background: #f1f5f9;
    border: none;
    width: 7px;
    margin: 2px 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #f1f5f9;
    border: none;
    height: 7px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover { background: #94a3b8; }
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ══════════════════════════ DIALOGS ══════════════════════════════════════ */
QDialog {
    background: #f8fafc;
}
QDialogButtonBox QPushButton {
    min-width: 90px;
}

/* Login */
#LoginDialog { background: #ffffff; }
#LoginTitle {
    color: #0f172a;
    font-size: 26px;
    font-weight: 900;
    letter-spacing: -0.6px;
}

/* Startup splash */
#StartupDialog {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}
#StartupTitle {
    color: #0f172a;
    font-size: 20px;
    font-weight: 900;
    letter-spacing: -0.4px;
}

/* Menu bar */
QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 2px 6px;
    font-size: 13px;
    font-weight: 600;
}
QMenuBar::item {
    background: transparent;
    color: #374151;
    padding: 6px 12px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #f1f5f9;
    color: #0f172a;
}
QMenuBar::item:pressed {
    background: #dbeafe;
    color: #1d4ed8;
}
QMenu {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 5px;
}
QMenu::item {
    padding: 8px 16px;
    border-radius: 7px;
    font-size: 13px;
    color: #374151;
}
QMenu::item:selected {
    background: #eff6ff;
    color: #1d4ed8;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 4px 8px;
}

/* Compact workflow desk overrides */
#Sidebar {
    background: #1a1f2e;
}
#BrandCard, #UserCard, #SidebarFooter {
    border-radius: 8px;
}
#LogoBadge {
    min-width: 34px; max-width: 34px;
    min-height: 34px; max-height: 34px;
    border-radius: 8px;
    background: #f59e0b;
}
#Brand {
    font-size: 14px;
    font-weight: 850;
}
#SidebarSubtle {
    font-size: 10.5px;
}
#SidebarUserName {
    font-size: 12px;
}
#RolePill {
    background: #fff7ed;
    color: #7c4a03;
    border: 1px solid rgba(245,158,11,0.32);
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 10px;
}
#NavSection {
    font-size: 9px;
    padding: 8px 8px 2px 8px;
}
QFrame#NavItem {
    border-radius: 7px;
}
QLabel#NavIcon {
    border-radius: 6px;
    font-size: 9px;
}
QLabel#NavText {
    font-size: 11.5px;
}
QFrame#NavItem[active="true"] {
    background: rgba(245,158,11,0.13);
    border-color: rgba(245,158,11,0.28);
}
#NavIndicator[active="true"] {
    background: #f59e0b;
}
QLabel#NavText[active="true"],
QLabel#NavIcon[active="true"] {
    color: #fbbf24;
}
#Content {
    background: #eef3f9;
}
#TopBar {
    background: #ffffff;
    border-bottom: 1px solid #d6e1ee;
}
#TopTitle {
    font-size: 15px;
    font-weight: 750;
}
#PageTitle {
    font-size: 24px;
    font-weight: 850;
}
#SectionTitle {
    font-size: 17px;
    font-weight: 850;
}
QPushButton {
    min-height: 30px;
    padding: 5px 11px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 750;
}
#AccentButton {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
#DangerButton {
    background: #fff1f2;
    color: #dc2626;
    border-color: rgba(220,38,38,0.26);
}
#WarningButton {
    background: #fffbeb;
    color: #b45309;
    border-color: rgba(245,158,11,0.32);
}
#SelectionCount {
    min-height: 26px;
    padding: 3px 8px;
    border-radius: 12px;
    background: #f8fafc;
    color: #5f7189;
    font-size: 11px;
}
QTableWidget {
    border-radius: 8px;
    gridline-color: #e2e8f0;
    selection-background-color: #dbeafe;
}
QTableWidget::item {
    padding: 6px 8px;
    min-height: 24px;
    font-size: 11.5px;
}
QHeaderView::section {
    padding: 7px 10px;
    font-size: 10.5px;
    font-weight: 850;
    color: #5f7189;
    background: #f8fafc;
    border-bottom: 1px solid #d6e1ee;
}
"""


# ── DARK THEME ───────────────────────────────────────────────────────────────
DARK_APP_STYLE = APP_STYLE + """
/* ═══════════════════════════════════════════════════════════════════════════
   DARK THEME OVERRIDES
   ═══════════════════════════════════════════════════════════════════════════ */

QMainWindow { background: #0d1117; }
#Content { background: #0d1117; }
QWidget { color: #e2e8f0; }
QDialog { background: #111827; }

#TopTitle, #PageTitle, #SectionTitle { color: #f1f5f9; }
#MutedText { color: #64748b; }
#DialogTitle { color: #f1f5f9; }
#SelectionCount { background: #1e2d45; color: #94a3b8; }

/* Cards */
#MetricCard, #Panel {
    background: #111827;
    border-color: #1e293b;
}
#MetricTitle { color: #64748b; }
#MetricValue { color: #f1f5f9; }
#MetricNote { color: #475569; }

#PhaseCard {
    background: #111827;
    color: #f1f5f9;
    border-color: #1e293b;
}
#PhaseCard:hover {
    background: #172554;
    border-color: #3b82f6;
    color: #93c5fd;
}

/* Form labels */
QLabel#FormLabel { color: #94a3b8; }
QLabel#RequiredLabel { color: #60a5fa; }
QLabel#FormGroupTitle {
    color: #93c5fd;
    background: #0f2344;
    border-color: #1e3a5f;
}

/* Inputs */
QLineEdit, QTextEdit, QDateEdit {
    background: #1e293b;
    border-color: #334155;
    color: #e2e8f0;
}
QLineEdit:focus, QTextEdit:focus, QDateEdit:focus {
    border-color: #3b82f6;
    background: #172034;
}
QLineEdit:hover, QTextEdit:hover, QDateEdit:hover { border-color: #475569; }
QComboBox {
    background: #1e293b;
    border-color: #334155;
    color: #e2e8f0;
}
QComboBox:focus { border-color: #3b82f6; }
QComboBox QAbstractItemView {
    background: #1e293b;
    border-color: #334155;
    selection-background-color: #1d4ed8;
    color: #e2e8f0;
}

/* Table */
QTableWidget {
    background: #111827;
    border-color: #1e293b;
    gridline-color: #1a2234;
    alternate-background-color: #131e2e;
    selection-background-color: #1e3a5f;
    color: #e2e8f0;
}
QTableWidget::item { color: #e2e8f0; padding: 8px 10px; min-height: 30px; }
QTableWidget::item:selected { background: #1e3a5f; color: #f1f5f9; }
QTableWidget::item:hover { background: #18253a; }
QHeaderView::section {
    background: #161f30;
    color: #64748b;
    border-bottom-color: #1e293b;
    border-right-color: #1e293b;
}
QHeaderView::section:hover {
    background: #1e293b;
    color: #94a3b8;
}

/* Buttons */
QPushButton {
    background: #1e293b;
    color: #cbd5e1;
    border-color: #334155;
}
QPushButton:hover {
    background: #263548;
    border-color: #475569;
    color: #f1f5f9;
}
QPushButton:pressed {
    background: #0f172a;
    border-color: #64748b;
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
#AccentButton:disabled {
    background: #172554;
    color: #64748b;
    border-color: #1e3a8a;
}
#WarningButton {
    background: #29200a;
    color: #fcd34d;
    border-color: #854d0e;
}
#WarningButton:hover {
    background: #3b2c0a;
    border-color: #d97706;
}
#WarningButton:pressed {
    background: #422006;
    border-color: #f59e0b;
}
#DangerButton {
    background: #3b0d0d;
    color: #fca5a5;
    border-color: #7f1d1d;
}
#DangerButton:hover {
    background: #dc2626;
    color: #ffffff;
}
#DangerButton:pressed {
    background: #7f1d1d;
    color: #ffffff;
}

/* Facilities */
#FacilitiesBox {
    background: #131e2e;
    border-color: #1e293b;
}
QRadioButton#FacilityCheck {
    background: #1e293b;
    color: #94a3b8;
    border-color: #334155;
}
QRadioButton#FacilityCheck:hover {
    background: #172554;
    border-color: #3b82f6;
    color: #93c5fd;
}
QRadioButton#FacilityCheck:checked {
    background: #1e3a5f;
    border-color: #2563eb;
    color: #93c5fd;
}

/* Tabs */
QTabWidget::pane {
    background: #111827;
    border-color: #1e293b;
}
QTabBar::tab { color: #475569; }
QTabBar::tab:selected {
    color: #60a5fa;
    border-bottom-color: #3b82f6;
}
QTabBar::tab:hover:!selected { color: #94a3b8; }

/* Scrollbars */
QScrollBar:vertical { background: #0d1117; }
QScrollBar::handle:vertical { background: #1e293b; }
QScrollBar::handle:vertical:hover { background: #334155; }
QScrollBar:horizontal { background: #0d1117; }
QScrollBar::handle:horizontal { background: #1e293b; }
QScrollBar::handle:horizontal:hover { background: #334155; }
QTableWidget QScrollBar:vertical { background: #e2e8f0; width: 10px; margin: 2px; }
QTableWidget QScrollBar::handle:vertical { background: #94a3b8; border-radius: 4px; min-height: 28px; }
QTableWidget QScrollBar::handle:vertical:hover { background: #64748b; }
QTableWidget QScrollBar:horizontal { background: #e2e8f0; height: 10px; margin: 2px; }
QTableWidget QScrollBar::handle:horizontal { background: #94a3b8; border-radius: 4px; min-width: 28px; }
QTableWidget QScrollBar::handle:horizontal:hover { background: #64748b; }
QTableWidget QScrollBar::corner { background: #e2e8f0; }
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical { background: rgba(255,255,255,0.08); }
QScrollArea#SidebarNavScroll QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.18); }

/* Menus */
QMenuBar { background: #111827; border-bottom-color: #1e293b; }
QMenuBar::item { color: #94a3b8; }
QMenuBar::item:selected { background: #1e293b; color: #e2e8f0; }
QMenuBar::item:pressed { background: #172554; color: #bfdbfe; }
QMenu { background: #1e293b; border-color: #334155; }
QMenu::item { color: #cbd5e1; }
QMenu::item:selected { background: #172554; color: #93c5fd; }
QMenu::separator { background: #334155; }

/* Status bar */
QStatusBar#AppStatusBar { background: #111827; border-top-color: #1e293b; }
QLabel#StatusBarLabel { color: #64748b; }

/* Login */
#LoginDialog { background: #111827; }
#LoginTitle { color: #f1f5f9; }
#StartupDialog { background: #111827; border-color: #1e293b; }
#StartupTitle { color: #f1f5f9; }

QProgressBar { background: #1e293b; color: #e2e8f0; }
"""


# ── INTEGRATION INSTRUCTIONS ─────────────────────────────────────────────────
INTEGRATION = """
HOW TO INTEGRATE INTO qt_crm_app.py
=====================================

1. Copy this file next to qt_crm_app.py

2. In qt_crm_app.py, replace the existing APP_STYLE and DARK_APP_STYLE
   definitions (the large triple-quoted strings) with:

       from qt_crm_premium_style import APP_STYLE, DARK_APP_STYLE

   OR simply paste the contents of APP_STYLE and DARK_APP_STYLE from this
   file into qt_crm_app.py, replacing the old definitions.

3. No other changes needed — all object names referenced in the stylesheet
   already exist in the codebase.
"""

if __name__ == "__main__":
    print(INTEGRATION)
    print(f"\nAPP_STYLE length   : {len(APP_STYLE):,} chars")
    print(f"DARK_APP_STYLE length: {len(DARK_APP_STYLE):,} chars")
