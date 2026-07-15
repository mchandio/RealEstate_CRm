"""Desktop Server - Local HTTP API for Qt CRM.

Extracts the CRMApiHandler and start/stop logic from ModernCRMWindow.
Uses the AppContext protocol to avoid tight coupling to the main window.
"""
from __future__ import annotations

import json
import os
import re
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, TYPE_CHECKING

from crm_core import DB_PATH
from crm_core.constants import (
    has_permission,
    normalize_contact_role,
    normalize_availability_status,
)
from CRM.constants import (
    LOCAL_SERVICE_PORT,
    DEAL_TABLES,
    GLOBAL_SEARCH_MONEY_COLUMNS,
    GLOBAL_SEARCH_HIDDEN_COLUMNS,
    SF_TABLES,
    WF_TABLES,
    READ_ONLY_API_TABLES,
    PHASE1_TABLES,
    DEAL_STAGES,
    DATE_FORM_KEYS,
    PHONE_FORM_KEYS,
)
from CRM.utils import (
    is_date_key,
    quote_identifier,
    PhoneValidator,
    DateUtils,
    parse_currency,
)

if TYPE_CHECKING:
    from CRM.api.protocol import AppContext


class DesktopServer:
    """Local HTTP API server for the Qt CRM desktop application.

    Runs on LOCAL_SERVICE_PORT and provides RESTful access to CRM tables.
    The server uses threading to avoid blocking the Qt event loop.
    """

    def __init__(self) -> None:
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._server is not None and self._thread is not None

    @property
    def port(self) -> int:
        """Return the port the server is running on."""
        return LOCAL_SERVICE_PORT

    def start(self, app: AppContext) -> None:
        """Start the local HTTP server in a daemon thread.

        Args:
            app: Application context providing access to services and user state.
        """
        if self.is_running:
            return

        def serve() -> None:
            try:
                handler = _create_handler(app)
                self._server = ThreadingHTTPServer(("0.0.0.0", LOCAL_SERVICE_PORT), handler)
                self._server.serve_forever()
            except Exception as exc:
                print(f"Local API Error: {exc}")

        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the local HTTP server and clean up resources."""
        try:
            if self._server:
                self._server.shutdown()
                self._server.server_close()
        except Exception:
            pass
        self._server = None
        self._thread = None


def get_local_ip() -> str:
    """Get the local IP address for network access."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _create_handler(app: AppContext) -> type[BaseHTTPRequestHandler]:
    """Create a CRMApiHandler class bound to the application context.

    This factory function replaces the closure pattern where the handler
    class was defined inside start_local_service().
    """

    class CRMApiHandler(BaseHTTPRequestHandler):
        _rate_limit: dict[str, tuple[datetime, int]] = {}
        _rate_limit_lock = threading.Lock()

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _send(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _check_rate_limit(self) -> bool:
            client = self.client_address[0]
            now = datetime.now()
            with self._rate_limit_lock:
                stale = [ip for ip, (ts, _count) in self._rate_limit.items() if (now - ts).total_seconds() > 60]
                for ip in stale:
                    del self._rate_limit[ip]
                if client in self._rate_limit:
                    last, count = self._rate_limit[client]
                    if (now - last).total_seconds() < 1:
                        count += 1
                        if count > 30:
                            return False
                    else:
                        count = 1
                    self._rate_limit[client] = (now, count)
                else:
                    self._rate_limit[client] = (now, 1)
            return True

        def _table_columns(self, table: str) -> set[str]:
            return app.services.repo.table_columns(table)

        def _clean_payload(self, table: str, data: dict, *, add_create_meta: bool = False) -> tuple[dict, list[str]]:
            columns = self._table_columns(table)
            cleaned = {key: value for key, value in data.items() if key in columns and key != "id"}
            unknown = sorted(key for key in data if key not in columns and key != "id")
            if add_create_meta:
                if "created_by" in columns and "created_by" not in cleaned:
                    cleaned["created_by"] = app.current_user.get("username", "api")
                if "created_at" in columns and "created_at" not in cleaned:
                    cleaned["created_at"] = str(datetime.now())
            return cleaned, unknown

        def _normalize_payload(self, table: str, cleaned: dict) -> tuple[dict, str]:
            number_keys = GLOBAL_SEARCH_MONEY_COLUMNS | {
                "base_salary", "bonus", "deductions", "net_salary", "maintenance_charge",
                "deposit", "sale_price", "allowances", "total_compensation", "target_value",
                "current_value", "actual_value", "progress_pct", "weight_pct",
                "achievement_pct", "score", "actual_hours",
            }
            date_keys = {
                key for key in cleaned
                if is_date_key(key) or key in {"due_at", "assigned_at", "completed_at"}
            }
            try:
                for key in set(cleaned) & PHONE_FORM_KEYS:
                    cleaned[key] = PhoneValidator.validate_phone(cleaned.get(key))
                for key in date_keys:
                    if cleaned.get(key) not in (None, ""):
                        cleaned[key] = DateUtils.store_date(cleaned.get(key))
                for key in set(cleaned) & number_keys:
                    if cleaned.get(key) in (None, ""):
                        cleaned[key] = 0
                        continue
                    number = parse_currency(cleaned.get(key))
                    if number is None:
                        return cleaned, f"{key} must be a number"
                    if number < 0:
                        return cleaned, f"{key} cannot be negative"
                    cleaned[key] = number
                if table in {"rent_requirements", "sale_requirements"} and "client_status" in cleaned:
                    cleaned["client_status"] = normalize_contact_role(cleaned.get("client_status"), "Client")
                if table in {"rent_availability", "sale_availability"}:
                    if "client_broker" in cleaned:
                        cleaned["client_broker"] = normalize_contact_role(cleaned.get("client_broker"), "Owner")
                    if "status" in cleaned:
                        cleaned["status"] = normalize_availability_status(cleaned.get("status"), "Available")
            except ValueError as exc:
                return cleaned, str(exc)
            return cleaned, ""

        def do_OPTIONS(self) -> None:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
            self.end_headers()

        def do_GET(self) -> None:
            if not self._check_rate_limit():
                self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                return
            from urllib.parse import parse_qs

            path, _, query = self.path.partition("?")
            params = {key: values[-1] for key, values in parse_qs(query).items()}
            if path in ("/", "/index"):
                self._send({
                    "ok": True,
                    "service": "realestate-crm-api",
                    "version": "qt-1.0",
                    "message": "Qt CRM API is running",
                    "routes": ["/health", "/meta", "/users", "/stats", "/pipeline", "/search?q=term", "/records/<table>"],
                })
                return
            if path in ("/health", "/healthz"):
                self._send({"ok": True, "service": "realestate-crm-api", "port": LOCAL_SERVICE_PORT})
                return
            if path == "/meta":
                self._send({
                    "ok": True,
                    "company": app.company_name,
                    "user": app.current_user.get("full_name"),
                    "role": app.role,
                    "url": app.local_service_url,
                    "db_size": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
                    "expense_categories": app.services.expense_categories(),
                })
                return
            if path == "/users":
                if not has_permission(app.role, "users"):
                    self._send({"ok": False, "error": "access denied"}, 403)
                    return
                rows = app.services.fetch_all("SELECT id, username, full_name, email, role, is_active, last_login FROM users ORDER BY id")
                self._send({"ok": True, "users": rows})
                return
            if path == "/stats":
                stats = {}
                for table in sorted(app.api_allowed_tables()):
                    row = app.services.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
                    stats[table] = row["count"] if row else 0
                self._send({"ok": True, "stats": stats})
                return
            if path == "/pipeline":
                stage = params.get("stage") or None
                if stage and stage not in DEAL_STAGES:
                    self._send({"ok": False, "error": f"invalid stage. allowed: {DEAL_STAGES}"}, 400)
                    return
                rows = app.pipeline_rows(stage)
                self._send({"ok": True, "stage": stage or "All", "count": len(rows), "totals": app.pipeline_counts(), "rows": rows})
                return
            if path in ("/options", "/records/options"):
                self._send({
                    "ok": True,
                    "expense_categories": app.services.expense_categories(),
                    "tables": {
                        "expense_transactions": {
                            "expense_category": app.services.expense_categories(),
                        },
                    },
                })
                return
            if path.startswith("/records/"):
                table = path.replace("/records/", "", 1).strip().lower()
                if table not in app.api_allowed_tables():
                    self._send({"ok": False, "error": f"invalid table. allowed: {sorted(app.api_allowed_tables())}"}, 400)
                    return
                try:
                    limit = min(int(params.get("limit", 500)), 2000)
                    offset = int(params.get("offset", 0))
                except ValueError:
                    self._send({"ok": False, "error": "limit and offset must be integers"}, 400)
                    return
                columns = self._table_columns(table)
                where_parts: list[str] = []
                sql_params: list[Any] = []
                if "is_deleted" in columns:
                    where_parts.append("COALESCE(is_deleted, 0)=0")
                keyword = (params.get("keyword") or params.get("q") or "").strip()
                if keyword:
                    searchable = [
                        column for column in sorted(columns)
                        if column not in {"password_hash", "is_deleted", "deleted_by", "deleted_at"}
                    ]
                    if searchable:
                        where_parts.append(
                            "(" + " OR ".join(f"LOWER(CAST(COALESCE({quote_identifier(column)}, '') AS TEXT)) LIKE ?" for column in searchable) + ")"
                        )
                        sql_params.extend([f"%{keyword.lower()}%"] * len(searchable))
                stage = params.get("stage")
                if stage and "workflow_stage" in columns:
                    where_parts.append(f"{quote_identifier('workflow_stage')}=?")
                    sql_params.append(stage)
                status = params.get("status")
                if status and "status" in columns:
                    where_parts.append(f"{quote_identifier('status')}=?")
                    sql_params.append(status)
                if table == "broker_contacts":
                    for filter_key in ("area", "office_address", "home_address"):
                        filter_value = (params.get(filter_key) or "").strip()
                        if not filter_value or filter_key not in columns:
                            continue
                        terms = [term.strip().lower() for term in re.split(r"[,;]+", filter_value) if term.strip()]
                        if terms:
                            quoted = quote_identifier(filter_key)
                            where_parts.append(
                                "(" + " OR ".join(
                                    f"LOWER(CAST(COALESCE({quoted}, '') AS TEXT)) LIKE ?" for _term in terms
                                ) + ")"
                            )
                            sql_params.extend([f"%{term}%" for term in terms])
                date_key = next(
                    (
                        key for key in (
                            "date", "transaction_date", "payment_date", "hire_date",
                            "open_date", "close_date", "due_date", "assigned_date",
                            "completion_date", "effective_date", "initiated_at", "assigned_at",
                            "due_at", "completed_at", "requested_at", "reviewed_at",
                            "sent_at", "read_at", "logged_at", "performed_at",
                            "created_at", "last_edited_at",
                        )
                        if key in columns
                    ),
                    None,
                )
                start = params.get("start_date") or params.get("date_from")
                end = params.get("end_date") or params.get("date_to")
                try:
                    if date_key and start:
                        where_parts.append(f"date({quote_identifier(date_key)}) >= date(?)")
                        sql_params.append(DateUtils.store_date(start))
                    if date_key and end:
                        where_parts.append(f"date({quote_identifier(date_key)}) <= date(?)")
                        sql_params.append(DateUtils.store_date(end))
                except ValueError as exc:
                    self._send({"ok": False, "error": str(exc)}, 400)
                    return
                default_sort = "area" if table == "broker_contacts" else "id"
                default_direction = "asc" if table == "broker_contacts" else "desc"
                sort_key = (params.get("sort_by") or params.get("sort") or default_sort).strip()
                if sort_key not in columns:
                    self._send({"ok": False, "error": f"invalid sort_by: {sort_key}"}, 400)
                    return
                direction = (params.get("sort_order") or params.get("direction") or default_direction).strip().upper()
                if direction not in {"ASC", "DESC"}:
                    self._send({"ok": False, "error": "invalid sort direction"}, 400)
                    return
                where_sql = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
                total_row = app.services.fetch_one(
                    f"SELECT COUNT(*) AS count FROM {quote_identifier(table)}{where_sql}",
                    tuple(sql_params),
                )
                order_sql = f" ORDER BY {quote_identifier(sort_key)} {direction}"
                if sort_key != "id" and "id" in columns:
                    order_sql += f", {quote_identifier('id')} DESC"
                rows = app.services.fetch_all(
                    f"SELECT * FROM {quote_identifier(table)}{where_sql}{order_sql} LIMIT ? OFFSET ?",
                    tuple(sql_params + [limit, offset]),
                )
                self._send({"ok": True, "table": table, "count": len(rows), "total": total_row["count"] if total_row else 0, "rows": rows})
                return
            if path == "/search":
                q = params.get("q", "").strip().lower()
                if not q:
                    self._send({"ok": False, "error": "query param 'q' is required"}, 400)
                    return
                results = []
                pattern = f"%{q}%"
                for source, table in app.find_sources():
                    columns = [
                        column
                        for column in sorted(app.services.repo.table_columns(table))
                        if column not in GLOBAL_SEARCH_HIDDEN_COLUMNS
                    ]
                    if not columns:
                        continue
                    source_text = f"{source} {table.replace('_', ' ')}".lower()
                    if q in source_text:
                        rows = app.services.fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 20")
                    else:
                        where = " OR ".join(f"LOWER(CAST(COALESCE(\"{col}\", '') AS TEXT)) LIKE ?" for col in columns)
                        rows = app.services.fetch_all(f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT 20", tuple([pattern] * len(columns)))
                    for row in rows:
                        fields = {column: row.get(column) for column in columns}
                        label = (
                            fields.get("client_name")
                            or fields.get("owner_name")
                            or fields.get("name")
                            or fields.get("full_name")
                            or fields.get("title")
                            or fields.get("property_code")
                            or fields.get("id")
                        )
                        detail = (
                            fields.get("contact")
                            or fields.get("contact_phone")
                            or fields.get("owner_phone")
                            or fields.get("phone")
                            or fields.get("owner_contact")
                            or fields.get("email")
                            or fields.get("location")
                            or fields.get("area")
                            or ""
                        )
                        results.append({
                            "table": table,
                            "source": source,
                            "id": row.get("id"),
                            "label": str(label or ""),
                            "detail": str(detail or ""),
                            "fields": fields,
                        })
                self._send({"ok": True, "query": q, "count": len(results), "results": results})
                return
            self._send({"ok": False, "error": "not found"}, 404)

        def do_POST(self) -> None:
            self._write_record("POST")

        def do_PUT(self) -> None:
            self._write_record("PUT")

        def _write_record(self, method: str) -> None:
            if not self._check_rate_limit():
                self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                return
            path = self.path.split("?", 1)[0]
            parts = path.strip("/").split("/")
            if method == "POST":
                if len(parts) != 2 or parts[0] != "records":
                    self._send({"ok": False, "error": "POST requires /records/<table>"}, 400)
                    return
                table = parts[1].lower()
                row_id = None
            else:
                if len(parts) != 3 or parts[0] != "records":
                    self._send({"ok": False, "error": "PUT requires /records/<table>/<id>"}, 400)
                    return
                table = parts[1].lower()
                try:
                    row_id = int(parts[2])
                except ValueError:
                    self._send({"ok": False, "error": "invalid id"}, 400)
                    return
            if table not in app.api_allowed_tables():
                self._send({"ok": False, "error": "invalid table"}, 400)
                return
            if not app.api_can_write_table(table):
                self._send({"ok": False, "error": "write access denied"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8") if length else "{}"
                data = json.loads(body)
            except Exception:
                self._send({"ok": False, "error": "invalid JSON body"}, 400)
                return
            if not isinstance(data, dict) or not data:
                self._send({"ok": False, "error": "empty body"}, 400)
                return
            cleaned, unknown = self._clean_payload(table, data, add_create_meta=(method == "POST"))
            if unknown:
                self._send({"ok": False, "error": f"unknown fields: {unknown}"}, 400)
                return
            if not cleaned:
                self._send({"ok": False, "error": "no valid fields to save"}, 400)
                return
            cleaned, validation_error = self._normalize_payload(table, cleaned)
            if validation_error:
                self._send({"ok": False, "error": validation_error}, 422)
                return
            try:
                if method == "POST":
                    cols = ", ".join(quote_identifier(col) for col in cleaned)
                    placeholders = ", ".join("?" for _ in cleaned)
                    new_id = app.services.insert(f"INSERT INTO {quote_identifier(table)} ({cols}) VALUES ({placeholders})", tuple(cleaned.values()))
                    app.after_record_saved(table, new_id)
                    self._send({"ok": True, "table": table, "id": new_id, "message": "record created"}, 201)
                else:
                    set_clause = ", ".join(f"{quote_identifier(key)}=?" for key in cleaned)
                    changed = app.services.execute(f"UPDATE {quote_identifier(table)} SET {set_clause} WHERE id=?", tuple(cleaned.values()) + (row_id,))
                    if changed <= 0:
                        self._send({"ok": False, "error": "record not found"}, 404)
                        return
                    app.after_record_saved(table, row_id)
                    self._send({"ok": True, "table": table, "id": row_id, "message": "record updated"})
            except Exception as exc:
                self._send({"ok": False, "error": str(exc)}, 500)

        def do_DELETE(self) -> None:
            if not self._check_rate_limit():
                self._send({"ok": False, "error": "rate limit exceeded"}, 429)
                return
            parts = self.path.split("?", 1)[0].strip("/").split("/")
            if len(parts) != 3 or parts[0] != "records":
                self._send({"ok": False, "error": "DELETE requires /records/<table>/<id>"}, 400)
                return
            table = parts[1].lower()
            if table not in app.api_allowed_tables():
                self._send({"ok": False, "error": "invalid table"}, 400)
                return
            if not app.api_can_write_table(table):
                self._send({"ok": False, "error": "write access denied"}, 403)
                return
            try:
                row_id = int(parts[2])
            except ValueError:
                self._send({"ok": False, "error": "invalid id"}, 400)
                return
            try:
                ok, message = app.can_delete_record(table, row_id)
                if not ok:
                    self._send({"ok": False, "error": message}, 409)
                    return
                columns = self._table_columns(table)
                if "is_deleted" in columns:
                    changed = app.services.execute(
                        f"UPDATE {quote_identifier(table)} SET is_deleted=1, deleted_by=?, deleted_at=? WHERE id=?",
                        (app.current_user.get("username", "api"), datetime.now().isoformat(timespec="seconds"), row_id),
                    )
                else:
                    changed = app.services.execute(f"DELETE FROM {quote_identifier(table)} WHERE id=?", (row_id,))
                if changed <= 0:
                    self._send({"ok": False, "error": "record not found"}, 404)
                    return
                app.log_audit("delete", table, row_id)
                self._send({"ok": True, "table": table, "id": row_id, "message": "record recycled" if "is_deleted" in columns else "record deleted"})
            except Exception as exc:
                self._send({"ok": False, "error": str(exc)}, 500)

    return CRMApiHandler
