# Centralized styles for the Qt CRM app

def validate_css_fragment(css: str) -> bool:
    """Basic CSS sanity checks: non-empty and balanced braces.
    This is intentionally lightweight; it prevents obvious malformed fragments
    from being applied and causing Qt parse warnings.
    """
    if not css or not isinstance(css, str):
        return False
    # Check balanced braces
    depth = 0
    for ch in css:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def apply_style(widget, css_fragment: str, selector: str | None = None) -> None:
    """Apply a CSS fragment to a widget, wrapping it with a selector if needed
    and validating braces. If invalid, logs a warning and does not apply.
    """
    if not css_fragment or not isinstance(css_fragment, str):
        return
    fragment = css_fragment.strip()
    # If the fragment already contains a selector/style block, use it as-is
    if "{" in fragment and "}" in fragment:
        full = fragment
    else:
        sel = selector or widget.__class__.__name__
        full = f"{sel} {{ {fragment} }}"
    if validate_css_fragment(full):
        try:
            widget.setStyleSheet(full)
        except Exception:
            # Best-effort: silently ignore UI failures
            print(f"Warning: failed to apply style to {widget}")
    else:
        print(f"Warning: invalid CSS fragment skipped: {fragment[:80]}")

try:
    # Prefer premium style if available
    from qt_crm_premium_style import APP_STYLE as PREMIUM_APP_STYLE, DARK_APP_STYLE as PREMIUM_DARK_APP_STYLE
    APP_STYLE = PREMIUM_APP_STYLE
    DARK_APP_STYLE = PREMIUM_DARK_APP_STYLE
except Exception:
    # Fallback application style (extracted from qt_crm_app.py)
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
    padding: 7px 8px;
    min-height: 28px;
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
    padding: 9px 8px;
    font-weight: 800;
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
}
"""
