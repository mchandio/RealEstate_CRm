"""Consistent date parsing, storage, and display helpers.

Phase 1 stores date-only values as YYYY-MM-DD. This avoids browser timezone
shifts where 01/01 becomes 31/12 on another machine. The system uses
Asia/Karachi timezone for datetime operations where timezone awareness is needed.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


KARACHI_TZ = ZoneInfo("Asia/Karachi")
UTC_TZ = timezone.utc

DATE_STORAGE_FORMAT = "%Y-%m-%d"
DATE_DISPLAY_FORMAT = "%d/%m/%Y"
DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y")


class DateUtils:
    """Date handling with timezone support for cross-timezone consistency."""

    @staticmethod
    def parse_date(value: object) -> date | None:
        """Parse various date formats and return a date object.

        Handles YYYY-MM-DD, DD/MM/YYYY, ISO datetime strings, and date objects.
        """
        if isinstance(value, datetime):
            # Convert to Karachi time before extracting date
            if value.tzinfo is None:
                return value.date()
            local = value.astimezone(KARACHI_TZ)
            return local.date()
        if isinstance(value, date):
            return value
        text = str(value or "").strip()
        if not text:
            return None
        # Handle ISO format with timezone (e.g., '2025-01-01T00:00:00+00:00')
        if "T" in text:
            try:
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    return dt.date()
                local = dt.astimezone(KARACHI_TZ)
                return local.date()
            except (ValueError, TypeError):
                pass
        # Handle date-only strings
        text = text.split("T", 1)[0][:10]
        for fmt in DATE_INPUT_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def parse_datetime(value: object) -> datetime | None:
        """Parse value and return a timezone-aware datetime in Karachi time.

        Useful when both date and time are needed with timezone awareness.
        """
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=KARACHI_TZ)
            return value.astimezone(KARACHI_TZ)
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time()).replace(tzinfo=KARACHI_TZ)
        text = str(value or "").strip()
        if not text:
            return None
        # Handle ISO format with timezone
        if "T" in text:
            try:
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=KARACHI_TZ)
                return dt.astimezone(KARACHI_TZ)
            except (ValueError, TypeError):
                pass
        # Try date-only formats, assume midnight Karachi time
        text_clean = text.split("T", 1)[0][:10]
        for fmt in DATE_INPUT_FORMATS:
            try:
                naive = datetime.strptime(text_clean, fmt)
                return naive.replace(tzinfo=KARACHI_TZ)
            except ValueError:
                continue
        return None

    @staticmethod
    def store_date(value: object) -> str:
        """Convert user input to YYYY-MM-DD for storage.

        Accepts DD/MM/YYYY, YYYY-MM-DD, or datetime objects.
        Returns date-only string to avoid timezone shift issues.
        Note: Date-only storage prevents 01/01 becoming 31/12 across timezones.
        """
        parsed = DateUtils.parse_date(value)
        if parsed is None:
            raise ValueError("Use date format YYYY-MM-DD or DD/MM/YYYY")
        return parsed.strftime(DATE_STORAGE_FORMAT)

    @staticmethod
    def store_datetime_utc(value: object) -> str | None:
        """Convert user input to UTC ISO format for storage.

        Use this only when time precision AND timezone safety are required.
        For date-only fields, use store_date() instead to avoid date shifts.
        """
        if value in (None, ""):
            return None
        parsed = DateUtils.parse_datetime(value)
        if parsed is None:
            raise ValueError("Use date format YYYY-MM-DD or DD/MM/YYYY")
        utc_dt = parsed.astimezone(UTC_TZ)
        return utc_dt.isoformat()

    @staticmethod
    def display_date(value: object) -> str:
        """Convert stored date to DD/MM/YYYY format for display.

        Handles YYYY-MM-DD strings, ISO format strings, and date objects.
        """
        if value in (None, ""):
            return ""
        parsed = DateUtils.parse_date(value)
        if parsed is None:
            return str(value)
        return parsed.strftime(DATE_DISPLAY_FORMAT)
