import json
import re
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, text, or_, func
from typing import Optional
from backend.backup import backup_status, run_database_backup
from backend.database import get_db, engine
from backend.models import User, Client, Property, AuditLog
from backend.schemas import RecordCreate, RecordUpdate, ApprovalAction, MatchRequest, WorkflowAction
from backend.auth import get_current_user, require_permission, has_permission
from crm_core.matching import best_matches

router = APIRouter(prefix="/api/records", tags=["Records"])

ALLOWED_TABLES = [
    "rent_requirements", "rent_availability",
    "sale_requirements", "sale_availability",
    "clients", "properties", "employees",
    "income_transactions", "expense_transactions",
    "attendance", "salary_payments",
]

GLOBAL_SEARCH_TABLES = [
    "rent_requirements",
    "rent_availability",
    "sale_requirements",
    "sale_availability",
]

TABLE_LABELS = {
    "rent_requirements": "Rent Requirement",
    "rent_availability": "Rent Availability",
    "sale_requirements": "Sale Requirement",
    "sale_availability": "Sale Availability",
    "clients": "Client",
    "properties": "Property",
    "employees": "Employee",
    "income_transactions": "Income Transaction",
    "expense_transactions": "Expense Transaction",
    "attendance": "Attendance",
    "salary_payments": "Salary Payment",
}

GLOBAL_SEARCH_HIDDEN_COLUMNS = {"cnic", "password_hash"}

TABLE_PERMISSIONS = {
    "rent_requirements": ("rent", "rent_view"),
    "rent_availability": ("rent", "rent_view"),
    "sale_requirements": ("sale", "sale_view"),
    "sale_availability": ("sale", "sale_view"),
    "clients": ("clients", None),
    "properties": ("properties", None),
    "employees": ("employees", "employees_view"),
    "attendance": ("employees", "employees_view"),
    "salary_payments": ("employees", "employees_view"),
    "income_transactions": ("financial", "financial_view"),
    "expense_transactions": ("financial", "financial_view"),
}

DEAL_STAGES = ["Lead", "Contacted", "Visit Scheduled", "Negotiation", "Closed", "Deal Done"]
DEAL_PRIORITIES = ["Low", "Medium", "High", "Urgent"]
STAGE_PROBABILITY = {
    "Lead": 10.0,
    "Contacted": 25.0,
    "Visit Scheduled": 45.0,
    "Negotiation": 70.0,
    "Closed": 90.0,
    "Deal Done": 100.0,
}
DEAL_TABLES = {
    "rent_requirements": ("client_name", "contact", "property_requires", "budget"),
    "rent_availability": ("owner_name", "contact", "property_availability", "monthly_rent"),
    "sale_requirements": ("client_name", "contact", "property_requires", "budget"),
    "sale_availability": ("owner_name", "contact", "property_availability", "demand"),
}

CONTACT_FIELDS = {
    "rent_requirements": "contact",
    "rent_availability": "contact",
    "sale_requirements": "contact",
    "sale_availability": "contact",
    "clients": "phone",
    "properties": "owner_contact",
    "employees": "phone",
}

REQUIRED_FIELDS = {
    "rent_requirements": ("date", "client_name", "contact", "property_requires", "location", "budget"),
    "rent_availability": ("date", "owner_name", "contact", "property_availability", "location", "monthly_rent"),
    "sale_requirements": ("date", "client_name", "contact", "property_requires", "location", "budget"),
    "sale_availability": ("date", "owner_name", "contact", "property_availability", "location", "demand"),
    "clients": ("client_name", "phone"),
    "properties": ("title", "property_type", "location"),
    "employees": ("employee_id", "full_name", "phone"),
    "income_transactions": ("transaction_date", "income_type", "amount"),
    "expense_transactions": ("transaction_date", "expense_category", "amount"),
}

