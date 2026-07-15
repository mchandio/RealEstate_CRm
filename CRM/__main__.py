"""Allow running: python3 -m CRM (from project root)."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so CRM.* imports resolve.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from CRM.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
