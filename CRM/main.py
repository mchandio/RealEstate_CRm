"""Application entry point.

Ports the startup flow from the original monolithic qt_crm_app: 
1. Database initialization
2. CRMServices creation
3. Login dialog
4. Splash/startup dialog with progress
5. Main window creation with services + user
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtGui import QIcon

from CRM.database import ensure_database
from CRM.constants import crm_app_icon
from CRM.services import CRMServices
from CRM.dialogs.login import LoginDialog
from CRM.dialogs.startup import StartupDialog
from CRM.app_window import ModernCRMWindow, APP_STYLE


def main() -> int:
    """Initialize database, show login, create window, and run the app."""
    app = QApplication(sys.argv)
    app.setApplicationName("Real Estate CRM")
    app.setOrganizationName("RealEstateCRM")
    icon = crm_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setStyleSheet(APP_STYLE)

    splash: StartupDialog | None = None

    try:
        # ── Phase 1: splash + database ──
        splash = StartupDialog()
        splash.show()
        splash.set_progress(8, "Starting application")
        splash.set_progress(18, "Preparing database")
        ensure_database()

        # ── Phase 2: services + login ──
        splash.set_progress(38, "Loading services")
        services = CRMServices()
        splash.set_progress(48, "Opening login")
        splash.close()
        splash = None

        login = LoginDialog(services)
        if login.exec() != QDialog.Accepted or not login.current_user:
            return 0

        # ── Phase 3: main window ──
        splash = StartupDialog("Loading Real Estate CRM")
        splash.show()
        splash.set_progress(52, "Signing in")

        window = ModernCRMWindow(
            services,
            login.current_user,
            startup_progress=splash.set_progress,
        )
        splash.set_progress(100, "Ready")
        window.show()
        splash.close()
        splash = None

        return app.exec()

    except Exception as exc:
        if splash is not None:
            splash.close()
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Real Estate CRM could not start:\n\n{exc}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