DATE_FIELDS = {"date", "transaction_date", "hire_date", "payment_date", "next_follow_up", "last_contacted"}
MONEY_FIELDS = {
    "budget", "monthly_rent", "demand", "deposit", "maintenance_charge", "amount",
    "base_salary", "bonus", "deductions", "net_salary", "sale_price", "expected_close_value",
}
TEXT_FILTER_FIELDS = {
    "rent_requirements": ("client_name", "contact", "property_requires", "location", "facilities", "remarks"),
    "rent_availability": ("owner_name", "contact", "property_availability", "location", "facilities", "remarks"),
    "sale_requirements": ("client_name", "contact", "property_requires", "location", "facilities", "remarks"),
    "sale_availability": ("owner_name", "contact", "property_availability", "location", "facilities", "remarks"),
    "clients": ("client_name", "phone", "email", "address", "client_type", "notes"),
    "properties": ("property_code", "title", "property_type", "owner_name", "owner_contact", "location", "facilities"),
    "employees": ("employee_id", "full_name", "phone", "email", "position", "department"),
    "income_transactions": ("income_type", "tenant_name", "description", "receipt_no", "payment_method"),
    "expense_transactions": ("expense_category", "vendor_name", "description", "invoice_no", "payment_method"),
}


def get_table_model(table: str):
    from backend.models import (
        RentRequirement, RentAvailability,
        SaleRequirement, SaleAvailability,
        IncomeTransaction, ExpenseTransaction,
        Client, Property, Employee,
        Attendance, SalaryPayment,
    )
    mapping = {
        "rent_requirements": RentRequirement,
        "rent_availability": RentAvailability,
        "sale_requirements": SaleRequirement,
        "sale_availability": SaleAvailability,
        "income_transactions": IncomeTransaction,
        "expense_transactions": ExpenseTransaction,
        "clients": Client,
        "properties": Property,
        "employees": Employee,
        "attendance": Attendance,
        "salary_payments": SalaryPayment,
    }
    return mapping.get(table)


def can_read_table(user: User, table: str) -> bool:
    edit_perm, view_perm = TABLE_PERMISSIONS.get(table, (None, None))
    if edit_perm and has_permission(user.role, edit_perm):
        return True
    if view_perm and has_permission(user.role, view_perm):
        return True
    return False


def can_write_table(user: User, table: str) -> bool:
    edit_perm, _view_perm = TABLE_PERMISSIONS.get(table, (None, None))
    return bool(edit_perm and has_permission(user.role, edit_perm))


def require_table_read(user: User, table: str) -> None:
    if not can_read_table(user, table):
        raise HTTPException(status_code=403, detail=f"You do not have access to {TABLE_LABELS.get(table, table)}")


def require_table_write(user: User, table: str) -> None:
    if not can_write_table(user, table):
        raise HTTPException(status_code=403, detail=f"You cannot change {TABLE_LABELS.get(table, table)}")


def serialize_record(record):
    return {c.name: getattr(record, c.name) for c in record.__table__.columns if c.name not in GLOBAL_SEARCH_HIDDEN_COLUMNS}


def model_columns(model):
    return {c.name for c in model.__table__.columns}


def normalize_phone(value: object) -> str:
    digits = re.sub(r"\D+", "", str(value or ""))
    if digits.startswith("92") and len(digits) == 12:
        digits = "0" + digits[2:]
    return digits


def parse_date_value(value: object) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text_value[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("Use date format YYYY-MM-DD or DD/MM/YYYY")


def validate_record_payload(table: str, data: dict, *, creating: bool = False) -> None:
    errors: list[str] = []
    required = REQUIRED_FIELDS.get(table, ())
    if creating:
        for field in required:
            if str(data.get(field) or "").strip() == "":
                errors.append(f"{field.replace('_', ' ').title()} is required")
    else:
        for field in required:
            if field in data and str(data.get(field) or "").strip() == "":
                errors.append(f"{field.replace('_', ' ').title()} cannot be empty")

    for field in DATE_FIELDS & set(data):
        if data.get(field) in (None, ""):
            continue
        try:
            data[field] = parse_date_value(data[field])
        except ValueError as exc:
            errors.append(f"{field.replace('_', ' ').title()}: {exc}")

    for field in MONEY_FIELDS & set(data):
        value = data.get(field)
        if value in (None, ""):
            data[field] = 0
            continue
        try:
            number = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            errors.append(f"{field.replace('_', ' ').title()} must be a number")
            continue
        if number < 0:
            errors.append(f"{field.replace('_', ' ').title()} cannot be negative")
        data[field] = number

    phone_field = CONTACT_FIELDS.get(table)
    if phone_field and phone_field in data:
        phone = normalize_phone(data.get(phone_field))
        if data.get(phone_field) not in (None, "") and (len(phone) != 11 or not phone.startswith("03")):
            errors.append(f"{phone_field.replace('_', ' ').title()} must be an 11 digit mobile number starting with 03")
        elif phone:
            data[phone_field] = phone

    if "workflow_stage" in data and data["workflow_stage"] not in (None, ""):
        data["workflow_stage"] = normalize_stage(str(data["workflow_stage"]))
    if "priority" in data and data["priority"] not in DEAL_PRIORITIES:
        errors.append(f"Priority must be one of {', '.join(DEAL_PRIORITIES)}")

    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Please fix the highlighted record fields.", "errors": errors},
        )


