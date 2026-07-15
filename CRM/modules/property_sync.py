"""Property sync and deal contact logic extracted from ModernCRMWindow.

Provides PropertySyncService that handles:
- Client contact upsert from deal records
- Property matching and syncing from availability records
- Archiving closed availability records
- Phase1 alias normalization
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from crm_core.constants import (
    normalize_contact_role,
    normalize_availability_status,
    CLOSED_AVAILABILITY_ARCHIVES,
)

from CRM.constants import (
    DEAL_TABLES,
    GLOBAL_SEARCH_SOURCE_LABELS,
    PY_DATE_STORAGE_FORMAT,
)
from CRM.utils import (
    safe_float,
    gen_id,
    quote_identifier,
    PhoneValidator,
    DateUtils,
)


class PropertySyncService:
    """Handles property sync, client upsert, and deal contact management.

    This service receives a reference to the host application to access
    services, current user, and other state.
    """

    def __init__(self, host: Any) -> None:
        self.host = host

    @property
    def services(self) -> Any:
        return self.host.services

    # ── Contact extraction ────────────────────────────────────────────

    def _owner_broker_type(self, value: Any, default: str) -> str:
        text = str(value or "").strip().lower()
        if text in {"b", "broker"}:
            return "Broker"
        if text in {"o", "owner"}:
            return "Owner"
        return default

    def deal_client_contacts(self, table: str, row: dict) -> list[dict[str, str]]:
        """Extract client contacts from a deal record."""
        contacts: list[dict[str, str]] = []
        if table in {"rent_requirements", "sale_requirements"}:
            default_type = "Tenant" if table.startswith("rent") else "Buyer"
            contacts.append({
                "name": str(row.get("client_name") or "").strip(),
                "phone": str(row.get("contact_phone") or row.get("contact") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_status"), default_type),
            })
        elif table in {"rent_availability", "sale_availability"}:
            contacts.append({
                "name": str(row.get("owner_name") or "").strip(),
                "phone": str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip(),
                "email": str(row.get("contact_email") or "").strip(),
                "type": self._owner_broker_type(row.get("client_broker"), "Owner"),
            })
        for key in ("broker", "preferred_broker", "posted_by_broker", "posted_by", "client_broker"):
            broker = str(row.get(key) or "").strip()
            if broker and broker.lower() not in {"o", "b", "owner", "broker", "direct", "client"}:
                contacts.append({"name": broker, "phone": "", "email": "", "type": "Broker"})
        return contacts

    # ── Client upsert ─────────────────────────────────────────────────

    def upsert_client_from_deal(self, table: str, row: dict) -> None:
        """Create or update a client record from a deal record."""
        if table not in DEAL_TABLES:
            return
        for contact in self.deal_client_contacts(table, row):
            name = contact["name"]
            if not name:
                continue
            phone = contact["phone"]
            email = contact["email"]
            client_type = contact["type"] or "Other"
            notes = f"Auto-synced from {GLOBAL_SEARCH_SOURCE_LABELS.get(table, table)} #{row.get('id') or ''}".strip()
            existing = None
            if phone:
                existing = self.services.fetch_one("SELECT id FROM clients WHERE phone=? LIMIT 1", (phone,))
            if not existing:
                existing = self.services.fetch_one("SELECT id FROM clients WHERE LOWER(client_name)=LOWER(?) LIMIT 1", (name,))
            if existing:
                self.services.execute(
                    """UPDATE clients
                       SET client_name=COALESCE(NULLIF(client_name,''), ?),
                           phone=COALESCE(NULLIF(phone,''), ?),
                           email=COALESCE(NULLIF(email,''), ?),
                           client_type=COALESCE(NULLIF(client_type,''), ?),
                           status=COALESCE(NULLIF(status,''), 'Active'),
                           notes=COALESCE(NULLIF(notes,''), ?)
                       WHERE id=?""",
                    (name, phone, email, client_type, notes, existing["id"]),
                )
            else:
                self.services.insert(
                    """INSERT INTO clients (client_name, phone, email, client_type, status, notes, created_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (name, phone, email, client_type, "Active", notes, datetime.now()),
                )

    # ── Property matching ─────────────────────────────────────────────

    def property_match(self, row: dict, title: str, property_type: str) -> dict | None:
        """Find an existing property that matches the given row data."""
        location = str(row.get("location") or "").strip()
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip()
        floor = str(row.get("floor") or row.get("floor_no") or "").strip()
        if owner_contact and location:
            params: list[Any] = [owner_contact, location]
            where = [
                "owner_contact=?",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            if floor:
                floor_where = where + ["LOWER(COALESCE(floor,''))=LOWER(?)"]
                found = self.services.fetch_one(
                    f"SELECT id FROM properties WHERE {' AND '.join(floor_where)} LIMIT 1",
                    tuple(params + [floor]),
                )
                if found:
                    return found
            found = self.services.fetch_one(
                f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1",
                tuple(params),
            )
            if found:
                return found
        if owner_name and location:
            params = [owner_name, location]
            where = [
                "LOWER(COALESCE(owner_name,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if title and location:
            params = [title, location]
            where = [
                "LOWER(COALESCE(title,''))=LOWER(?)",
                "LOWER(COALESCE(location,''))=LOWER(?)",
            ]
            if property_type:
                where.append("LOWER(COALESCE(property_type,''))=LOWER(?)")
                params.append(property_type)
            found = self.services.fetch_one(f"SELECT id FROM properties WHERE {' AND '.join(where)} LIMIT 1", tuple(params))
            if found:
                return found
        if owner_contact and not location:
            return self.services.fetch_one("SELECT id FROM properties WHERE owner_contact=? LIMIT 1", (owner_contact,))
        return None

    # ── Property sync ─────────────────────────────────────────────────

    def availability_property_status(self, table: str, row: dict) -> str:
        """Determine the effective status for an availability record."""
        try:
            status = normalize_availability_status(row.get("status"), "Available")
        except ValueError:
            status = str(row.get("status") or "Available").strip()
        stage = str(row.get("workflow_stage") or "").strip()
        if stage == "Pending" and status == "Available":
            return "Pending"
        if table == "rent_availability" and status == "Sold":
            return "Available"
        if table == "sale_availability" and status == "Rented":
            return "Available"
        return status

    def sync_property_from_availability(self, table: str, row: dict, status: str) -> int | None:
        """Sync an availability record to the properties table."""
        if table not in {"rent_availability", "sale_availability"}:
            return None
        property_type = str(row.get("property_availability") or row.get("property_type") or "").strip()
        location = str(row.get("location") or "").strip()
        if not property_type and not location:
            return None
        title = f"{property_type or 'Property'} - {location or 'Location'}"
        owner_name = str(row.get("owner_name") or "").strip()
        owner_contact = str(row.get("owner_phone") or row.get("contact_phone") or row.get("contact") or "").strip()
        area = " ".join(str(row.get(key) or "").strip() for key in ("size", "measurement") if row.get(key)).strip()
        maintenance = safe_float(row.get("maintenance_charge"))
        description = str(row.get("remarks") or row.get("description") or "").strip()
        fields = {
            "title": title,
            "property_type": property_type,
            "status": status,
            "owner_name": owner_name,
            "owner_contact": owner_contact,
            "location": location,
            "area": area,
            "floor": row.get("floor") or row.get("floor_no") or "",
            "maintenance_charge": maintenance,
            "facilities": row.get("facilities") or "",
            "description": description,
        }
        if table.startswith("rent"):
            fields["monthly_rent"] = safe_float(row.get("monthly_rent"))
        elif table.startswith("sale"):
            fields["sale_price"] = safe_float(row.get("demand") or row.get("asking_price"))
        existing = self.property_match(row, title, property_type)
        if existing:
            assignments = ", ".join(f"{key}=?" for key in fields)
            self.services.execute(
                f"UPDATE properties SET {assignments} WHERE id=?",
                tuple(fields.values()) + (existing["id"],),
            )
            return int(existing["id"])
        fields["property_code"] = gen_id("PROP")
        fields["created_at"] = datetime.now()
        columns = ["property_code", "title", "property_type", "status", "owner_name", "owner_contact", "location", "area", "floor", "monthly_rent", "sale_price", "maintenance_charge", "facilities", "description", "created_at"]
        return self.services.insert(
            f"INSERT INTO properties ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
            tuple(fields.get(column) for column in columns),
        )

    # ── Archiving ─────────────────────────────────────────────────────

    def archive_closed_availability(self, table: str, record_id: int, archived_by: str | None = None) -> bool:
        """Archive a closed availability record to the archive table."""
        rule = CLOSED_AVAILABILITY_ARCHIVES.get(table)
        if not rule:
            return False
        closed_status, archive_table, deal_type = rule
        row = self.services.fetch_one(f"SELECT * FROM {quote_identifier(table)} WHERE id=?", (record_id,))
        if not row:
            return False
        try:
            status = normalize_availability_status(row.get("status"), "Available")
        except ValueError:
            status = str(row.get("status") or "").strip()
        if status != closed_status:
            return False
        archive_columns = self.services.table_columns(archive_table)
        source_columns = self.services.table_columns(table)
        if not archive_columns:
            return False
        now = datetime.now().isoformat(timespec="seconds")
        username = archived_by or str(self.host.current_user.get("username") or "system")
        copy_columns = [
            "date", "owner_name", "owner_phone", "contact_phone", "contact",
            "property_availability", "size", "measurement", "measurement_unit",
            "monthly_rent", "demand", "deposit", "maintenance_charge", "floor",
            "location", "bedrooms", "bathrooms", "furnishing", "parking",
            "nearby_landmarks", "area_notes", "verification_status", "photo_paths",
            "facilities", "client_broker", "bachelor_family", "remarks", "persons",
            "building_name", "workflow_stage", "priority", "assigned_to",
            "deal_probability", "expected_close_value", "approval_status",
            "created_by", "created_at",
        ]
        archive_data: dict[str, Any] = {
            "source_table": table,
            "source_id": record_id,
            "deal_type": deal_type,
            "closed_status": closed_status,
            "closed_at": row.get("closed_at") or now,
            "archived_at": now,
            "archived_by": username,
            "workflow_stage": row.get("workflow_stage") or "Deal Done",
            "deal_probability": row.get("deal_probability") or 100,
            "original_payload": json.dumps(row, default=str, ensure_ascii=True),
        }
        for column in copy_columns:
            if column in archive_columns:
                archive_data.setdefault(column, row.get(column))
        keys = [key for key in archive_data if key in archive_columns]
        existing = self.services.fetch_one(
            f"SELECT id FROM {quote_identifier(archive_table)} WHERE source_table=? AND source_id=?",
            (table, record_id),
        )
        if existing:
            update_keys = [key for key in keys if key not in {"source_table", "source_id"}]
            assignments = ", ".join(f"{quote_identifier(key)}=?" for key in update_keys)
            self.services.execute(
                f"UPDATE {quote_identifier(archive_table)} SET {assignments} WHERE id=?",
                tuple(archive_data[key] for key in update_keys) + (existing["id"],),
            )
        else:
            placeholders = ", ".join("?" for _ in keys)
            self.services.insert(
                f"INSERT INTO {quote_identifier(archive_table)} "
                f"({', '.join(quote_identifier(key) for key in keys)}) VALUES ({placeholders})",
                tuple(archive_data[key] for key in keys),
            )
        updates = []
        params: list[Any] = []
        if "status" in source_columns:
            updates.append("status=?")
            params.append(closed_status)
        if "workflow_stage" in source_columns:
            updates.append("workflow_stage=?")
            params.append("Deal Done")
        if "deal_probability" in source_columns:
            updates.append("deal_probability=?")
            params.append(100)
        if "closed_at" in source_columns:
            updates.append("closed_at=COALESCE(closed_at, ?)")
            params.append(now)
        if "is_deleted" in source_columns:
            updates.append("is_deleted=1")
        if "deleted_by" in source_columns:
            updates.append("deleted_by=?")
            params.append(username)
        if "deleted_at" in source_columns:
            updates.append("deleted_at=?")
            params.append(now)
        if updates:
            params.append(record_id)
            self.services.execute(
                f"UPDATE {quote_identifier(table)} SET {', '.join(updates)} WHERE id=?",
                tuple(params),
            )
        self.host.log_audit(f"archive_{closed_status.lower()}", table, record_id, new_value=archive_table)
        return True

    # ── Phase1 alias normalization ────────────────────────────────────

    def sync_phase1_aliases(self, table: str, row: dict) -> None:
        """Normalize Phase1 field aliases after a record is saved."""
        if table not in DEAL_TABLES or not row.get("id"):
            return
        columns = self.services.table_columns(table)
        updates: dict[str, Any] = {}
        if row.get("date") not in (None, "") and "date" in columns:
            try:
                updates["date"] = DateUtils.store_date(row.get("date"))
            except ValueError:
                pass
        if table in {"rent_requirements", "sale_requirements"}:
            try:
                updates["client_status"] = normalize_contact_role(row.get("client_status"), "Client")
            except ValueError:
                pass
            phone = PhoneValidator.normalize(row.get("contact") or row.get("contact_phone"))
            if phone:
                for key in ("contact", "contact_phone"):
                    if key in columns:
                        updates[key] = phone
            if "contact_person" in columns:
                updates["contact_person"] = row.get("client_name") or row.get("contact_person") or ""
        else:
            try:
                updates["client_broker"] = normalize_contact_role(row.get("client_broker"), "Owner")
            except ValueError:
                pass
            if "status" in columns:
                try:
                    updates["status"] = normalize_availability_status(row.get("status"), "Available")
                except ValueError:
                    pass
            phone = PhoneValidator.normalize(row.get("contact") or row.get("owner_phone") or row.get("contact_phone"))
            if phone:
                for key in ("contact", "owner_phone", "contact_phone"):
                    if key in columns:
                        updates[key] = phone
        if not updates:
            return
        cols = [key for key in updates if key in columns]
        assignments = ", ".join(f"{key}=?" for key in cols)
        self.services.execute(
            f"UPDATE {table} SET {assignments} WHERE id=?",
            tuple(updates[key] for key in cols) + (row["id"],),
        )

    # ── Bulk sync ─────────────────────────────────────────────────────

    def sync_all_deal_contacts(self) -> int:
        """Sync all deal records to clients and properties tables."""
        synced = 0
        for table in DEAL_TABLES:
            for row in self.services.fetch_all(f"SELECT * FROM {table} ORDER BY id"):
                self.sync_phase1_aliases(table, row)
                row = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (row["id"],)) or row
                self.upsert_client_from_deal(table, row)
                if table in {"rent_availability", "sale_availability"}:
                    self.sync_property_from_availability(table, row, self.availability_property_status(table, row))
                    self.archive_closed_availability(table, int(row["id"]))
                synced += 1
        return synced

    # ── Workflow status update ────────────────────────────────────────

    def update_deal_workflow_status(self, table: str, record_id: int, status: str) -> tuple[dict, int | None]:
        """Update a deal record's workflow status and sync downstream."""
        columns = self.services.table_columns(table)
        now = datetime.now()
        final_status = status in {"Rented", "Sold"}
        stage = "Pending" if status == "Pending" else "Deal Done" if final_status else "Contacted"
        probability = 60.0 if status == "Pending" else 100.0 if final_status else 25.0
        assignments: list[str] = []
        params: list[Any] = []
        if "workflow_stage" in columns:
            assignments.append("workflow_stage=?")
            params.append(stage)
        if "priority" in columns:
            assignments.append("priority=?")
            params.append("High" if status == "Pending" else "Medium")
        if "deal_probability" in columns:
            assignments.append("deal_probability=?")
            params.append(probability)
        if "last_contacted" in columns:
            assignments.append("last_contacted=?")
            params.append(now.strftime(PY_DATE_STORAGE_FORMAT))
        if "status" in columns and (status == "Pending" or final_status):
            assignments.append("status=?")
            params.append(normalize_availability_status(status))
        if final_status and "closed_at" in columns:
            assignments.append("closed_at=COALESCE(closed_at, ?)")
            params.append(now)
        if assignments:
            params.append(record_id)
            self.services.execute(f"UPDATE {table} SET {', '.join(assignments)} WHERE id=?", tuple(params))
        full = self.services.fetch_one(f"SELECT * FROM {table} WHERE id=?", (record_id,)) or {"id": record_id}
        property_id: int | None = None
        if table in {"rent_availability", "sale_availability"}:
            property_id = self.sync_property_from_availability(table, full, self.availability_property_status(table, full))
            self.archive_closed_availability(table, record_id)
        self.upsert_client_from_deal(table, full)
        return full, property_id
