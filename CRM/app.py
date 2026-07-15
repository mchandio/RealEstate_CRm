"""CRM Application - Module Orchestrator.

Re-exports all classes and functions from CRM sub-modules.

Usage (from project root):
    python3 -m CRM
"""
from __future__ import annotations

import sys
from pathlib import Path as _Path

# Ensure project root is on sys.path so CRM.* imports resolve
# whether run as 'python3 -m CRM' or 'python3 CRM/app.py'.
_root = str(_Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Import all sub-modules in dependency order (no circular deps)
from CRM.constants import *
from CRM.models import FieldSpec, ColumnSpec, TableSpec
from CRM.services import CRMServices
from CRM.database import ensure_database, ensure_qt_schema
from CRM.utils import *
from CRM.widgets import *
from CRM.dialogs import *
from CRM.modules import *

# Import main window (uses all above)
from CRM.app_window import ModernCRMWindow

# Import entry point
from CRM.main import main