def clean_payload(model, payload: dict, user: Optional[User] = None, creating: bool = False):
    columns = model_columns(model)
    unknown = sorted(k for k in payload.keys() if k not in columns or k == "id")
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {unknown}")
    data = {k: v for k, v in payload.items() if k in columns and k != "id"}
    if creating and user is not None and "created_by" in columns and not data.get("created_by"):
        data["created_by"] = user.username
    return data


def record_value(record, *names: str):
    for name in names:
        if hasattr(record, name):
            value = getattr(record, name)
            if value not in (None, ""):
                return value
    return ""


def record_text(record, *names: str) -> str:
    return str(record_value(record, *names) or "").strip()


def record_number(record, *names: str) -> float:
    value = record_value(record, *names)
    try:
        if value in (None, ""):
            return 0.0
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def contact_type(value, default: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"b", "broker", "agent"}:
        return "Broker"
    if text in {"o", "owner", "seller"}:
        return "Owner"
    return default


def deal_client_contacts(table: str, record) -> list[dict[str, str]]:
    contacts: list[dict[str, str]] = []
    if table in {"rent_requirements", "sale_requirements"}:
        default_type = "Tenant" if table.startswith("rent") else "Buyer"
        contacts.append({
            "name": record_text(record, "client_name"),
            "phone": record_text(record, "contact", "contact_phone"),
            "email": record_text(record, "contact_email"),
            "type": contact_type(record_text(record, "client_status"), default_type),
        })
    elif table in {"rent_availability", "sale_availability"}:
        contacts.append({
            "name": record_text(record, "owner_name"),
            "phone": record_text(record, "contact", "contact_phone"),
            "email": record_text(record, "contact_email"),
            "type": contact_type(record_text(record, "client_broker"), "Owner"),
        })
    for key in ("broker", "preferred_broker", "posted_by_broker", "posted_by", "client_broker"):
        broker = record_text(record, key)
        if broker and broker.lower() not in {"o", "b", "owner", "broker", "direct", "agent", "client"}:
            contacts.append({"name": broker, "phone": "", "email": "", "type": "Broker"})
    return contacts


def upsert_clients_from_deal(db: Session, table: str, record) -> None:
    if table not in DEAL_TABLES:
        return
    for contact in deal_client_contacts(table, record):
        name = contact["name"]
        if not name:
            continue
        phone = contact["phone"]
        email = contact["email"]
        client_type = contact["type"] or "Other"
        notes = f"Auto-synced from {TABLE_LABELS.get(table, table)} #{getattr(record, 'id', '')}".strip()
        existing = None
        if phone:
            existing = db.query(Client).filter(Client.phone == phone).first()
        if existing is None:
            existing = db.query(Client).filter(func.lower(Client.client_name) == name.lower()).first()
        if existing:
            if not existing.client_name:
                existing.client_name = name
            if phone and not existing.phone:
                existing.phone = phone
            if email and not existing.email:
                existing.email = email
            if client_type and not existing.client_type:
                existing.client_type = client_type
            if not existing.status:
                existing.status = "Active"
            if not existing.notes:
                existing.notes = notes
        else:
            db.add(Client(
                client_name=name,
                phone=phone,
                email=email,
                client_type=client_type,
                status="Active",
                notes=notes,
            ))


