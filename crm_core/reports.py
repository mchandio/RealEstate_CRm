"""Report generation services for rent and sale sections."""

from __future__ import annotations

import csv
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .attendance import AttendancePolicy, summarize_attendance
from .db import SQLiteRepository
from .matching import smart_match_score


@dataclass
class ReportResult:
    title: str
    text: str
    rows: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    filename_slug: str = "report"
    generated_at: datetime = field(default_factory=datetime.now)


class ReportService:
    """Creates text/CSV/PDF-ready reports from the CRM database."""

    RENT_REQUIREMENT_FIELDS = [
        "id", "date", "client_name", "contact", "property_requires", "size",
        "measurement", "measurement_unit", "budget", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    RENT_AVAILABILITY_FIELDS = [
        "id", "date", "owner_name", "contact", "property_availability", "size",
        "measurement", "measurement_unit", "monthly_rent", "floor", "location", "deposit",
        "maintenance_charge", "workflow_stage", "priority", "assigned_to",
        "deal_probability", "approval_status", "remarks",
    ]
    RENTED_PROPERTY_FIELDS = [
        "id", "source_id", "date", "closed_at", "owner_name", "contact",
        "property_availability", "size", "measurement", "measurement_unit",
        "monthly_rent", "floor", "location", "maintenance_charge", "archived_by",
        "remarks",
    ]
    SALE_REQUIREMENT_FIELDS = [
        "id", "date", "client_name", "contact", "property_requires", "size",
        "measurement", "measurement_unit", "budget", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    SALE_AVAILABILITY_FIELDS = [
        "id", "date", "owner_name", "contact", "property_availability", "size",
        "measurement", "measurement_unit", "demand", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    SOLD_PROPERTY_FIELDS = [
        "id", "source_id", "date", "closed_at", "owner_name", "contact",
        "property_availability", "size", "measurement", "measurement_unit",
        "demand", "floor", "location", "maintenance_charge", "archived_by",
        "remarks",
    ]
    FIELD_ALIASES = {
        "date": ("date", "date_created", "date_posted", "created_at", "transaction_date"),
        "closed_at": ("closed_at", "archived_at", "completed_at"),
        "contact": ("contact", "contact_phone", "phone", "owner_contact"),
        "property_requires": ("property_requires", "property_type", "property_requirement"),
        "property_availability": ("property_availability", "property_type"),
        "size": ("size", "size_beds"),
        "measurement": ("measurement", "sq_ft_yards", "sq_ft"),
        "measurement_unit": ("measurement_unit", "area_unit", "size_unit"),
        "budget": ("budget", "budget_max", "budget_min"),
        "demand": ("demand", "asking_price", "sale_price"),
        "floor": ("floor", "floor_no"),
        "remarks": ("remarks", "description", "notes"),
    }
    FIELD_DEFAULTS = {
        "workflow_stage": "'Lead'",
        "priority": "'Medium'",
        "assigned_to": "''",
        "deal_probability": "0",
        "approval_status": "''",
        "budget": "0",
        "monthly_rent": "0",
        "demand": "0",
    }

    def __init__(
        self,
        db_path: str | Path,
        *,
        currency_symbol: str = "Rs.",
        company_name: str = "Real Estate Management",
    ):
        self.repo = SQLiteRepository(db_path)
        self.currency_symbol = currency_symbol or "Rs."
        self.company_name = company_name or "Real Estate Management"

    def rent_report(self, start_date: str | None = None, end_date: str | None = None) -> ReportResult:
        requirements = self._fetch_section_rows(
            "rent_requirements", self.RENT_REQUIREMENT_FIELDS, start_date, end_date
        )
        availability = self._fetch_section_rows(
            "rent_availability", self.RENT_AVAILABILITY_FIELDS, start_date, end_date
        )
        rented = self._fetch_section_rows(
            "rented_properties", self.RENTED_PROPERTY_FIELDS, start_date, end_date, date_filter_key="closed_at"
        )
        summary = {
            "requirements": len(requirements),
            "available_properties": len(availability),
            "completed_rent_deals": len(rented),
            "total_requirement_budget": self._sum(requirements, "budget"),
            "average_requirement_budget": self._avg(requirements, "budget"),
            "total_monthly_rent": self._sum(availability, "monthly_rent"),
            "average_monthly_rent": self._avg(availability, "monthly_rent"),
            "total_completed_monthly_rent": self._sum(rented, "monthly_rent"),
            "stage_counts": self._combined_counts(requirements + availability, "workflow_stage"),
            "completed_location_counts": self._combined_counts(rented, "location"),
            "location_counts": self._combined_counts(requirements + availability, "location"),
        }
        csv_rows = (
            self._tag_rows("Rent Requirement", requirements)
            + self._tag_rows("Rent Availability", availability)
            + self._tag_rows("Rented Properties", rented)
        )
        text = self._build_rent_text(summary, requirements, availability, rented, start_date, end_date)
        return ReportResult(
            title="Rent Dealings Report",
            text=text,
            rows=csv_rows,
            summary=summary,
            filename_slug="rent_report",
        )

    def sale_report(self, start_date: str | None = None, end_date: str | None = None) -> ReportResult:
        requirements = self._fetch_section_rows(
            "sale_requirements", self.SALE_REQUIREMENT_FIELDS, start_date, end_date
        )
        availability = self._fetch_section_rows(
            "sale_availability", self.SALE_AVAILABILITY_FIELDS, start_date, end_date
        )
        sold = self._fetch_section_rows(
            "sold_properties", self.SOLD_PROPERTY_FIELDS, start_date, end_date, date_filter_key="closed_at"
        )
        summary = {
            "requirements": len(requirements),
            "available_properties": len(availability),
            "completed_sale_deals": len(sold),
            "total_requirement_budget": self._sum(requirements, "budget"),
            "average_requirement_budget": self._avg(requirements, "budget"),
            "total_owner_demand": self._sum(availability, "demand"),
            "average_owner_demand": self._avg(availability, "demand"),
            "total_completed_sale_value": self._sum(sold, "demand"),
            "stage_counts": self._combined_counts(requirements + availability, "workflow_stage"),
            "completed_location_counts": self._combined_counts(sold, "location"),
            "location_counts": self._combined_counts(requirements + availability, "location"),
        }
        csv_rows = (
            self._tag_rows("Sale Requirement", requirements)
            + self._tag_rows("Sale Availability", availability)
            + self._tag_rows("Sold Properties", sold)
        )
        text = self._build_sale_text(summary, requirements, availability, sold, start_date, end_date)
        return ReportResult(
            title="Sale Dealings Report",
            text=text,
            rows=csv_rows,
            summary=summary,
            filename_slug="sale_report",
        )

    def dealings_report(self, start_date: str | None = None, end_date: str | None = None) -> ReportResult:
        rent = self.rent_report(start_date, end_date)
        sale = self.sale_report(start_date, end_date)
        text = rent.text.rstrip() + "\n\n" + sale.text
        summary = {"rent": rent.summary, "sale": sale.summary}
        return ReportResult(
            title="Property Dealings Report",
            text=text,
            rows=rent.rows + sale.rows,
            summary=summary,
            filename_slug="property_dealings_report",
        )

    def dashboard_summary(
        self,
        *,
        generated_by: str = "CRM User",
        generated_role: str = "Staff",
    ) -> dict:
        rent_requirements = self._active_count("rent_requirements")
        rent_available = self._active_count("rent_availability")
        sale_requirements = self._active_count("sale_requirements")
        sale_available = self._active_count("sale_availability")
        rented_done = self._table_count("rented_properties")
        sold_done = self._table_count("sold_properties")
        properties = self._table_count("properties")
        clients = self._table_count("clients")
        employees = self._table_count("employees")
        pending_approvals = self._pending_approvals_count()
        closed_deals = self._closed_deals_count(rented_done, sold_done)
        active_matched_pairs = self._matched_demand_supply_pairs()
        matched_pair_opportunities = active_matched_pairs + closed_deals
        conversion = round((closed_deals / matched_pair_opportunities) * 100) if matched_pair_opportunities else 0
        response = self._first_response_metrics()
        approval = self._approval_metrics()
        return {
            "company": self.company_name,
            "generated_by": generated_by,
            "generated_role": generated_role,
            "currency_symbol": self.currency_symbol,
            "rent_requirements": rent_requirements,
            "rent_available": rent_available,
            "rented_done": rented_done,
            "sale_requirements": sale_requirements,
            "sale_available": sale_available,
            "sold_done": sold_done,
            "properties": properties,
            "clients": clients,
            "employees": employees,
            "pending_approvals": pending_approvals,
            "approval_queue": approval["pending"],
            "conversion_rate": conversion,
            "matched_pairs": matched_pair_opportunities,
            "active_matched_pairs": active_matched_pairs,
            "closed_deals": closed_deals,
            "first_response_minutes": response["average_minutes"],
            "first_response_label": response["label"],
            "approval_clearance_rate": approval["clearance_rate"],
            "demand_supply": self._location_buckets(),
            "client_segments": self._client_segments(),
            "roadmap": self._operating_health_rows(),
            "operations": [
                {"label": "First Response", "value": response["label"], "tone": "blue"},
                {"label": "Pending Approvals", "value": f"{pending_approvals} Needs Review", "tone": "orange"},
                {"label": "Conversion Rate", "value": f"{conversion}%", "tone": "green"},
            ],
        }

    def financial_summary(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        income_records = self._date_filtered_rows("income_transactions", "transaction_date", start_date, end_date)
        expense_records = self._date_filtered_rows("expense_transactions", "transaction_date", start_date, end_date)
        income = self._sum(income_records, "amount")
        expense = self._sum(expense_records, "amount")
        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "total_income": income,
            "total_expense": expense,
            "net_profit": income - expense,
            "profit_margin": round((income - expense) / income * 100, 2) if income > 0 else 0,
            "income_by_type": self._sum_by(income_records, "income_type", "amount"),
            "expense_by_category": self._sum_by(expense_records, "expense_category", "amount"),
        }

    def property_summary(self) -> dict:
        rows = self._table_rows("properties")
        by_status = self._combined_counts(rows, "status")
        by_verification = self._combined_counts(rows, "verification_status")
        presentation_ready = sum(1 for row in rows if self._listing_score(row) >= 80)
        return {
            "total": len(rows),
            "by_status": by_status,
            "by_verification": by_verification,
            "presentation_ready": presentation_ready,
            "properties": [
                {
                    "id": row.get("id"),
                    "code": row.get("property_code"),
                    "title": row.get("title"),
                    "type": row.get("property_type"),
                    "status": row.get("status"),
                    "owner": row.get("owner_name"),
                    "location": row.get("location"),
                    "rent": row.get("monthly_rent"),
                    "price": row.get("sale_price"),
                    "listing_score": self._listing_score(row),
                    "verification": row.get("verification_status"),
                }
                for row in rows
            ],
        }

    def employee_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        policy: AttendancePolicy | None = None,
    ) -> dict:
        rows = self._table_rows("employees")
        attendance = self.attendance_summary(start_date, end_date, policy=policy)
        total_payroll = self._sum(rows, "base_salary")
        return {
            "total": len(rows),
            "total_payroll": total_payroll,
            "attendance": attendance,
            "employees": [
                {
                    "id": row.get("id"),
                    "emp_id": row.get("employee_id"),
                    "name": row.get("full_name"),
                    "position": row.get("position"),
                    "department": row.get("department"),
                    "salary": row.get("base_salary"),
                    "status": row.get("status"),
                }
                for row in rows
            ],
        }

    def attendance_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        policy: AttendancePolicy | None = None,
    ) -> dict:
        rows = self._fetch_attendance_rows()
        return summarize_attendance(rows, policy or AttendancePolicy(), start_date=start_date, end_date=end_date)

    def _table_rows(self, table: str, *, active: bool = False) -> list[dict]:
        columns = self.repo.table_columns(table)
        if not columns:
            return []
        sql = f"SELECT * FROM {self._quote_identifier(table)}"
        where = self._active_where(table, columns) if active else []
        if where:
            sql += " WHERE " + " AND ".join(where)
        order = "id" if "id" in columns else ""
        if order:
            sql += f" ORDER BY {self._quote_identifier(order)} DESC"
        try:
            return self.repo.fetch_all(sql)
        except sqlite3.DatabaseError:
            return []

    def _table_count(self, table: str, *, active: bool = False) -> int:
        return len(self._table_rows(table, active=active))

    def _active_count(self, table: str) -> int:
        return self._table_count(table, active=True)

    def _active_where(self, table: str, columns: set[str]) -> list[str]:
        where: list[str] = []
        if "is_deleted" in columns:
            where.append("COALESCE(is_deleted,0)=0")
        if table == "rent_availability" and "status" in columns:
            where.append("LOWER(COALESCE(status,''))<>'rented'")
        if table == "sale_availability" and "status" in columns:
            where.append("LOWER(COALESCE(status,''))<>'sold'")
        return where

    def _date_filtered_rows(self, table: str, date_key: str, start_date: str | None, end_date: str | None) -> list[dict]:
        return self._filter_rows_by_date(self._table_rows(table), start_date, end_date, key=date_key)

    def _sum_by(self, rows: list[dict], group_key: str, value_key: str) -> dict[str, float]:
        buckets: dict[str, float] = {}
        for row in rows:
            key = str(row.get(group_key) or "Other")
            buckets[key] = buckets.get(key, 0.0) + self._number(row.get(value_key))
        return buckets

    def _fetch_attendance_rows(self) -> list[dict]:
        columns = self.repo.table_columns("attendance")
        if not columns:
            return []
        select = [
            "a.*",
            "e.full_name AS full_name",
            "e.employee_id AS employee_code",
        ]
        try:
            return self.repo.fetch_all(
                f"""SELECT {', '.join(select)}
                    FROM attendance a
                    LEFT JOIN employees e ON a.employee_id=e.id
                    ORDER BY a.date DESC, e.full_name ASC, a.id DESC"""
            )
        except sqlite3.DatabaseError:
            return self._table_rows("attendance")

    def _location_buckets(self) -> list[dict]:
        buckets: dict[str, dict[str, int | str]] = {}
        for table, key in (
            ("rent_requirements", "rent_requirements"),
            ("rent_availability", "rent_availability"),
            ("sale_requirements", "sale_requirements"),
            ("sale_availability", "sale_availability"),
        ):
            for row in self._table_rows(table, active=True):
                label = self._normalize_location(row.get("location"))
                bucket = buckets.setdefault(label, {
                    "location": label,
                    "rent_requirements": 0,
                    "rent_availability": 0,
                    "sale_requirements": 0,
                    "sale_availability": 0,
                })
                bucket[key] = int(bucket[key]) + 1
        rows = sorted(
            buckets.values(),
            key=lambda item: int(item["rent_requirements"]) + int(item["rent_availability"]) + int(item["sale_requirements"]) + int(item["sale_availability"]),
            reverse=True,
        )
        return rows[:6] or [{
            "location": "No Data",
            "rent_requirements": 0,
            "rent_availability": 0,
            "sale_requirements": 0,
            "sale_availability": 0,
        }]

    def _normalize_location(self, value: object) -> str:
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

    def _client_segments(self) -> list[dict]:
        rows = self._table_rows("clients")
        total = len(rows)
        if total <= 0:
            return [
                {"label": "Active Searchers", "value": 0, "percent": 0, "color": "#1976d2"},
                {"label": "Long-Term Leads", "value": 0, "percent": 0, "color": "#43a047"},
                {"label": "Past Clients", "value": 0, "percent": 0, "color": "#007c91"},
            ]
        active = sum(
            1 for row in rows
            if str(row.get("status") or "").strip().lower() == "active"
            and str(row.get("client_type") or "").strip().lower() in {"tenant", "buyer", "investor"}
        )
        long_term = sum(
            1 for row in rows
            if str(row.get("client_type") or "").strip().lower() in {"owner", "seller", "broker"}
        )
        past = max(total - active - long_term, 0)
        return [
            {"label": label, "value": value, "percent": round((value / total) * 100), "color": color}
            for label, value, color in (
                ("Active Searchers", active, "#1976d2"),
                ("Long-Term Leads", long_term, "#43a047"),
                ("Past Clients", past, "#007c91"),
            )
        ]

    def _pending_approvals_count(self) -> int:
        count = 0
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in self._table_rows(table, active=True):
                if str(row.get("approval_status") or "").strip().lower() == "pending":
                    count += 1
        for row in self._table_rows("pending_approvals"):
            if str(row.get("status") or "").strip().lower() == "pending":
                count += 1
        return count

    def _approval_metrics(self) -> dict[str, int]:
        rows = self._table_rows("pending_approvals")
        pending = sum(1 for row in rows if str(row.get("status") or "").strip().lower() == "pending")
        reviewed = sum(1 for row in rows if str(row.get("status") or "").strip().lower() in {"approved", "resend", "rejected"})
        total = pending + reviewed
        return {
            "pending": pending,
            "reviewed": reviewed,
            "clearance_rate": round((reviewed / total) * 100) if total else 100,
        }

    def _closed_deals_count(self, rented_done: int | None = None, sold_done: int | None = None) -> int:
        closed_stage = 0
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in self._table_rows(table, active=True):
                if str(row.get("workflow_stage") or "").strip().lower() == "deal done":
                    closed_stage += 1
        return closed_stage + (rented_done if rented_done is not None else self._table_count("rented_properties")) + (sold_done if sold_done is not None else self._table_count("sold_properties"))

    def _active_match_rows(self, table: str, *, limit: int = 2000) -> list[dict]:
        rows = []
        for row in self._table_rows(table, active=True):
            stage = str(row.get("workflow_stage") or "").strip().lower()
            if stage not in {"closed", "deal done"}:
                rows.append(row)
            if len(rows) >= limit:
                break
        return rows

    def _matched_demand_supply_pairs(self, *, minimum_score: float = 40.0) -> int:
        pairs = 0
        match_sets = (
            ("rent_requirements", "rent_availability"),
            ("sale_requirements", "sale_availability"),
        )
        for requirement_table, availability_table in match_sets:
            requirements = self._active_match_rows(requirement_table)
            availability = self._active_match_rows(availability_table)
            for requirement in requirements:
                for available in availability:
                    score, _reasons = smart_match_score(requirement, available, requirement_table, availability_table)
                    if score >= minimum_score:
                        pairs += 1
        return pairs

    def _first_response_metrics(self, *, start_date: date | None = None, end_date: date | None = None) -> dict[str, object]:
        deltas: list[float] = []
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in self._table_rows(table, active=True):
                created = self._parse_datetime(row.get("created_at") or row.get("date"))
                contacted = self._parse_datetime(row.get("last_contacted"))
                if not created or not contacted:
                    continue
                if start_date and created.date() < start_date:
                    continue
                if end_date and created.date() > end_date:
                    continue
                minutes = (contacted - created).total_seconds() / 60
                if minutes >= 0:
                    deltas.append(minutes)
        if not deltas:
            return {"average_minutes": None, "score": 0, "label": "No Data"}
        average = sum(deltas) / len(deltas)
        score = max(0, min(100, round(100 - max(average - 15, 0) * 1.5)))
        return {"average_minutes": round(average, 1), "score": score, "label": self._duration_label(average)}

    def _operating_health_rows(self) -> list[dict]:
        today = date.today()
        rows = []
        for label, days in (("30 Days", 30), ("90 Days", 90), ("180 Days", 180)):
            start = today - timedelta(days=days - 1)
            response = self._first_response_metrics(start_date=start, end_date=today)
            approval = self._approval_metrics()
            conversion = self._conversion_for_period(start, today)
            rows.append({
                "period": label,
                "response_time": response["score"],
                "approvals_cleared": approval["clearance_rate"],
                "conversion": conversion,
            })
        return rows

    def _conversion_for_period(self, start: date, end: date) -> int:
        closed = 0
        for table, date_key in (("rented_properties", "closed_at"), ("sold_properties", "closed_at")):
            for row in self._table_rows(table):
                closed_date = self._parse_date(row.get(date_key))
                if closed_date and start <= closed_date <= end:
                    closed += 1
        created = 0
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in self._table_rows(table):
                row_date = self._parse_date(row.get("created_at") or row.get("date"))
                if row_date and start <= row_date <= end:
                    created += 1
        opportunities = created + closed
        return round((closed / opportunities) * 100) if opportunities else 0

    def _listing_score(self, row: dict) -> int:
        fields = (
            "title", "property_type", "status", "owner_name", "owner_contact",
            "location", "area", "floor", "bedrooms", "bathrooms", "facilities",
            "nearby_landmarks", "verification_status", "photo_paths",
        )
        present = sum(1 for field in fields if str(row.get(field) or "").strip())
        return round(present / len(fields) * 100)

    def _duration_label(self, minutes: float | int | None) -> str:
        if minutes is None:
            return "No Data"
        if minutes < 60:
            return f"{round(minutes)} Min"
        hours = minutes / 60
        return f"{hours:.1f} Hrs"

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        parsed_date = self._parse_date(value)
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        if parsed_date:
            return datetime.combine(parsed_date, datetime.min.time())
        return None

    def _fetch_section_rows(
        self,
        table: str,
        preferred_fields: Iterable[str],
        start_date: str | None,
        end_date: str | None,
        *,
        date_filter_key: str = "date",
    ) -> list[dict]:
        columns = self.repo.table_columns(table)
        if not columns:
            return []
        expressions = [self._field_expression(field, columns) for field in preferred_fields]
        order_column = "id" if "id" in columns else self._source_column("date", columns)
        sql = f"SELECT {', '.join(expressions)} FROM {self._quote_identifier(table)}"
        where_parts: list[str] = []
        if "is_deleted" in columns:
            where_parts.append("COALESCE(is_deleted,0)=0")
        if table == "rent_availability" and "status" in columns:
            where_parts.append("LOWER(COALESCE(status,''))<>'rented'")
        elif table == "sale_availability" and "status" in columns:
            where_parts.append("LOWER(COALESCE(status,''))<>'sold'")
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if order_column:
            sql += f" ORDER BY {self._quote_identifier(order_column)} DESC"
        rows = self.repo.fetch_all(sql)
        return self._filter_rows_by_date(rows, start_date, end_date, key=date_filter_key)

    def _build_rent_text(
        self,
        summary: dict,
        requirements: list[dict],
        availability: list[dict],
        rented: list[dict],
        start_date: str | None,
        end_date: str | None,
    ) -> str:
        lines = self._header("RENT DEALINGS REPORT", start_date, end_date)
        lines += [
            "SUMMARY",
            "-" * 78,
            f"Requirements:          {summary['requirements']}",
            f"Available properties:  {summary['available_properties']}",
            f"Rented deals done:     {summary['completed_rent_deals']}",
            f"Total client budget:   {self._money(summary['total_requirement_budget'])}",
            f"Average client budget: {self._money(summary['average_requirement_budget'])}",
            f"Total monthly rent:    {self._money(summary['total_monthly_rent'])}",
            f"Average monthly rent:  {self._money(summary['average_monthly_rent'])}",
            f"Completed rent value:  {self._money(summary['total_completed_monthly_rent'])}",
            "",
            "Pipeline by stage:",
        ]
        lines += self._count_lines(summary["stage_counts"])
        lines += ["", "Top locations:"]
        lines += self._count_lines(summary["location_counts"], limit=10)
        lines += ["", "Completed rent locations:"]
        lines += self._count_lines(summary["completed_location_counts"], limit=10)
        lines += ["", "RENT REQUIREMENTS", "-" * 78]
        lines += self._section_lines(
            requirements,
            "client_name",
            "property_requires",
            "budget",
            "Budget",
        )
        lines += ["", "RENT AVAILABILITY", "-" * 78]
        lines += self._section_lines(
            availability,
            "owner_name",
            "property_availability",
            "monthly_rent",
            "Rent",
        )
        lines += ["", "RENTED PROPERTIES", "-" * 78]
        lines += self._section_lines(
            rented,
            "owner_name",
            "property_availability",
            "monthly_rent",
            "Rent",
            date_key="closed_at",
        )
        return "\n".join(lines).rstrip() + "\n"

    def _build_sale_text(
        self,
        summary: dict,
        requirements: list[dict],
        availability: list[dict],
        sold: list[dict],
        start_date: str | None,
        end_date: str | None,
    ) -> str:
        lines = self._header("SALE DEALINGS REPORT", start_date, end_date)
        lines += [
            "SUMMARY",
            "-" * 78,
            f"Requirements:          {summary['requirements']}",
            f"Available properties:  {summary['available_properties']}",
            f"Sold deals done:       {summary['completed_sale_deals']}",
            f"Total client budget:   {self._money(summary['total_requirement_budget'])}",
            f"Average client budget: {self._money(summary['average_requirement_budget'])}",
            f"Total owner demand:    {self._money(summary['total_owner_demand'])}",
            f"Average owner demand:  {self._money(summary['average_owner_demand'])}",
            f"Completed sale value:  {self._money(summary['total_completed_sale_value'])}",
            "",
            "Pipeline by stage:",
        ]
        lines += self._count_lines(summary["stage_counts"])
        lines += ["", "Top locations:"]
        lines += self._count_lines(summary["location_counts"], limit=10)
        lines += ["", "Completed sale locations:"]
        lines += self._count_lines(summary["completed_location_counts"], limit=10)
        lines += ["", "SALE REQUIREMENTS", "-" * 78]
        lines += self._section_lines(
            requirements,
            "client_name",
            "property_requires",
            "budget",
            "Budget",
        )
        lines += ["", "SALE AVAILABILITY", "-" * 78]
        lines += self._section_lines(
            availability,
            "owner_name",
            "property_availability",
            "demand",
            "Demand",
        )
        lines += ["", "SOLD PROPERTIES", "-" * 78]
        lines += self._section_lines(
            sold,
            "owner_name",
            "property_availability",
            "demand",
            "Demand",
            date_key="closed_at",
        )
        return "\n".join(lines).rstrip() + "\n"

    def _header(self, title: str, start_date: str | None, end_date: str | None) -> list[str]:
        period = "All records"
        if self._valid_date(start_date) or self._valid_date(end_date):
            period = f"{self._display_date(start_date) if start_date else 'Beginning'} to {self._display_date(end_date) if end_date else 'Today'}"
        return [
            "=" * 78,
            title,
            f"Company: {self.company_name}",
            f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Period: {period}",
            "=" * 78,
            "",
        ]

    def _section_lines(
        self,
        rows: list[dict],
        name_key: str,
        property_key: str,
        amount_key: str,
        amount_label: str,
        *,
        date_key: str = "date",
    ) -> list[str]:
        if not rows:
            return ["No records found."]
        lines: list[str] = []
        for row in rows:
            lines.append(
                f"#{row.get('id', '-'):<5} "
                f"{self._clip(self._display_date(row.get(date_key)), 10):<10} "
                f"{self._clip(row.get(name_key), 22):<22} "
                f"{self._clip(row.get('location'), 18):<18} "
                f"{amount_label}: {self._money(row.get(amount_key)):<16} "
                f"Stage: {self._clip(row.get('workflow_stage') or 'Lead', 14)}"
            )
            detail = self._clip(row.get(property_key), 28)
            contact = self._clip(row.get("contact"), 18)
            if detail or contact:
                lines.append(f"       Property: {detail or '-':<28} Contact: {contact or '-'}")
        return lines

    def _count_lines(self, counts: dict[str, int], *, limit: int | None = None) -> list[str]:
        if not counts:
            return ["  None"]
        items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [f"  {name:<28} {count:>5}" for name, count in items]

    def _tag_rows(self, section: str, rows: list[dict]) -> list[dict]:
        return [{"section": section, **row} for row in rows]

    def _combined_counts(self, rows: list[dict], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "Unknown").strip() or "Unknown"
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _sum(self, rows: list[dict], key: str) -> float:
        return sum(self._number(row.get(key)) for row in rows)

    def _avg(self, rows: list[dict], key: str) -> float:
        values = [self._number(row.get(key)) for row in rows if row.get(key) not in (None, "")]
        return sum(values) / len(values) if values else 0.0

    def _money(self, value: object) -> str:
        return f"{self.currency_symbol}{self._number(value):,.0f}"

    def _number(self, value: object) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return 0.0

    def _clip(self, value: object, max_chars: int) -> str:
        text = str(value or "").strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _field_expression(self, field: str, columns: set[str]) -> str:
        alias = self._quote_identifier(field)
        sources = self._source_columns(field, columns)
        default = self.FIELD_DEFAULTS.get(field)
        if sources:
            parts = [f"NULLIF({self._quote_identifier(source)}, '')" for source in sources]
            if default is not None:
                parts.append(default)
            if len(parts) == 1:
                return f"{parts[0]} AS {alias}"
            return f"COALESCE({', '.join(parts)}) AS {alias}"
        default = self.FIELD_DEFAULTS.get(field, "''")
        return f"{default} AS {alias}"

    def _source_columns(self, field: str, columns: set[str]) -> list[str]:
        return [candidate for candidate in self.FIELD_ALIASES.get(field, (field,)) if candidate in columns]

    def _source_column(self, field: str, columns: set[str]) -> str | None:
        sources = self._source_columns(field, columns)
        return sources[0] if sources else None

    def _filter_rows_by_date(
        self,
        rows: list[dict],
        start_date: str | None,
        end_date: str | None,
        *,
        key: str = "date",
    ) -> list[dict]:
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if not start and not end:
            return rows
        filtered: list[dict] = []
        for row in rows:
            row_date = self._parse_date(row.get(key))
            if not row_date:
                continue
            if start and row_date < start:
                continue
            if end and row_date > end:
                continue
            filtered.append(row)
        return filtered

    def _display_date(self, value: object) -> str:
        parsed = self._parse_date(value)
        if parsed:
            return parsed.strftime("%d/%m/%Y")
        return str(value or "")

    def _parse_date(self, value: object) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        text = text.split("T", 1)[0].split(" ", 1)[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _quote_identifier(self, value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    def _valid_date(self, value: str | None) -> bool:
        return self._parse_date(value) is not None


def export_report_text(result: ReportResult, path: str | Path) -> Path:
    output = Path(path)
    _ensure_parent(output)
    output.write_text(result.text, encoding="utf-8")
    return output


def export_report_csv(result: ReportResult, path: str | Path) -> Path:
    output = Path(path)
    _ensure_parent(output)
    headers = _csv_headers(result.rows)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result.rows)
    return output


PDF_LABELS = {
    "id": "ID",
    "date": "Date",
    "closed_at": "Closed",
    "client_name": "Client",
    "owner_name": "Owner",
    "contact": "Contact",
    "property_requires": "Requirement",
    "property_availability": "Property",
    "size": "Rooms",
    "measurement": "Measure",
    "measurement_unit": "Unit",
    "budget": "Budget",
    "monthly_rent": "Rent",
    "demand": "Demand",
    "floor": "Floor",
    "location": "Location",
    "workflow_stage": "Stage",
    "approval_status": "Approval",
    "source_id": "Source",
    "archived_by": "Archived By",
}

PDF_MONEY_KEYS = {
    "budget", "monthly_rent", "demand", "deposit", "maintenance_charge",
    "total_requirement_budget", "average_requirement_budget",
    "total_monthly_rent", "average_monthly_rent",
    "total_completed_monthly_rent", "total_owner_demand",
    "average_owner_demand", "total_completed_sale_value",
}


def export_report_pdf(result: ReportResult, path: str | Path) -> Path:
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError("fpdf2 is required to export PDF reports.") from exc

    output = Path(path)
    _ensure_parent(output)

    class NumberedReportPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-10)
            self.set_font("Helvetica", size=8)
            self.set_text_color(90, 100, 115)
            self.cell(0, 6, f"Page {self.page_no()} of {{nb}}", align="R")

    pdf = NumberedReportPDF(orientation="L", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=13)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    _render_pdf_header(pdf, result)
    _render_pdf_summary(pdf, result)
    _render_pdf_sections(pdf, result)
    pdf.output(str(output))
    return output


def _render_pdf_header(pdf, result: ReportResult) -> None:
    company, period = _extract_report_meta(result)
    pdf.set_fill_color(10, 22, 42)
    pdf.rect(0, 0, pdf.w, 27, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_xy(pdf.l_margin, 8)
    pdf.cell(0, 7, _ascii(result.title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(211, 226, 247)
    meta = f"{company}   |   {period}   |   Generated {result.generated_at.strftime('%d/%m/%Y %I:%M %p')}"
    pdf.cell(0, 6, _ascii(meta), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_text_color(10, 22, 42)


def _render_pdf_summary(pdf, result: ReportResult) -> None:
    pairs = _summary_pairs(result.summary)
    if not pairs:
        return
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    gap = 3
    cols = 4
    card_w = (usable - gap * (cols - 1)) / cols
    card_h = 17
    start_x = pdf.l_margin
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 8)
    for idx, (label, value) in enumerate(pairs[:8]):
        col = idx % cols
        if idx and col == 0:
            y += card_h + gap
        x = start_x + col * (card_w + gap)
        if y + card_h > pdf.h - pdf.b_margin:
            pdf.add_page()
            y = pdf.get_y()
        pdf.set_fill_color(247, 250, 252)
        pdf.set_draw_color(211, 222, 235)
        pdf.rect(x, y, card_w, card_h, "DF")
        pdf.set_xy(x + 3, y + 3)
        pdf.set_text_color(77, 91, 111)
        pdf.set_font("Helvetica", "B", 7.4)
        pdf.cell(card_w - 6, 4, _ascii(label), new_x="LEFT", new_y="NEXT")
        pdf.set_x(x + 3)
        pdf.set_text_color(10, 22, 42)
        pdf.set_font("Helvetica", "B", 10.6)
        pdf.cell(card_w - 6, 5, _ascii(str(value)), new_x="LEFT", new_y="NEXT")
    pdf.set_y(y + card_h + 8)


def _render_pdf_sections(pdf, result: ReportResult) -> None:
    groups: dict[str, list[dict]] = {}
    for row in result.rows:
        section = str(row.get("section") or "Records")
        groups.setdefault(section, []).append(row)

    if not groups:
        _render_pdf_text_fallback(pdf, result)
        return

    for section, rows in groups.items():
        columns = _section_columns(section)
        _ensure_pdf_space(pdf, 20)
        pdf.set_fill_color(234, 242, 251)
        pdf.set_draw_color(191, 208, 228)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.cell(0, 8, _ascii(f"{section} ({len(rows)})"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        _render_pdf_table_header(pdf, columns)
        for index, row in enumerate(rows):
            _render_pdf_table_row(pdf, columns, row, shaded=index % 2 == 1)
        pdf.ln(4)


def _render_pdf_table_header(pdf, columns: list[tuple[str, str, float]]) -> None:
    _ensure_pdf_space(pdf, 12)
    pdf.set_font("Helvetica", "B", 7.2)
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(37, 99, 235)
    pdf.set_draw_color(37, 99, 235)
    for _key, label, width in columns:
        pdf.cell(width, 6.5, _ascii(label), border=1, fill=True)
    pdf.ln()


def _render_pdf_table_row(pdf, columns: list[tuple[str, str, float]], row: dict, *, shaded: bool) -> None:
    _ensure_pdf_space(pdf, 8)
    pdf.set_font("Helvetica", size=7.0)
    pdf.set_text_color(15, 23, 42)
    pdf.set_draw_color(226, 232, 240)
    fill = shaded
    if fill:
        pdf.set_fill_color(248, 250, 252)
    for key, _label, width in columns:
        value = _format_pdf_cell(key, row.get(key))
        pdf.cell(width, 6.2, _ascii(_clip_pdf(value, width)), border=1, fill=fill)
    pdf.ln()


def _render_pdf_text_fallback(pdf, result: ReportResult) -> None:
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Courier", size=9)
    for line in result.text.splitlines():
        _ensure_pdf_space(pdf, 6)
        pdf.multi_cell(0, 5.5, _ascii(line) or " ", new_x="LMARGIN", new_y="NEXT")


def _section_columns(section: str) -> list[tuple[str, str, float]]:
    normalized = section.lower()
    if "requirement" in normalized:
        keys = ("id", "date", "client_name", "contact", "property_requires", "size", "budget", "floor", "location", "workflow_stage")
        weights = (0.7, 1.0, 1.8, 1.35, 2.1, 0.75, 1.35, 0.85, 1.7, 1.15)
    elif "rented" in normalized or "sold" in normalized:
        amount_key = "monthly_rent" if "rented" in normalized else "demand"
        keys = ("id", "source_id", "closed_at", "owner_name", "contact", "property_availability", amount_key, "floor", "location")
        weights = (0.65, 0.8, 1.0, 1.8, 1.3, 2.2, 1.3, 0.8, 1.6)
    else:
        amount_key = "monthly_rent" if "rent" in normalized else "demand"
        keys = ("id", "date", "owner_name", "contact", "property_availability", "size", amount_key, "floor", "location", "workflow_stage")
        weights = (0.7, 1.0, 1.8, 1.35, 2.1, 0.75, 1.35, 0.85, 1.7, 1.15)
    usable_width = 277.0
    scale = usable_width / sum(weights)
    return [(key, PDF_LABELS.get(key, key.replace("_", " ").title()), weight * scale) for key, weight in zip(keys, weights)]


def _summary_pairs(summary: dict) -> list[tuple[str, str]]:
    if not summary:
        return []
    if "rent" in summary or "sale" in summary:
        rent = summary.get("rent") or {}
        sale = summary.get("sale") or {}
        return [
            ("Rent Requirements", _format_summary_value(rent.get("requirements"))),
            ("Rent Availability", _format_summary_value(rent.get("available_properties"))),
            ("Rented Deals", _format_summary_value(rent.get("completed_rent_deals"))),
            ("Rent Value", _format_summary_value(rent.get("total_monthly_rent"), money=True)),
            ("Sale Requirements", _format_summary_value(sale.get("requirements"))),
            ("Sale Availability", _format_summary_value(sale.get("available_properties"))),
            ("Sold Deals", _format_summary_value(sale.get("completed_sale_deals"))),
            ("Sale Demand", _format_summary_value(sale.get("total_owner_demand"), money=True)),
        ]
    preferred = [
        "requirements",
        "available_properties",
        "completed_rent_deals",
        "completed_sale_deals",
        "total_requirement_budget",
        "average_requirement_budget",
        "total_monthly_rent",
        "total_owner_demand",
        "total_completed_monthly_rent",
        "total_completed_sale_value",
    ]
    pairs = []
    for key in preferred:
        if key in summary:
            pairs.append((_humanize(key), _format_summary_value(summary[key], money=key in PDF_MONEY_KEYS)))
    return pairs


def _extract_report_meta(result: ReportResult) -> tuple[str, str]:
    company = "Real Estate CRM"
    period = "All records"
    for line in result.text.splitlines()[:10]:
        if line.startswith("Company:"):
            company = line.split(":", 1)[1].strip() or company
        elif line.startswith("Period:"):
            period = line.split(":", 1)[1].strip() or period
    return company, period


def _format_pdf_cell(key: str, value: object) -> str:
    if key in PDF_MONEY_KEYS:
        return _format_summary_value(value, money=True)
    return str(value or "").strip()


def _format_summary_value(value: object, *, money: bool = False) -> str:
    if isinstance(value, dict):
        return str(sum(_number(item) for item in value.values()))
    if money:
        return f"Rs. {_number(value):,.0f}"
    number = _number(value)
    if value in (None, ""):
        return "0"
    if abs(number - int(number)) < 0.0001:
        return f"{int(number):,}"
    return f"{number:,.1f}"


def _number(value: object) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(str(value).replace(",", "").replace("Rs.", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _humanize(key: str) -> str:
    return key.replace("_", " ").title()


def _ensure_pdf_space(pdf, height: float) -> None:
    if pdf.get_y() + height > pdf.h - pdf.b_margin:
        pdf.add_page()


def _clip_pdf(value: str, width: float) -> str:
    max_chars = max(4, int(width / 2.15))
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "."


def _ascii(value: object) -> str:
    return "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(value or "")).strip()


def _csv_headers(rows: list[dict]) -> list[str]:
    preferred = [
        "section", "id", "date", "client_name", "owner_name", "contact",
        "property_requires", "property_availability", "size", "measurement",
        "measurement_unit", "budget", "monthly_rent", "demand", "floor", "location",
        "workflow_stage", "priority", "assigned_to", "deal_probability",
        "approval_status", "remarks",
    ]
    present = {key for row in rows for key in row}
    ordered = [key for key in preferred if key in present]
    ordered += sorted(present - set(ordered))
    return ordered or ["section"]


def _ensure_parent(path: Path) -> None:
    parent = path.parent
    if str(parent) and not parent.exists():
        os.makedirs(parent, exist_ok=True)
