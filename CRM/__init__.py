"""Real Estate CRM - Qt Application Package.

Modules:
  constants.py  - Configuration, constants
  models.py     - FieldSpec, ColumnSpec, TableSpec dataclasses
  services.py   - CRMServices (database, auth, settings)
  database.py   - Schema init, migrations
  utils/        - Utility functions (validation, formatting, parsing)
  widgets/      - UI components (tables, charts, cards)
  dialogs/      - Dialog windows (login, record, search, etc.)
  modules/      - Feature modules (deal, financial, HR, reports)
  app_window.py - ModernCRMWindow (main window)
  main.py       - Entry point
  frontend/     - Web UI files
"""

from .app import *

__version__ = "3.0.0"