def property_match(db: Session, record, title: str, property_type: str):
    location = record_text(record, "location")
    owner_name = record_text(record, "owner_name")
    owner_contact = record_text(record, "contact", "contact_phone")
    if owner_contact:
        found = db.query(Property).filter(Property.owner_contact == owner_contact).first()
        if found:
            return found
    if owner_name and location:
        found = (
            db.query(Property)
            .filter(func.lower(Property.owner_name) == owner_name.lower())
            .filter(func.lower(Property.location) == location.lower())
            .first()
        )
        if found:
            return found
    if title and location:
        return (
            db.query(Property)
            .filter(func.lower(Property.title) == title.lower())
            .filter(func.lower(Property.location) == location.lower())
            .filter(func.lower(Property.property_type) == property_type.lower())
            .first()
        )
    return None


def sync_property_from_availability(db: Session, table: str, record, status: str) -> None:
    if table not in {"rent_availability", "sale_availability"}:
        return
    property_type = record_text(record, "property_availability", "property_type")
    location = record_text(record, "location")
    if not property_type and not location:
        return
    title = f"{property_type or 'Property'} - {location or 'Location'}"
    area = " ".join(part for part in (record_text(record, "size"), record_text(record, "measurement")) if part)
    data = {
        "title": title,
        "property_type": property_type,
        "status": status,
        "owner_name": record_text(record, "owner_name"),
        "owner_contact": record_text(record, "contact", "contact_phone"),
        "location": location,
        "area": area,
        "floor": record_text(record, "floor", "floor_no"),
        "monthly_rent": record_number(record, "monthly_rent") if table.startswith("rent") else 0.0,
        "sale_price": record_number(record, "demand", "asking_price") if table.startswith("sale") else 0.0,
        "maintenance_charge": record_number(record, "maintenance_charge"),
        "facilities": record_text(record, "facilities"),
        "description": record_text(record, "remarks", "description", "notes"),
    }
    existing = property_match(db, record, title, property_type)
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
    else:
        db.add(Property(property_code=f"PROP{datetime.now().strftime('%Y%m%d%H%M%S')}", **data))


def sync_after_deal_save(db: Session, table: str, record) -> None:
    if table not in DEAL_TABLES:
        return
    upsert_clients_from_deal(db, table, record)
    status = record_text(record, "status").lower()
    if table == "rent_availability" and status == "rented":
        sync_property_from_availability(db, table, record, "Rented")
    elif table == "sale_availability" and status == "sold":
        sync_property_from_availability(db, table, record, "Sold")


def normalize_stage(stage: Optional[str]) -> str:
    return stage if stage in DEAL_STAGES else "Lead"


def deal_row(table: str, record):
    name_col, contact_col, type_col, value_col = DEAL_TABLES[table]
    stage = normalize_stage(getattr(record, "workflow_stage", None))
    amount = getattr(record, "expected_close_value", None) or getattr(record, value_col, 0) or 0
    return {
        "table": table,
        "id": record.id,
        "name": getattr(record, name_col, "") or "",
        "contact": getattr(record, contact_col, "") or "",
        "location": getattr(record, "location", "") or "",
        "property_type": getattr(record, type_col, "") or "",
        "amount": float(amount or 0),
        "stage": stage,
        "priority": getattr(record, "priority", None) or "Medium",
        "next_follow_up": getattr(record, "next_follow_up", None),
        "assigned_to": getattr(record, "assigned_to", None),
        "probability": float(getattr(record, "deal_probability", None) or STAGE_PROBABILITY[stage]),
    }


def record_label(record) -> str:
    return (
        record_text(record, "client_name")
        or record_text(record, "owner_name")
        or record_text(record, "full_name")
        or record_text(record, "title")
        or record_text(record, "property_code")
        or f"#{getattr(record, 'id', '')}"
    )


