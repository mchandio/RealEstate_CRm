import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import CRM_DB_PATH
from backend.models import (
    User, RentRequirement, RentAvailability,
    SaleRequirement, SaleAvailability, RentedProperty, SoldProperty,
    IncomeTransaction, ExpenseTransaction,
    Employee, Client, Property, Attendance, SalaryPayment, AppSetting, PendingApproval,
)
from backend.auth import get_current_user, has_permission
from crm_core.attendance import attendance_policy_from_settings
from crm_core.matching import smart_match_score
from crm_core.reports import ReportResult, ReportService, export_report_pdf

router = APIRouter(prefix="/api/reports", tags=["Reports"])
MATCH_SCORE_THRESHOLD = 40.0


def require_perm(user: User, *permissions: str) -> None:
    if not any(has_permission(user.role, permission) for permission in permissions):
        raise HTTPException(status_code=403, detail="You do not have access to this report")


def report_setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value).strip() if row and row.value else default


def report_service(db: Session) -> ReportService:
    return ReportService(
        CRM_DB_PATH,
        company_name=report_setting(db, "company_name", "Real Estate CRM"),
        currency_symbol=report_setting(db, "currency_symbol", "Rs."),
    )


def attendance_policy(db: Session):
    keys = {
        "attendance_shift_name",
        "attendance_shift_start",
        "attendance_shift_end",
        "attendance_grace_minutes",
        "attendance_half_day_minutes",
    }
    settings = {
        row.key: row.value
        for row in db.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
    }
    return attendance_policy_from_settings(settings)


def parse_report_date(value: str | None):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def in_report_range(value: str | None, start: str | None, end: str | None) -> bool:
    start_date = parse_report_date(start)
    end_date = parse_report_date(end)
    if not start_date and not end_date:
        return True
    row_date = parse_report_date(value)
    if not row_date:
        return False
    if start_date and row_date < start_date:
        return False
    if end_date and row_date > end_date:
        return False
    return True


PROPERTY_QUALITY_FIELDS = (
    "title", "property_type", "status", "owner_name", "owner_contact",
    "location", "area", "floor", "bedrooms", "bathrooms", "facilities",
    "nearby_landmarks", "verification_status", "photo_paths",
)


def listing_score(record, fields: tuple[str, ...]) -> int:
    if not fields:
        return 0
    completed = sum(1 for field in fields if str(getattr(record, field, "") or "").strip())
    return round(completed / len(fields) * 100)


def active_query(db: Session, model):
    query = db.query(model)
    if hasattr(model, "is_deleted"):
        deleted_col = getattr(model, "is_deleted")
        query = query.filter(or_(deleted_col.is_(False), deleted_col == 0, deleted_col.is_(None)))
    table_name = getattr(model, "__tablename__", "")
    if table_name == "rent_availability" and hasattr(model, "status"):
        query = query.filter(func.lower(func.coalesce(model.status, "")) != "rented")
    elif table_name == "sale_availability" and hasattr(model, "status"):
        query = query.filter(func.lower(func.coalesce(model.status, "")) != "sold")
    return query


def normalize_location(value: object) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return "Unspecified"
    upper = text.upper()
    if "GIZRI" in upper:
        return "Gizri"
    if "DHA" in upper or "DEFENCE" in upper:
        return "DHA"
    if "CLIFTON" in upper:
        return "Clifton"
    if "PECHS" in upper:
        return "PECHS"
    if "NORTH" in upper and "NAZIM" in upper:
        return "North Nazim"
    if "BAHRIA" in upper:
        return "Bahria"
    return text[:18]


def location_buckets(db: Session) -> list[dict]:
    buckets: dict[str, dict[str, int]] = {}

    def add(model, key: str) -> None:
        for (location,) in active_query(db, model).with_entities(model.location).all():
            label = normalize_location(location)
            bucket = buckets.setdefault(label, {
                "location": label,
                "rent_requirements": 0,
                "rent_availability": 0,
                "sale_requirements": 0,
                "sale_availability": 0,
            })
            bucket[key] += 1

    add(RentRequirement, "rent_requirements")
    add(RentAvailability, "rent_availability")
    add(SaleRequirement, "sale_requirements")
    add(SaleAvailability, "sale_availability")
    rows = sorted(
        buckets.values(),
        key=lambda item: item["rent_requirements"] + item["rent_availability"] + item["sale_requirements"] + item["sale_availability"],
        reverse=True,
    )
    return rows[:6] or [{
        "location": "No Data",
        "rent_requirements": 0,
        "rent_availability": 0,
        "sale_requirements": 0,
        "sale_availability": 0,
    }]


def active_match_rows(db: Session, model, *, limit: int = 2000):
    query = active_query(db, model)
    if hasattr(model, "workflow_stage"):
        stage_col = getattr(model, "workflow_stage")
        query = query.filter(or_(stage_col.is_(None), ~stage_col.in_(["Closed", "Deal Done"])))
    return query.order_by(model.id.desc()).limit(limit).all()


def count_matched_demand_supply_pairs(db: Session, *, minimum_score: float = MATCH_SCORE_THRESHOLD) -> int:
    pairs = 0
    match_sets = (
        (RentRequirement, RentAvailability, "rent_requirements", "rent_availability"),
        (SaleRequirement, SaleAvailability, "sale_requirements", "sale_availability"),
    )
    for requirement_model, availability_model, requirement_table, availability_table in match_sets:
        requirements = active_match_rows(db, requirement_model)
        availability = active_match_rows(db, availability_model)
        for requirement in requirements:
            for available in availability:
                score, _reasons = smart_match_score(requirement, available, requirement_table, availability_table)
                if score >= minimum_score:
                    pairs += 1
    return pairs


