"""Shared explainable matching logic for CRM deal records."""

from __future__ import annotations

import re
from typing import Any


STOP_WORDS = {
    "and", "or", "the", "for", "with", "from", "this", "that", "have",
    "has", "need", "needs", "want", "wants", "required", "requirement",
    "available", "availability", "property", "properties", "rent", "sale",
    "flat", "house", "home", "plot", "apartment", "villa", "room", "bed",
    "beds", "bath", "baths", "sqft", "sq", "ft", "yard", "yards", "rs",
    "near", "area", "location", "client", "owner", "family", "bachelor",
}


def record_to_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return dict(record)
    table = getattr(record, "__table__", None)
    if table is not None:
        return {column.name: getattr(record, column.name, None) for column in table.columns}
    return dict(getattr(record, "__dict__", {}) or {})


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def tokens(value: Any) -> set[str]:
    text = re.sub(r"[^a-z0-9]+", " ", normalize_text(value))
    return {part for part in text.split() if len(part) > 1 and part not in STOP_WORDS}


def number(value: Any) -> float:
    try:
        text = re.sub(r"[^0-9.]", "", str(value or ""))
        return float(text) if text else 0.0
    except (TypeError, ValueError):
        return 0.0


def property_text(row: dict[str, Any], table: str) -> str:
    if table.endswith("requirements"):
        return str(row.get("property_requires") or row.get("property_type") or "")
    return str(row.get("property_availability") or row.get("property_type") or "")


def amount_for_table(row: dict[str, Any], table: str) -> float:
    if table == "rent_availability":
        return number(row.get("monthly_rent"))
    if table == "sale_availability":
        return number(row.get("demand") or row.get("sale_price"))
    return number(row.get("budget") or row.get("expected_close_value"))


def display_name(row: dict[str, Any]) -> str:
    for key in ("client_name", "owner_name", "full_name", "title", "property_code"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    row_id = row.get("id")
    return f"Record #{row_id}" if row_id else "Record"


def is_open_candidate(row: dict[str, Any], table: str) -> bool:
    status = normalize_text(row.get("status"))
    stage = normalize_text(row.get("workflow_stage"))
    if table.endswith("availability") and status in {"rented", "sold", "closed", "inactive"}:
        return False
    if stage in {"closed", "deal done"}:
        return False
    return True


def _location_score(left: str, right: str) -> tuple[float, str | None]:
    if not left or not right:
        return 0.0, None
    if left == right:
        return 30.0, "same location"
    if left in right or right in left:
        return 24.0, "near location"
    overlap = tokens(left) & tokens(right)
    if overlap:
        return min(20.0, 8.0 + len(overlap) * 4.0), "location word match"
    return 0.0, None


def _token_score(left: str, right: str, max_score: float, label: str) -> tuple[float, str | None]:
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0, None
    overlap = left_tokens & right_tokens
    if not overlap:
        return 0.0, None
    ratio = len(overlap) / max(len(left_tokens), len(right_tokens), 1)
    return min(max_score, max_score * (0.35 + ratio)), label


def _budget_score(left_amount: float, right_amount: float, left_table: str, right_table: str) -> tuple[float, str | None]:
    if not left_amount or not right_amount:
        return 0.0, None
    requirement_amount = left_amount if left_table.endswith("requirements") else right_amount
    availability_amount = right_amount if right_table.endswith("availability") else left_amount
    if not requirement_amount or not availability_amount:
        return 0.0, None
    if availability_amount <= requirement_amount:
        ratio = availability_amount / max(requirement_amount, 1.0)
        if ratio >= 0.75:
            return 25.0, "budget fit"
        return 18.0 + ratio * 6.0, "under budget"
    over = (availability_amount - requirement_amount) / max(requirement_amount, 1.0)
    if over <= 0.1:
        return 19.0, "slightly above budget"
    if over <= 0.25:
        return 12.0, "negotiable budget gap"
    return max(0.0, 8.0 - over * 10.0), None


def smart_match_score(
    left: Any,
    right: Any,
    left_table: str,
    right_table: str,
) -> tuple[float, list[str]]:
    left_row = record_to_dict(left)
    right_row = record_to_dict(right)
    if not is_open_candidate(right_row, right_table):
        return 0.0, ["not active"]

    score = 0.0
    reasons: list[str] = []

    loc_score, loc_reason = _location_score(
        normalize_text(left_row.get("location")),
        normalize_text(right_row.get("location")),
    )
    score += loc_score
    if loc_reason:
        reasons.append(loc_reason)

    type_score, type_reason = _token_score(
        property_text(left_row, left_table),
        property_text(right_row, right_table),
        25.0,
        "property type fit",
    )
    score += type_score
    if type_reason:
        reasons.append(type_reason)

    budget_score, budget_reason = _budget_score(
        amount_for_table(left_row, left_table),
        amount_for_table(right_row, right_table),
        left_table,
        right_table,
    )
    score += budget_score
    if budget_reason:
        reasons.append(budget_reason)

    size_score, size_reason = _token_score(
        left_row.get("size") or left_row.get("area"),
        right_row.get("size") or right_row.get("area"),
        10.0,
        "size fit",
    )
    score += size_score
    if size_reason:
        reasons.append(size_reason)

    floor_score, floor_reason = _token_score(left_row.get("floor"), right_row.get("floor"), 5.0, "floor fit")
    score += floor_score
    if floor_reason:
        reasons.append(floor_reason)

    facilities_score, facilities_reason = _token_score(
        left_row.get("facilities"),
        right_row.get("facilities"),
        5.0,
        "facilities overlap",
    )
    score += facilities_score
    if facilities_reason:
        reasons.append(facilities_reason)

    return min(100.0, round(score, 1)), reasons[:5]


def best_matches(
    target: Any,
    candidates: list[Any],
    target_table: str,
    candidate_table: str,
    *,
    limit: int = 12,
    minimum_score: float = 15.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        row = record_to_dict(candidate)
        score, reasons = smart_match_score(target, row, target_table, candidate_table)
        if score < minimum_score:
            continue
        rows.append({
            "id": row.get("id"),
            "name": display_name(row),
            "location": row.get("location") or "",
            "price": amount_for_table(row, candidate_table),
            "type": property_text(row, candidate_table),
            "score": score,
            "stage": row.get("workflow_stage") or "Lead",
            "status": row.get("status") or "",
            "reasons": reasons,
        })
    rows.sort(key=lambda item: (float(item["score"] or 0), int(item.get("id") or 0)), reverse=True)
    return rows[:limit]