def find_duplicate_records(
    db: Session,
    user: User,
    table: str,
    data: dict,
    *,
    exclude_id: int | None = None,
    max_per_table: int = 8,
) -> list[dict]:
    phone_field = CONTACT_FIELDS.get(table)
    if not phone_field:
        return []
    phone = normalize_phone(data.get(phone_field))
    if not phone:
        return []
    duplicates: list[dict] = []
    for other_table, other_field in CONTACT_FIELDS.items():
        if other_table in ALLOWED_TABLES and not can_read_table(user, other_table):
            continue
        model = get_table_model(other_table)
        if model is None or not hasattr(model, other_field):
            continue
        rows = (
            db.query(model)
            .filter(getattr(model, other_field).isnot(None))
            .order_by(model.id.desc())
            .limit(2000)
            .all()
        )
        found = 0
        for row in rows:
            if other_table == table and exclude_id and getattr(row, "id", None) == exclude_id:
                continue
            if normalize_phone(getattr(row, other_field, "")) != phone:
                continue
            duplicates.append({
                "table": other_table,
                "table_label": TABLE_LABELS.get(other_table, other_table),
                "id": getattr(row, "id", None),
                "name": record_label(row),
                "phone": phone,
                "location": record_text(row, "location", "address"),
            })
            found += 1
            if found >= max_per_table:
                break
    return duplicates


def audit_snapshot(record) -> dict:
    return serialize_record(record) if record is not None else {}


def audit_summary(table: str, record_id: int | None, action: str, before: dict | None, after: dict | None) -> str:
    label = TABLE_LABELS.get(table, table)
    if action == "create":
        return f"Created {label} #{record_id}"
    if action == "delete":
        return f"Deleted {label} #{record_id}"
    if action == "workflow":
        return f"Workflow changed for {label} #{record_id}"
    if action == "approve":
        return f"Approval changed for {label} #{record_id}"
    if before and after:
        changed = [key for key in sorted(after) if before.get(key) != after.get(key)]
        if changed:
            fields = ", ".join(changed[:6])
            suffix = "..." if len(changed) > 6 else ""
            return f"Updated {label} #{record_id}: {fields}{suffix}"
    return f"Updated {label} #{record_id}"


def write_audit_log(
    db: Session,
    user: User,
    table: str,
    record_id: int | None,
    action: str,
    *,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    details = {"before": before or {}, "after": after or {}}
    db.add(AuditLog(
        table_name=table,
        record_id=record_id,
        action=action,
        username=user.username,
        summary=audit_summary(table, record_id, action, before, after),
        details=json.dumps(details, default=str, ensure_ascii=True),
    ))


def date_column_for_table(model):
    for column_name in ("date", "transaction_date", "payment_date", "hire_date", "created_at"):
        if hasattr(model, column_name):
            return getattr(model, column_name)
    return None


def apply_list_filters(
    query,
    model,
    table: str,
    *,
    q: str = "",
    stage: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    term = (q or "").strip()
    if term:
        pattern = f"%{term}%"
        columns = [col for col in TEXT_FILTER_FIELDS.get(table, ()) if hasattr(model, col)]
        if columns:
            query = query.filter(or_(*[cast(getattr(model, col), String).ilike(pattern) for col in columns]))
    if stage and hasattr(model, "workflow_stage"):
        query = query.filter(getattr(model, "workflow_stage") == stage)
    if status and hasattr(model, "status"):
        query = query.filter(getattr(model, "status") == status)
    date_col = date_column_for_table(model)
    if date_col is not None:
        if date_from:
            try:
                parsed_from = parse_date_value(date_from)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"date_from: {exc}")
            query = query.filter(cast(date_col, String) >= parsed_from)
        if date_to:
            try:
                parsed_to = parse_date_value(date_to)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"date_to: {exc}")
            query = query.filter(cast(date_col, String) <= parsed_to)
    return query


def require_audit_permission(user: User) -> None:
    if user.role not in ("Super Admin", "Admin"):
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")