def count_closed_deals_from_session(db: Session) -> int:
    """Count closed deals using the SQLAlchemy session (not the file DB)."""
    closed_stage = 0
    for model in (RentRequirement, RentAvailability, SaleRequirement, SaleAvailability):
        if hasattr(model, "workflow_stage"):
            stage_col = getattr(model, "workflow_stage")
            closed_stage += db.query(model).filter(
                func.lower(func.coalesce(stage_col, "")) == "deal done"
            ).count()
    rented = db.query(RentedProperty).count()
    sold = db.query(SoldProperty).count()
    return closed_stage + rented + sold


def client_segments(db: Session) -> list[dict]:
    total = db.query(Client).count()
    if total <= 0:
        return [
            {"label": "Active Searchers", "value": 0, "percent": 0, "color": "#1976d2"},
            {"label": "Long-Term Leads", "value": 0, "percent": 0, "color": "#43a047"},
            {"label": "Past Clients", "value": 0, "percent": 0, "color": "#007c91"},
        ]
    active = db.query(Client).filter(
        Client.status.ilike("active"),
        or_(Client.client_type.ilike("tenant"), Client.client_type.ilike("buyer"), Client.client_type.ilike("investor")),
    ).count()
    long_term = db.query(Client).filter(
        or_(Client.client_type.ilike("owner"), Client.client_type.ilike("seller"), Client.client_type.ilike("broker"))
    ).count()
    past = max(total - active - long_term, 0)
    rows = [
        ("Active Searchers", active, "#1976d2"),
        ("Long-Term Leads", long_term, "#43a047"),
        ("Past Clients", past, "#007c91"),
    ]
    return [
        {"label": label, "value": value, "percent": round((value / total) * 100), "color": color}
        for label, value, color in rows
    ]


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "dashboard")
    result = report_service(db).dashboard_summary(
        generated_by=user.full_name or user.username,
        generated_role=user.role,
    )
    # Override deal metrics with session-aware counts so the API
    # always reflects the live SQLAlchemy session rather than the file DB.
    result["active_matched_pairs"] = count_matched_demand_supply_pairs(db)
    result["closed_deals"] = count_closed_deals_from_session(db)
    result["matched_pairs"] = result["active_matched_pairs"] + result["closed_deals"]
    if result["matched_pairs"]:
        result["conversion_rate"] = round(
            (result["closed_deals"] / result["matched_pairs"]) * 100
        )
    return result


@router.get("/financial")
def financial_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_perm(user, "financial", "financial_view")
    return report_service(db).financial_summary(start_date, end_date)


@router.get("/properties")
def property_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "properties")
    return report_service(db).property_summary()


@router.get("/employees")
def employee_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "employees", "employees_view")
    return report_service(db).employee_summary(policy=attendance_policy(db))


@router.get("/attendance")
def attendance_report(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_perm(user, "employees", "employees_view")
    return report_service(db).attendance_summary(start_date, end_date, policy=attendance_policy(db))


@router.get("/dealings")
def dealings_report(
    kind: str = Query("all"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result, company_name, currency_symbol = build_dealings_result(kind, start_date, end_date, db, user)
    return {
        "ok": True,
        "kind": kind,
        "title": result.title,
        "summary": result.summary,
        "rows": result.rows,
        "text": result.text,
        "company": company_name,
        "currency_symbol": currency_symbol,
        "filename_slug": result.filename_slug,
        "generated_at": result.generated_at,
        "period": {"start_date": start_date, "end_date": end_date},
    }


@router.get("/dealings/pdf")
def dealings_report_pdf(
    kind: str = Query("all"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result, _company_name, _currency_symbol = build_dealings_result(kind, start_date, end_date, db, user)
    fd, temp_path = tempfile.mkstemp(prefix=f"{result.filename_slug}_", suffix=".pdf")
    os.close(fd)
    export_report_pdf(result, temp_path)
    filename = f"{result.filename_slug}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(
        temp_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(_remove_temp_file, temp_path),
    )


def build_dealings_result(
    kind: str,
    start_date: str | None,
    end_date: str | None,
    db: Session,
    user: User,
) -> tuple[ReportResult, str, str]:
    if kind not in {"rent", "sale", "all"}:
        raise HTTPException(status_code=400, detail="kind must be rent, sale, or all")
    if kind == "rent":
        require_perm(user, "rent", "rent_view", "reports")
    elif kind == "sale":
        require_perm(user, "sale", "sale_view", "reports")
    else:
        require_perm(user, "reports", "rent", "sale", "rent_view", "sale_view")

    company_name = report_setting(db, "company_name", "Real Estate CRM")
    currency_symbol = report_setting(db, "currency_symbol", "Rs.")
    service = ReportService(CRM_DB_PATH, company_name=company_name, currency_symbol=currency_symbol)
    if kind == "rent":
        result = service.rent_report(start_date, end_date)
    elif kind == "sale":
        result = service.sale_report(start_date, end_date)
    else:
        result = service.dealings_report(start_date, end_date)
    return result, company_name, currency_symbol


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
