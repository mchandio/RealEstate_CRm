"""Consistent date parsing and display helpers.

Phase 1 stores date-only values as YYYY-MM-DD. Keeping dates as date-only avoids
browser timezone shifts such as 01/01 becoming 31/12 on another machine.
"""

from __future__ import annotations

from datetime import date, datetime


DATE_STORAGE_FORMAT = "%Y-%m-%d"
DATE_DISPLAY_FORMAT = "%d/%m/%Y"
DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y")


class DateUtils:
    @staticmethod
    def parse_date(value: object) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value or "").strip()
        if not text:
            return None
        text = text.split("T", 1)[0][:10]
        for fmt in DATE_INPUT_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def store_date(value: object) -> str:
        parsed = DateUtils.parse_date(value)
        if parsed is None:
            raise ValueError("Use date format YYYY-MM-DD or DD/MM/YYYY")
        return parsed.strftime(DATE_STORAGE_FORMAT)

    @staticmethod
    def display_date(value: object) -> str:
        parsed = DateUtils.parse_date(value)
        if parsed is None:
            return "" if value in (None, "") else str(value)
        return parsed.strftime(DATE_DISPLAY_FORMAT)