# Specific routes must come before parameterized /{table} routes
@router.get("/search/global")
def global_search(
    q: str = Query("", min_length=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = []
    term = q.strip()
    if not term:
        return {"ok": True, "query": q, "count": 0, "results": []}
    pattern = f"%{term}%"
    normalized_term = term.lower()
    for table in GLOBAL_SEARCH_TABLES:
        if not can_read_table(user, table):
            continue
        try:
            model = get_table_model(table)
            if model is None:
                continue
            columns = [c.name for c in model.__table__.columns if c.name not in GLOBAL_SEARCH_HIDDEN_COLUMNS]
            if not columns:
                continue
            source = TABLE_LABELS.get(table, table.replace("_", " ").title())
            source_text = f"{source} {table.replace('_', ' ')}".lower()
            query = db.query(model)
            if normalized_term in source_text:
                records = query.order_by(getattr(model, "id").desc()).limit(limit).all()
            else:
                records = (
                    query.filter(
                        or_(
                            *[cast(getattr(model, col), String).ilike(pattern) for col in columns if hasattr(model, col)]
                        )
                    )
                    .limit(limit)
                    .all()
                )
            for r in records:
                fields = serialize_record(r)
                label = (
                    fields.get("client_name")
                    or fields.get("owner_name")
                    or fields.get("full_name")
                    or fields.get("title")
                    or fields.get("property_code")
                    or fields.get("receipt_no")
                    or fields.get("invoice_no")
                    or ""
                )
                detail = (
                    fields.get("contact")
                    or fields.get("contact_phone")
                    or fields.get("phone")
                    or fields.get("owner_contact")
                    or fields.get("email")
                    or fields.get("location")
                    or fields.get("status")
                    or ""
                )
                results.append({
                    "table": table,
                    "source": source,
                    "id": r.id,
                    "label": str(label or ""),
                    "detail": str(detail or ""),
                    "fields": fields,
                })
        except Exception:
            pass
    return {"ok": True, "query": q, "count": len(results), "results": results}


@router.post("/ai-match")
def ai_match(
    req: MatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Explainable smart matching: find complementary deal records."""
    model = get_table_model(req.table)
    if model is None or req.table not in DEAL_TABLES:
        raise HTTPException(status_code=400, detail="AI matching is only supported for deal tables")
    require_table_read(user, req.table)
    record = db.query(model).filter(model.id == req.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if "requirements" in req.table:
        match_table_name = req.table.replace("requirements", "availability")
        match_model = get_table_model(match_table_name)
    elif "availability" in req.table:
        match_table_name = req.table.replace("availability", "requirements")
        match_model = get_table_model(match_table_name)
    else:
        return {"ok": True, "matches": []}
    if match_model is None:
        return {"ok": True, "matches": []}

    query = db.query(match_model)
    if hasattr(match_model, "status"):
        status_col = getattr(match_model, "status")
        query = query.filter(or_(status_col.is_(None), ~status_col.in_(["Rented", "Sold", "Closed", "Inactive"])))
    if hasattr(match_model, "workflow_stage"):
        stage_col = getattr(match_model, "workflow_stage")
        query = query.filter(or_(stage_col.is_(None), ~stage_col.in_(["Closed", "Deal Done"])))
    matches = best_matches(record, query.order_by(match_model.id.desc()).limit(500).all(), req.table, match_table_name, limit=20)
    return {"ok": True, "matches": matches}


@router.get("/pipeline/stats")
def pipeline_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    counts = {stage: 0 for stage in DEAL_STAGES}
    totals = {stage: 0.0 for stage in DEAL_STAGES}
    for table in DEAL_TABLES:
        if not can_read_table(user, table):
            continue
        model = get_table_model(table)
        for record in db.query(model).all():
            row = deal_row(table, record)
            counts[row["stage"]] += 1
            totals[row["stage"]] += row["amount"]
    return {"ok": True, "stages": DEAL_STAGES, "counts": counts, "totals": totals}


@router.get("/pipeline/records")
def pipeline_records(
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if stage and stage not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Allowed: {DEAL_STAGES}")
    rows = []
    for table in DEAL_TABLES:
        if not can_read_table(user, table):
            continue
        model = get_table_model(table)
        query = db.query(model)
        if stage:
            query = query.filter(model.workflow_stage == stage)
        for record in query.order_by(model.id.desc()).limit(500).all():
            rows.append(deal_row(table, record))
    rows.sort(key=lambda r: (DEAL_STAGES.index(r["stage"]), r["next_follow_up"] or "9999-12-31"))
    return {"ok": True, "stage": stage or "All", "count": len(rows), "rows": rows}


@router.put("/{table}/{record_id}/workflow")
def update_workflow(
    table: str,
    record_id: int,
    req: WorkflowAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if table not in DEAL_TABLES:
        raise HTTPException(status_code=400, detail="Workflow is only supported for deal tables")
    require_table_write(user, table)
    if req.stage not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Allowed: {DEAL_STAGES}")
    if req.priority not in DEAL_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Allowed: {DEAL_PRIORITIES}")
    model = get_table_model(table)
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    before = audit_snapshot(record)
    record.workflow_stage = req.stage
    record.priority = req.priority
    record.next_follow_up = req.next_follow_up
    record.assigned_to = req.assigned_to or user.username
    record.last_contacted = datetime.now().strftime("%Y-%m-%d")
    record.deal_probability = req.deal_probability if req.deal_probability is not None else STAGE_PROBABILITY[req.stage]
    if req.expected_close_value is not None:
        record.expected_close_value = req.expected_close_value
    record.lost_reason = req.lost_reason
    if req.stage in {"Closed", "Deal Done"}:
        record.closed_at = datetime.now()
        if table == "rent_availability" and hasattr(record, "status"):
            record.status = "Rented"
        elif table == "sale_availability" and hasattr(record, "status"):
            record.status = "Sold"
    sync_after_deal_save(db, table, record)
    write_audit_log(db, user, table, record_id, "workflow", before=before, after=audit_snapshot(record))
    db.commit()
    return {"ok": True, "message": "Workflow updated", "record": deal_row(table, record)}


@router.post("/duplicates/check")
def check_duplicates(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    table = str(payload.get("table") or "")
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_read(user, table)
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")
    record_id = payload.get("record_id")
    try:
        exclude_id = int(record_id) if record_id not in (None, "") else None
    except (TypeError, ValueError):
        exclude_id = None
    duplicates = find_duplicate_records(db, user, table, data, exclude_id=exclude_id)
    return {"ok": True, "duplicates": duplicates, "count": len(duplicates)}


@router.get("/followups/today")
def due_followups(
    limit: int = Query(120, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today().isoformat()
    rows: list[dict] = []
    for table in DEAL_TABLES:
        if not can_read_table(user, table):
            continue
        model = get_table_model(table)
        if model is None:
            continue
        records = db.query(model).order_by(model.id.desc()).limit(1000).all()
        for record in records:
            stage = normalize_stage(getattr(record, "workflow_stage", None))
            if stage in {"Closed", "Deal Done"}:
                continue
            follow_up = str(getattr(record, "next_follow_up", "") or "").strip()
            priority = str(getattr(record, "priority", "") or "Medium")
            is_due = bool(follow_up and follow_up <= today)
            is_hot = priority in {"High", "Urgent"}
            if not is_due and not is_hot:
                continue
            row = deal_row(table, record)
            row["due_status"] = "Overdue" if follow_up and follow_up < today else "Due Today" if follow_up == today else "High Priority"
            row["label"] = TABLE_LABELS.get(table, table)
            rows.append(row)
    priority_order = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
    rows.sort(key=lambda r: (r.get("next_follow_up") or "9999-12-31", priority_order.get(r.get("priority"), 9)))
    return {"ok": True, "date": today, "count": len(rows[:limit]), "rows": rows[:limit]}


@router.get("/audit/logs")
def list_audit_logs(
    table: Optional[str] = Query(None),
    record_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_audit_permission(user)
    query = db.query(AuditLog)
    if table:
        query = query.filter(AuditLog.table_name == table)
    if record_id is not None:
        query = query.filter(AuditLog.record_id == record_id)
    total = query.count()
    logs = query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
    rows = []
    for item in logs:
        rows.append({
            "id": item.id,
            "table": item.table_name,
            "table_label": TABLE_LABELS.get(item.table_name, item.table_name),
            "record_id": item.record_id,
            "action": item.action,
            "username": item.username,
            "summary": item.summary,
            "created_at": item.created_at,
        })
    return {"ok": True, "total": total, "count": len(rows), "rows": rows}


@router.get("/backup/status")
def get_backup_status(user: User = Depends(require_permission("backup"))):
    return {"ok": True, **backup_status()}


@router.post("/backup/run")
def run_backup_now(user: User = Depends(require_permission("backup"))):
    path = run_database_backup("manual")
    return {"ok": True, "path": str(path), "message": "Backup created"}


@router.get("/{table}")
def list_records(
    table: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    q: str = Query(""),
    stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    direction: str = Query("desc"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Invalid table. Allowed: {sorted(ALLOWED_TABLES)}")
    require_table_read(user, table)
    model = get_table_model(table)
    if model is None:
        raise HTTPException(status_code=400, detail="Table not supported")
    query = apply_list_filters(
        db.query(model),
        model,
        table,
        q=q,
        stage=stage,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total = query.count()
    sort_column = getattr(model, sort, None) if sort else None
    if sort_column is None:
        sort_column = getattr(model, "id")
    order = sort_column.asc() if direction.lower() == "asc" else sort_column.desc()
    rows = query.order_by(order).offset(offset).limit(limit).all()
    return {"ok": True, "table": table, "total": total, "count": len(rows), "rows": [serialize_record(r) for r in rows]}


@router.get("/{table}/{record_id}")
def get_record(
    table: str,
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_read(user, table)
    model = get_table_model(table)
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"ok": True, "record": serialize_record(record)}


@router.post("/{table}")
def create_record(
    table: str,
    req: RecordCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_write(user, table)
    model = get_table_model(table)
    if model is None:
        raise HTTPException(status_code=400, detail="Table not supported")
    data = clean_payload(model, req.data, user=user, creating=True)
    if not data:
        raise HTTPException(status_code=400, detail="No valid fields to create")
    validate_record_payload(table, data, creating=True)
    duplicates = find_duplicate_records(db, user, table, data)
    instance = model(**data)
    db.add(instance)
    db.flush()
    sync_after_deal_save(db, table, instance)
    write_audit_log(db, user, table, instance.id, "create", after=audit_snapshot(instance))
    db.commit()
    db.refresh(instance)
    return {"ok": True, "id": instance.id, "message": "Record created", "duplicates": duplicates}


@router.put("/{table}/{record_id}")
def update_record(
    table: str,
    record_id: int,
    req: RecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_write(user, table)
    model = get_table_model(table)
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    data = clean_payload(model, req.data)
    if not data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    validate_record_payload(table, data, creating=False)
    before = audit_snapshot(record)
    for key, value in data.items():
        setattr(record, key, value)
    sync_after_deal_save(db, table, record)
    write_audit_log(db, user, table, record_id, "update", before=before, after=audit_snapshot(record))
    db.commit()
    return {"ok": True, "message": "Record updated"}


@router.delete("/{table}/{record_id}")
def delete_record(
    table: str,
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("delete")),
):
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_write(user, table)
    model = get_table_model(table)
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    before = audit_snapshot(record)
    write_audit_log(db, user, table, record_id, "delete", before=before)
    db.delete(record)
    db.commit()
    return {"ok": True, "message": "Record deleted"}


@router.put("/{table}/{record_id}/approve")
def approve_record(
    table: str,
    record_id: int,
    req: ApprovalAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("Super Admin", "Admin"):
        raise HTTPException(status_code=403, detail="Only admins can approve")
    if table not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Invalid table")
    require_table_write(user, table)
    model = get_table_model(table)
    record = db.query(model).filter(model.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if not hasattr(record, "approval_status"):
        raise HTTPException(status_code=400, detail="This table does not support approvals")
    before = audit_snapshot(record)
    record.approval_status = req.status
    record.approval_comment = req.comment
    record.approved_by = user.username
    record.approved_at = datetime.now()
    write_audit_log(db, user, table, record_id, "approve", before=before, after=audit_snapshot(record))
    db.commit()
    return {"ok": True, "message": f"Record #{record_id} marked as {req.status}"}


# (ai_match and global_search are defined above, before parameterized routes)
