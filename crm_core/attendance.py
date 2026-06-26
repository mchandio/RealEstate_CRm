"""Shared attendance policy, calculations, and summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from .date_utils import DateUtils


ATTENDANCE_STATUSES = (
    "Not Marked",
    "Present",
    "Late",
    "Absent",
    "Leave",
    "Half Day",
    "Remote",
    "Field Visit",
)
LEAVE_TYPES = ("", "Sick", "Casual", "Annual", "Emergency", "Unpaid")


@dataclass(frozen=True)
class AttendancePolicy:
    shift_name: str = "Office"
    scheduled_start: str = "09:30"
    scheduled_end: str = "18:00"
    grace_minutes: int = 10
    half_day_minutes: int = 240


DEFAULT_POLICY = AttendancePolicy()


def parse_time(value: Any) -> time | None:
    if isinstance(value, time):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(text.upper(), fmt).time()
        except ValueError:
            continue
    return None


def format_minutes(minutes: Any) -> str:
    total = safe_int(minutes)
    hours, remainder = divmod(max(total, 0), 60)
    return f"{hours:02d}:{remainder:02d}"


def attendance_policy_from_settings(settings: dict[str, Any] | None = None) -> AttendancePolicy:
    settings = settings or {}
    return AttendancePolicy(
        shift_name=str(settings.get("attendance_shift_name") or DEFAULT_POLICY.shift_name),
        scheduled_start=str(settings.get("attendance_shift_start") or DEFAULT_POLICY.scheduled_start),
        scheduled_end=str(settings.get("attendance_shift_end") or DEFAULT_POLICY.scheduled_end),
        grace_minutes=safe_int(settings.get("attendance_grace_minutes"), DEFAULT_POLICY.grace_minutes),
        half_day_minutes=safe_int(settings.get("attendance_half_day_minutes"), DEFAULT_POLICY.half_day_minutes),
    )


def calculate_attendance(data: dict[str, Any], policy: AttendancePolicy = DEFAULT_POLICY) -> dict[str, Any]:
    """Return normalized attendance values plus derived time metrics.

    The input row is not mutated. Calculations intentionally stay simple and
    auditable: late and early-leave are based on scheduled shift bounds, worked
    minutes are check-in to check-out, and overtime is minutes beyond the shift.
    """
    row = dict(data or {})
    status = normalize_status(row.get("status"))
    check_in = parse_time(row.get("check_in"))
    check_out = parse_time(row.get("check_out"))
    scheduled_start_text = str(row.get("scheduled_start") or policy.scheduled_start)
    scheduled_end_text = str(row.get("scheduled_end") or policy.scheduled_end)
    scheduled_start = parse_time(scheduled_start_text) or parse_time(policy.scheduled_start)
    scheduled_end = parse_time(scheduled_end_text) or parse_time(policy.scheduled_end)

    worked_minutes = minutes_between(check_in, check_out)
    scheduled_minutes = minutes_between(scheduled_start, scheduled_end) or 0
    late_minutes = 0
    early_leave_minutes = 0
    overtime_minutes = 0

    if status in {"Leave", "Absent"}:
        worked_minutes = 0
    elif worked_minutes:
        overtime_minutes = max(0, worked_minutes - scheduled_minutes)
        if scheduled_start and check_in and status not in {"Remote", "Field Visit"}:
            late_minutes = max(0, minutes_since_midnight(check_in) - minutes_since_midnight(scheduled_start) - policy.grace_minutes)
        if scheduled_end and check_out and status not in {"Remote", "Field Visit"}:
            early_leave_minutes = max(0, minutes_since_midnight(scheduled_end) - minutes_since_midnight(check_out))

    if status == "Not Marked":
        if row.get("leave_type"):
            status = "Leave"
        elif check_in:
            status = "Present"
    if status == "Present" and late_minutes > 0:
        status = "Late"
    if status in {"Present", "Late"} and worked_minutes and worked_minutes < policy.half_day_minutes:
        status = "Half Day"

    return {
        **row,
        "status": status,
        "shift_name": row.get("shift_name") or policy.shift_name,
        "scheduled_start": scheduled_start_text,
        "scheduled_end": scheduled_end_text,
        "worked_minutes": worked_minutes,
        "late_minutes": late_minutes,
        "early_leave_minutes": early_leave_minutes,
        "overtime_minutes": overtime_minutes,
    }


def summarize_attendance(
    rows: list[dict[str, Any]],
    policy: AttendancePolicy = DEFAULT_POLICY,
    *,
    start_date: Any = None,
    end_date: Any = None,
) -> dict[str, Any]:
    start = DateUtils.parse_date(start_date)
    end = DateUtils.parse_date(end_date)
    calculated: list[dict[str, Any]] = []
    for row in rows:
        row_date = DateUtils.parse_date(row.get("date"))
        if start and (not row_date or row_date < start):
            continue
        if end and (not row_date or row_date > end):
            continue
        calculated.append(calculate_attendance(row, policy))

    by_employee: dict[str, dict[str, Any]] = {}
    status_counts = {status: 0 for status in ATTENDANCE_STATUSES}
    for row in calculated:
        status = normalize_status(row.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1
        employee = str(row.get("full_name") or row.get("employee_name") or row.get("employee_id") or "Unknown")
        bucket = by_employee.setdefault(employee, {
            "employee": employee,
            "days": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
            "leave": 0,
            "half_day": 0,
            "field_visit": 0,
            "worked_minutes": 0,
            "overtime_minutes": 0,
            "late_minutes": 0,
        })
        bucket["days"] += 1
        bucket["worked_minutes"] += safe_int(row.get("worked_minutes"))
        bucket["overtime_minutes"] += safe_int(row.get("overtime_minutes"))
        bucket["late_minutes"] += safe_int(row.get("late_minutes"))
        if status in {"Present", "Remote"}:
            bucket["present"] += 1
        elif status == "Late":
            bucket["present"] += 1
            bucket["late"] += 1
        elif status == "Field Visit":
            bucket["present"] += 1
            bucket["field_visit"] += 1
        elif status == "Absent":
            bucket["absent"] += 1
        elif status == "Leave":
            bucket["leave"] += 1
        elif status == "Half Day":
            bucket["half_day"] += 1

    total = len(calculated)
    present_like = sum(status_counts.get(key, 0) for key in ("Present", "Late", "Remote", "Field Visit"))
    absent = status_counts.get("Absent", 0)
    leave = status_counts.get("Leave", 0)
    return {
        "period": {
            "start_date": start.isoformat() if isinstance(start, date) else None,
            "end_date": end.isoformat() if isinstance(end, date) else None,
        },
        "total_rows": total,
        "present_days": present_like,
        "absent_days": absent,
        "leave_days": leave,
        "late_days": status_counts.get("Late", 0),
        "field_visit_days": status_counts.get("Field Visit", 0),
        "half_days": status_counts.get("Half Day", 0),
        "worked_minutes": sum(safe_int(row.get("worked_minutes")) for row in calculated),
        "overtime_minutes": sum(safe_int(row.get("overtime_minutes")) for row in calculated),
        "late_minutes": sum(safe_int(row.get("late_minutes")) for row in calculated),
        "attendance_rate": round((present_like / total) * 100, 2) if total else 0,
        "status_counts": status_counts,
        "employees": sorted(by_employee.values(), key=lambda item: item["employee"]),
    }


def normalize_status(value: Any) -> str:
    text = " ".join(str(value or "").strip().split()).lower()
    aliases = {
        "": "Not Marked",
        "not marked": "Not Marked",
        "present": "Present",
        "p": "Present",
        "late": "Late",
        "absent": "Absent",
        "a": "Absent",
        "leave": "Leave",
        "on leave": "Leave",
        "half day": "Half Day",
        "half-day": "Half Day",
        "remote": "Remote",
        "work from home": "Remote",
        "field": "Field Visit",
        "field visit": "Field Visit",
        "property visit": "Field Visit",
    }
    return aliases.get(text, str(value or "Not Marked").strip() or "Not Marked")


def minutes_between(start: time | None, end: time | None) -> int:
    if not start or not end:
        return 0
    start_minutes = minutes_since_midnight(start)
    end_minutes = minutes_since_midnight(end)
    if end_minutes < start_minutes:
        end_minutes += 24 * 60
    return max(0, end_minutes - start_minutes)


def minutes_since_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default
