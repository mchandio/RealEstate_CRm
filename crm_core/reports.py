"""Report generation services for rent and sale sections."""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .db import SQLiteRepository


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
        "measurement", "budget", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    RENT_AVAILABILITY_FIELDS = [
        "id", "date", "owner_name", "contact", "property_availability", "size",
        "measurement", "monthly_rent", "floor", "location", "deposit",
        "maintenance_charge", "workflow_stage", "priority", "assigned_to",
        "deal_probability", "approval_status", "remarks",
    ]
    SALE_REQUIREMENT_FIELDS = [
        "id", "date", "client_name", "contact", "property_requires", "size",
        "measurement", "budget", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    SALE_AVAILABILITY_FIELDS = [
        "id", "date", "owner_name", "contact", "property_availability", "size",
        "measurement", "demand", "floor", "location", "workflow_stage",
        "priority", "assigned_to", "deal_probability", "approval_status",
        "remarks",
    ]
    FIELD_ALIASES = {
        "date": ("date", "date_created", "date_posted", "created_at", "transaction_date"),
        "contact": ("contact", "contact_phone", "phone", "owner_contact"),
        "property_requires": ("property_requires", "property_type", "property_requirement"),
        "property_availability": ("property_availability", "property_type"),
        "size": ("size", "size_beds"),
        "measurement": ("measurement", "sq_ft_yards", "sq_ft"),
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
        summary = {
            "requirements": len(requirements),
            "available_properties": len(availability),
            "total_requirement_budget": self._sum(requirements, "budget"),
            "average_requirement_budget": self._avg(requirements, "budget"),
            "total_monthly_rent": self._sum(availability, "monthly_rent"),
            "average_monthly_rent": self._avg(availability, "monthly_rent"),
            "stage_counts": self._combined_counts(requirements + availability, "workflow_stage"),
            "location_counts": self._combined_counts(requirements + availability, "location"),
        }
        csv_rows = (
            self._tag_rows("Rent Requirement", requirements)
            + self._tag_rows("Rent Availability", availability)
        )
        text = self._build_rent_text(summary, requirements, availability, start_date, end_date)
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
        summary = {
            "requirements": len(requirements),
            "available_properties": len(availability),
            "total_requirement_budget": self._sum(requirements, "budget"),
            "average_requirement_budget": self._avg(requirements, "budget"),
            "total_owner_demand": self._sum(availability, "demand"),
            "average_owner_demand": self._avg(availability, "demand"),
            "stage_counts": self._combined_counts(requirements + availability, "workflow_stage"),
            "location_counts": self._combined_counts(requirements + availability, "location"),
        }
        csv_rows = (
            self._tag_rows("Sale Requirement", requirements)
            + self._tag_rows("Sale Availability", availability)
        )
        text = self._build_sale_text(summary, requirements, availability, start_date, end_date)
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

    def _fetch_section_rows(
        self,
        table: str,
        preferred_fields: Iterable[str],
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict]:
        columns = self.repo.table_columns(table)
        if not columns:
            return []
        expressions = [self._field_expression(field, columns) for field in preferred_fields]
        order_column = "id" if "id" in columns else self._source_column("date", columns)
        sql = f"SELECT {', '.join(expressions)} FROM {self._quote_identifier(table)}"
        if order_column:
            sql += f" ORDER BY {self._quote_identifier(order_column)} DESC"
        rows = self.repo.fetch_all(sql)
        return self._filter_rows_by_date(rows, start_date, end_date)

    def _build_rent_text(
        self,
        summary: dict,
        requirements: list[dict],
        availability: list[dict],
        start_date: str | None,
        end_date: str | None,
    ) -> str:
        lines = self._header("RENT DEALINGS REPORT", start_date, end_date)
        lines += [
            "SUMMARY",
            "-" * 78,
            f"Requirements:          {summary['requirements']}",
            f"Available properties:  {summary['available_properties']}",
            f"Total client budget:   {self._money(summary['total_requirement_budget'])}",
            f"Average client budget: {self._money(summary['average_requirement_budget'])}",
            f"Total monthly rent:    {self._money(summary['total_monthly_rent'])}",
            f"Average monthly rent:  {self._money(summary['average_monthly_rent'])}",
            "",
            "Pipeline by stage:",
        ]
        lines += self._count_lines(summary["stage_counts"])
        lines += ["", "Top locations:"]
        lines += self._count_lines(summary["location_counts"], limit=10)
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
        return "\n".join(lines).rstrip() + "\n"

    def _build_sale_text(
        self,
        summary: dict,
        requirements: list[dict],
        availability: list[dict],
        start_date: str | None,
        end_date: str | None,
    ) -> str:
        lines = self._header("SALE DEALINGS REPORT", start_date, end_date)
        lines += [
            "SUMMARY",
            "-" * 78,
            f"Requirements:          {summary['requirements']}",
            f"Available properties:  {summary['available_properties']}",
            f"Total client budget:   {self._money(summary['total_requirement_budget'])}",
            f"Average client budget: {self._money(summary['average_requirement_budget'])}",
            f"Total owner demand:    {self._money(summary['total_owner_demand'])}",
            f"Average owner demand:  {self._money(summary['average_owner_demand'])}",
            "",
            "Pipeline by stage:",
        ]
        lines += self._count_lines(summary["stage_counts"])
        lines += ["", "Top locations:"]
        lines += self._count_lines(summary["location_counts"], limit=10)
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
    ) -> list[str]:
        if not rows:
            return ["No records found."]
        lines: list[str] = []
        for row in rows:
            lines.append(
                f"#{row.get('id', '-'):<5} "
                f"{self._clip(self._display_date(row.get('date')), 10):<10} "
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
    ) -> list[dict]:
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if not start and not end:
            return rows
        filtered: list[dict] = []
        for row in rows:
            row_date = self._parse_date(row.get("date"))
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
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "".join(ch if ord(ch) < 128 else " " for ch in result.title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(80, 90, 105)
    pdf.cell(0, 6, f"Generated: {result.generated_at.strftime('%d/%m/%Y %I:%M %p')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(190, 200, 215)
    pdf.line(pdf.l_margin, pdf.get_y() + 2, pdf.w - pdf.r_margin, pdf.get_y() + 2)
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Courier", size=10.5)
    line_height = 5.8
    for line in result.text.splitlines():
        clean = "".join(ch if ord(ch) < 128 else " " for ch in line)
        pdf.multi_cell(0, line_height, clean or " ", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(output))
    return output


def _csv_headers(rows: list[dict]) -> list[str]:
    preferred = [
        "section", "id", "date", "client_name", "owner_name", "contact",
        "property_requires", "property_availability", "size", "measurement",
        "budget", "monthly_rent", "demand", "floor", "location",
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
