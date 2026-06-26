import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.main import schedule_system_backup


def test_system_backup_schedule_requires_backup_permission_dependency():
    dependency = inspect.signature(schedule_system_backup).parameters["_user"].default.dependency

    with pytest.raises(HTTPException) as exc:
        dependency(SimpleNamespace(role="Staff"))

    assert exc.value.status_code == 403
    admin = SimpleNamespace(role="Admin")
    assert dependency(admin) is admin


def test_system_backup_schedule_returns_filename_only(monkeypatch):
    import backend.backup as backup_module

    monkeypatch.setattr(
        backup_module,
        "run_database_backup",
        lambda reason: Path("C:/private/crm/backups/scheduled_backup_20260611.db"),
    )

    response = schedule_system_backup(_user=object())

    assert response == {
        "status": "backup_completed",
        "filename": "scheduled_backup_20260611.db",
    }
