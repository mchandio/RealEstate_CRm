from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import CRM_DB_PATH
from backend.models import (
    User, RentRequirement, RentAvailability,
    SaleRequirement, SaleAvailability,
    IncomeTransaction, ExpenseTransaction,
    Employee, Client, Property, Attendance, SalaryPayment, AppSetting,
)
from backend.auth import get_current_user, has_permission
from crm_core.reports import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def require_perm(user: User, *permissions: str) -> None:
    if not any(has_permission(user.role, permission) for permission in permissions):
        raise HTTPException(status_code=403, detail="You do not have access to this report")


def report_setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return str(row.value).strip() if row and row.value else default


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


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "dashboard")
    return {
        "company": report_setting(db, "company_name", "Real Estate CRM"),
        "currency_symbol": report_setting(db, "currency_symbol", "Rs."),
        "rent_requirements": db.query(RentRequirement).count(),
        "rent_available": db.query(RentAvailability).count(),
        "sale_requirements": db.query(SaleRequirement).count(),
        "sale_available": db.query(SaleAvailability).count(),
        "properties": db.query(Property).count(),
        "clients": db.query(Client).count(),
        "employees": db.query(Employee).count(),
        "pending_approvals": (
            db.query(RentRequirement).filter(RentRequirement.approval_status == "Pending").count()
            + db.query(RentAvailability).filter(RentAvailability.approval_status == "Pending").count()
            + db.query(SaleRequirement).filter(SaleRequirement.approval_status == "Pending").count()
            + db.query(SaleAvailability).filter(SaleAvailability.approval_status == "Pending").count()
        ),
    }


@router.get("/financial")
def financial_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_perm(user, "financial", "financial_view")
    income_records = [
        r for r in db.query(IncomeTransaction).all()
        if in_report_range(r.transaction_date, start_date, end_date)
    ]
    expense_records = [
        r for r in db.query(ExpenseTransaction).all()
        if in_report_range(r.transaction_date, start_date, end_date)
    ]
    income = sum(r.amount or 0 for r in income_records)
    expense = sum(r.amount or 0 for r in expense_records)
    income_by_type = {}
    for r in income_records:
        t = r.income_type or "Other"
        income_by_type[t] = income_by_type.get(t, 0) + (r.amount or 0)
    expense_by_category = {}
    for r in expense_records:
        c = r.expense_category or "Other"
        expense_by_category[c] = expense_by_category.get(c, 0) + (r.amount or 0)
    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "total_income": income,
        "total_expense": expense,
        "net_profit": income - expense,
        "profit_margin": round((income - expense) / income * 100, 2) if income > 0 else 0,
        "income_by_type": income_by_type,
        "expense_by_category": expense_by_category,
    }


@router.get("/properties")
def property_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "properties")
    rows = db.query(Property).order_by(Property.id.desc()).all()
    by_status = {}
    by_verification = {}
    presentation_ready = 0
    for r in rows:
        s = r.status or "Unknown"
        by_status[s] = by_status.get(s, 0) + 1
        verification = r.verification_status or "Unverified"
        by_verification[verification] = by_verification.get(verification, 0) + 1
        if listing_score(r, PROPERTY_QUALITY_FIELDS) >= 80:
            presentation_ready += 1
    return {
        "total": len(rows),
        "by_status": by_status,
        "by_verification": by_verification,
        "presentation_ready": presentation_ready,
        "properties": [
            {
                "id": r.id, "code": r.property_code, "title": r.title,
                "type": r.property_type, "status": r.status,
                "owner": r.owner_name, "location": r.location,
                "rent": r.monthly_rent, "price": r.sale_price,
                "listing_score": listing_score(r, PROPERTY_QUALITY_FIELDS),
                "verification": r.verification_status,
            }
            for r in rows
        ],
    }


@router.get("/employees")
def employee_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_perm(user, "employees", "employees_view")
    rows = db.query(Employee).order_by(Employee.id).all()
    total_payroll = sum(r.base_salary or 0 for r in rows)
    return {
        "total": len(rows),
        "total_payroll": total_payroll,
        "employees": [
            {
                "id": r.id, "emp_id": r.employee_id, "name": r.full_name,
                "position": r.position, "department": r.department,
                "salary": r.base_salary, "status": r.status,
            }
            for r in rows
        ],
    }


@router.get("/dealings")
def dealings_report(
    kind: str = Query("all"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
