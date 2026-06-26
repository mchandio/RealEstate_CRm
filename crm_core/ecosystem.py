"""Shared QT_CRM ecosystem contract and health audit helpers."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from crm_core.paths import APP_ROOT, DB_PATH, OUTPUT_DIR


PHASE1_CONTRACT: dict[str, dict[str, Any]] = {
    "rent_requirements": {
        "label": "Rent Requirements",
        "name_column": "client_name",
        "amount_column": "budget",
        "required_columns": [
            "id", "date", "client_name", "client_status", "contact",
            "contact_person", "contact_phone", "property_requires", "size",
            "measurement", "measurement_unit", "floor", "location",
            "bachelor_family", "persons", "facilities",
            "budget", "created_by", "created_at", "last_edited_by",
            "last_edited_at", "is_deleted", "deleted_by", "deleted_at",
        ],
    },
    "rent_availability": {
        "label": "Rent Availability",
        "name_column": "owner_name",
        "amount_column": "monthly_rent",
        "required_columns": [
            "id", "date", "owner_name", "client_broker", "contact",
            "contact_phone", "owner_phone", "property_availability", "size",
            "measurement", "measurement_unit", "floor", "monthly_rent",
            "deposit", "maintenance_charge", "location", "building_name",
            "bachelor_family", "persons",
            "facilities", "created_by", "created_at", "last_edited_by",
            "last_edited_at", "is_deleted", "deleted_by", "deleted_at",
        ],
    },
    "sale_requirements": {
        "label": "Sale Requirements",
        "name_column": "client_name",
        "amount_column": "budget",
        "required_columns": [
            "id", "date", "client_name", "client_status", "contact",
            "contact_person", "contact_phone", "property_requires", "size",
            "measurement", "measurement_unit", "floor", "budget",
            "maintenance_charge", "location",
            "bachelor_family", "facilities", "created_by",
            "created_at", "last_edited_by", "last_edited_at", "is_deleted",
            "deleted_by", "deleted_at",
        ],
    },
    "sale_availability": {
        "label": "Sale Availability",
        "name_column": "owner_name",
        "amount_column": "demand",
        "required_columns": [
            "id", "date", "owner_name", "client_broker", "contact",
            "contact_phone", "owner_phone", "property_availability", "size",
            "measurement", "measurement_unit", "floor", "demand",
            "maintenance_charge", "location", "building_name", "facilities",
            "created_by", "created_at",
            "last_edited_by", "last_edited_at", "is_deleted", "deleted_by",
            "deleted_at",
        ],
    },
}

REQUIRED_SETTING_KEYS = [
    "company_name",
    "currency_symbol",
    "phase1_areas",
    "phase1_facilities",
    "phase1_floors",
    "phase1_property_types",
    "phase1_measurement_units",
    "phase1_theme",
]

RECOMMENDED_MAX_BACKUPS = 30


def _count(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(query, params).fetchone()
    return int(row[0] or 0) if row else 0


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    if not _table_exists(conn, "app_settings"):
        return default
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return str(row["value"] or "") if row else default


def _backup_files() -> list[Path]:
    roots = [APP_ROOT / "backups", OUTPUT_DIR / "backups"]
    seen: set[Path] = set()
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*.db"):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(path)
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)


def collect_ecosystem_health(db_path: Path | str = DB_PATH) -> dict[str, Any]:
    """Inspect the live CRM database and return a UI/API friendly health payload."""

    db_path = Path(db_path)
    generated_at = datetime.now().isoformat(timespec="seconds")
    issues: list[dict[str, str]] = []
    health: dict[str, Any] = {
        "ok": True,
        "status": "Healthy",
        "generated_at": generated_at,
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
            "journal_mode": "",
        },
        "phase1": {},
        "settings": {},
        "users": {},
        "approvals": {},
        "audit": {},
        "backups": {},
        "issues": issues,
    }

    if not db_path.exists():
        issues.append({"severity": "error", "message": f"Database file not found: {db_path}"})
        health["ok"] = False
        health["status"] = "Error"
        return health

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
    except sqlite3.Error as exc:
        issues.append({"severity": "error", "message": f"Database could not be opened: {exc}"})
        health["ok"] = False
        health["status"] = "Error"
        return health

    with conn:
        try:
            journal = conn.execute("PRAGMA journal_mode").fetchone()
            health["database"]["journal_mode"] = str(journal[0]) if journal else ""
        except sqlite3.Error:
            health["database"]["journal_mode"] = "unknown"

        total_active = 0
        total_recycled = 0
        for table, contract in PHASE1_CONTRACT.items():
            if not _table_exists(conn, table):
                issues.append({"severity": "error", "message": f"Missing table: {table}"})
                health["phase1"][table] = {
                    "label": contract["label"],
                    "active": 0,
                    "recycled": 0,
                    "first_serial": None,
                    "last_serial": None,
                    "missing_columns": contract["required_columns"],
                }
                continue

            columns = _table_columns(conn, table)
            missing = [column for column in contract["required_columns"] if column not in columns]
            if missing:
                issues.append({
                    "severity": "error",
                    "message": f"{contract['label']} missing columns: {', '.join(missing)}",
                })
            active = _count(conn, f"SELECT COUNT(*) FROM {table} WHERE COALESCE(is_deleted,0)=0")
            recycled = _count(conn, f"SELECT COUNT(*) FROM {table} WHERE COALESCE(is_deleted,0)=1")
            id_row = conn.execute(
                f"SELECT MIN(id) AS first_id, MAX(id) AS last_id FROM {table} WHERE COALESCE(is_deleted,0)=0"
            ).fetchone()
            total_active += active
            total_recycled += recycled
            health["phase1"][table] = {
                "label": contract["label"],
                "active": active,
                "recycled": recycled,
                "first_serial": id_row["first_id"] if id_row else None,
                "last_serial": id_row["last_id"] if id_row else None,
                "missing_columns": missing,
            }

        health["phase1_total_active"] = total_active
        health["phase1_total_recycled"] = total_recycled

        if _table_exists(conn, "app_settings"):
            settings = {
                "company_name": _setting(conn, "company_name", "MBM Enterprises"),
                "currency_symbol": _setting(conn, "currency_symbol", "Rs."),
                "theme": _setting(conn, "phase1_theme", "Light"),
                "areas_count": len([line for line in _setting(conn, "phase1_areas").splitlines() if line.strip()]),
                "facilities_count": len([line for line in _setting(conn, "phase1_facilities").splitlines() if line.strip()]),
                "floors_count": len([line for line in _setting(conn, "phase1_floors").splitlines() if line.strip()]),
                "missing_keys": [key for key in REQUIRED_SETTING_KEYS if not _setting(conn, key).strip()],
            }
            health["settings"] = settings
            if settings["missing_keys"]:
                issues.append({
                    "severity": "warning",
                    "message": f"Settings need values: {', '.join(settings['missing_keys'])}",
                })
        else:
            issues.append({"severity": "error", "message": "Missing app_settings table"})

        if _table_exists(conn, "users"):
            role_rows = conn.execute(
                "SELECT COALESCE(role,'Staff') AS role, COUNT(*) AS count FROM users GROUP BY COALESCE(role,'Staff')"
            ).fetchall()
            health["users"] = {
                "total": _count(conn, "SELECT COUNT(*) FROM users"),
                "active": _count(conn, "SELECT COUNT(*) FROM users WHERE COALESCE(is_active,0)=1"),
                "inactive": _count(conn, "SELECT COUNT(*) FROM users WHERE COALESCE(is_active,0)=0"),
                "roles": {str(row["role"]): int(row["count"] or 0) for row in role_rows},
            }

        if _table_exists(conn, "pending_approvals"):
            health["approvals"] = {
                "pending": _count(conn, "SELECT COUNT(*) FROM pending_approvals WHERE status='Pending'"),
                "approved": _count(conn, "SELECT COUNT(*) FROM pending_approvals WHERE status='Approved'"),
                "rejected": _count(conn, "SELECT COUNT(*) FROM pending_approvals WHERE status='Rejected'"),
            }

        if _table_exists(conn, "audit_logs"):
            row = conn.execute("SELECT MAX(created_at) AS latest FROM audit_logs").fetchone()
            health["audit"] = {
                "total": _count(conn, "SELECT COUNT(*) FROM audit_logs"),
                "latest": str(row["latest"] or "") if row else "",
            }

    backups = _backup_files()
    latest_backup = backups[0] if backups else None
    health["backups"] = {
        "folder": str(APP_ROOT / "backups"),
        "legacy_folder": str(OUTPUT_DIR / "backups"),
        "count": len(backups),
        "retention_limit": RECOMMENDED_MAX_BACKUPS,
        "latest_path": str(latest_backup) if latest_backup else "",
        "latest_modified": (
            datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat(timespec="seconds")
            if latest_backup
            else ""
        ),
    }
    if not backups:
        issues.append({"severity": "warning", "message": "No database backup found"})
    elif len(backups) > RECOMMENDED_MAX_BACKUPS:
        issues.append({
            "severity": "warning",
            "message": f"Backup folder has {len(backups)} files; recommended maximum is {RECOMMENDED_MAX_BACKUPS}",
        })

    if any(issue["severity"] == "error" for issue in issues):
        health["ok"] = False
        health["status"] = "Error"
    elif issues:
        health["status"] = "Needs Attention"

    return health


def format_ecosystem_report(health: dict[str, Any]) -> str:
    """Format a health payload for the Desktop text dialog."""

    database = health.get("database", {})
    settings = health.get("settings", {})
    users = health.get("users", {})
    approvals = health.get("approvals", {})
    audit = health.get("audit", {})
    backups = health.get("backups", {})
    lines = [
        "QT_CRM ECOSYSTEM HEALTH",
        "=" * 24,
        f"Status: {health.get('status', '-')}",
        f"Generated: {health.get('generated_at', '-')}",
        "",
        "Database",
        f"  Path: {database.get('path', '-')}",
        f"  Exists: {database.get('exists', False)}",
        f"  Size: {int(database.get('size_bytes') or 0) / (1024 * 1024):.2f} MB",
        f"  Journal mode: {database.get('journal_mode', '-')}",
        "",
        "Phase 1 Tables",
    ]
    for table, info in (health.get("phase1") or {}).items():
        lines.append(
            f"  {info.get('label', table)}: active {info.get('active', 0)}, "
            f"recycled {info.get('recycled', 0)}, serial {info.get('last_serial') or '-'} to {info.get('first_serial') or '-'}"
        )
        missing = info.get("missing_columns") or []
        if missing:
            lines.append(f"    Missing columns: {', '.join(missing)}")

    lines.extend([
        "",
        "Settings",
        f"  Company: {settings.get('company_name', '-')}",
        f"  Currency: {settings.get('currency_symbol', '-')}",
        f"  Theme: {settings.get('theme', '-')}",
        f"  Areas / Facilities / Floors: {settings.get('areas_count', 0)} / {settings.get('facilities_count', 0)} / {settings.get('floors_count', 0)}",
        "",
        "Users and Controls",
        f"  Users: {users.get('active', 0)} active, {users.get('inactive', 0)} inactive",
        f"  Roles: {users.get('roles', {})}",
        f"  Pending approvals: {approvals.get('pending', 0)}",
        f"  Audit entries: {audit.get('total', 0)} latest {audit.get('latest', '-')}",
        "",
        "Backups",
        f"  Folder: {backups.get('folder', '-')}",
        f"  Files found: {backups.get('count', 0)} / {backups.get('retention_limit', RECOMMENDED_MAX_BACKUPS)}",
        f"  Latest: {backups.get('latest_path') or '-'}",
        "",
        "Issues",
    ])
    issues = health.get("issues") or []
    if issues:
        for issue in issues:
            lines.append(f"  [{str(issue.get('severity', 'info')).upper()}] {issue.get('message', '')}")
    else:
        lines.append("  No ecosystem issues found.")
    lines.append("")
    lines.append(f"Process ID: {os.getpid()}")
    return "\n".join(lines)
