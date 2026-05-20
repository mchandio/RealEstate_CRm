# CRM Modularization Plan

This project is being moved from one large desktop file into reusable modules.

## Current Production App

- `professional_crm.py`
  - Existing Tkinter CRM.
  - Still the safest app to run for day-to-day use.
  - Now calls the shared report service for rent and sale reports.

## Shared Core Library

- `crm_core/paths.py`
  - Shared project paths such as database and output folders.

- `crm_core/db.py`
  - Small SQLite repository helper.
  - Returns rows as dictionaries so UI code does not need raw sqlite handling.

- `crm_core/reports.py`
  - Rent report generation.
  - Sale report generation.
  - Combined dealings report.
  - TXT, CSV, and PDF export helpers.

## Qt Application

- `qt_crm_app.py`
  - PySide6 CRM UI.
  - Reads the same SQLite database.
  - Uses `crm_core.reports.ReportService`.
  - Includes login, dashboard, rent/sale dealings, workflow, approvals,
    AI-style matching, properties, clients, financials, employees,
    attendance, salary payments, reports, users, settings, export, and backup.
  - Now also carries over the important utility functions from `app.py`:
    form validation, row details/copy, local HTTP API service, fullscreen,
    restart/logout, user guide, roles/permissions, and about dialogs.

Run it with:

```bash
pip install -r requirements.txt
python qt_crm_app.py
```

## Recommended Next Splits

1. Move authentication and settings into `crm_core/auth.py` and `crm_core/settings.py`.
2. Split `qt_crm_app.py` into `crm_qt/widgets.py`, `crm_qt/pages.py`, and `crm_qt/app.py`.
3. Keep `professional_crm.py` as a fallback until the Qt UI has been used successfully in daily work.
