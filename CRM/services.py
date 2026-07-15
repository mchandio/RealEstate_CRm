"""CRM Services Layer."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Any
from crm_core import DB_PATH
from crm_core.db import SQLiteRepository
from crm_core.constants import EXPENSE_CATEGORIES
from CRM.utils import setting_lines

class CRMServices:
    def __init__(self):
        self.repo = SQLiteRepository(DB_PATH)

    def fetch_all(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> list[dict]:
        return self.repo.fetch_all(query, params)

    def fetch_one(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> dict | None:
        return self.repo.fetch_one(query, params)

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        return self.repo.execute(query, params)

    def insert(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> int:
        with self.repo.connect() as conn:
            cur = conn.execute(query, params)
            conn.commit()
            return int(cur.lastrowid)

    def settings_get(self, key: str, default: str = "") -> str:
        row = self.fetch_one("SELECT value FROM app_settings WHERE key=?", (key,))
        return str(row["value"]) if row else default

    def settings_set(self, key: str, value: str) -> None:
        self.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?,?)", (key, value))

    def expense_categories(self) -> list[str]:
        return setting_lines(self, "expense_categories", list(EXPENSE_CATEGORIES))

    def table_columns(self, table: str) -> set[str]:
        return self.repo.table_columns(table)

    def submit_approval(
        self,
        action: str,
        table_name: str,
        record_id: int | None,
        payload: dict[str, Any],
        requested_by: str,
    ) -> int:
        return self.insert(
            """INSERT INTO pending_approvals
               (action, table_name, record_id, payload, requested_by, requested_at, status)
               VALUES (?,?,?,?,?,?, 'Pending')""",
            (action, table_name, record_id, json.dumps(payload, default=str), requested_by, datetime.now().isoformat(timespec="seconds")),
        )

    def pending_approvals(self) -> list[dict]:
        return self.fetch_all(
            """SELECT id, action, table_name, record_id, requested_by, requested_at, status
               FROM pending_approvals
               WHERE status='Pending'
               ORDER BY id DESC"""
        )

    def review_approval(self, approval_id: int, approved: bool, reviewed_by: str, comment: str = "") -> None:
        status = "Approved" if approved else "Rejected"
        self.execute(
            """UPDATE pending_approvals
               SET status=?, reviewed_by=?, reviewed_at=?, review_comment=?
               WHERE id=?""",
            (status, reviewed_by, datetime.now().isoformat(timespec="seconds"), comment, approval_id),
        )

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username: str, password: str) -> dict | None:
        username = str(username or "").strip()
        row = self.fetch_one(
            "SELECT * FROM users WHERE LOWER(TRIM(username))=LOWER(?) AND is_active=1",
            (username,),
        )
        if row and row.get("password_hash") == self.hash_password(password):
            now = datetime.now()
            self.execute("UPDATE users SET last_login=? WHERE id=?", (now, row["id"]))
            self.execute(
                "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
                (row["id"], now, "Success"),
            )
            return row
        self.execute(
            "INSERT INTO login_logs (user_id, login_time, status) VALUES (?,?,?)",
            (None, datetime.now(), "Failed"),
        )
        return None

    def create_user(self, username: str, password: str, full_name: str, email: str, role: str) -> tuple[bool, str]:
        username = str(username or "").strip()
        if not username:
            return False, "Username is required."
        if self.fetch_one("SELECT id FROM users WHERE LOWER(TRIM(username))=LOWER(?)", (username,)):
            return False, "Username already exists."
        self.execute(
            """INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at)
               VALUES (?,?,?,?,?,1,?)""",
            (username, self.hash_password(password), full_name, email, role, datetime.now()),
        )
        return True, "User created."

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        row = self.fetch_one("SELECT password_hash FROM users WHERE id=?", (user_id,))
        if not row:
            return False, "User not found."
        if row["password_hash"] != self.hash_password(old_password):
            return False, "Current password is incorrect."
        self.execute("UPDATE users SET password_hash=? WHERE id=?", (self.hash_password(new_password), user_id))
        return True, "Password changed."
