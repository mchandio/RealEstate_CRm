"""Shared explainable matching logic for CRM deal records - Karachi Real Estate Edition."""

from __future__ import annotations

import re
from typing import Any

# =============================================================================
# KARACHI LOCATION ALIASES FOR MATCHING
# =============================================================================

KARACHI_LOCATION_ALIASES: dict[str, str] = {
    # DHA variants
    "dha": "DHA",
    "defence": "DHA",
    "defence housing": "DHA",
    "defence housing authority": "DHA",
    "phase 1": "DHA Phase 1",
    "phase-1": "DHA Phase 1",
    "phase1": "DHA Phase 1",
    "1": "DHA Phase 1",
    "phase 2": "DHA Phase 2",
    "phase-2": "DHA Phase 2",
    "phase2": "DHA Phase 2",
    "2": "DHA Phase 2",
    "phase 4": "DHA Phase 4",
    "phase-4": "DHA Phase 4",
    "phase4": "DHA Phase 4",
    "4": "DHA Phase 4",
    "phase 5": "DHA Phase 5",
    "phase-5": "DHA Phase 5",
    "phase5": "DHA Phase 5",
    "5": "DHA Phase 5",
    "phase 6": "DHA Phase 6",
    "phase-6": "DHA Phase 6",
    "phase6": "DHA Phase 6",
    "6": "DHA Phase 6",
    "phase 7": "DHA Phase 7",
    "phase-7": "DHA Phase 7",
    "phase7": "DHA Phase 7",
    "7": "DHA Phase 7",
    "phase 8": "DHA Phase 8",
    "phase-8": "DHA Phase 8",
    "phase8": "DHA Phase 8",
    "8": "DHA Phase 8",
    # Clifton variants
    "clifton": "Clifton",
    "cb": "Clifton Block",
    "clifton block": "Clifton Block",
    "block": "Clifton Block",
    "cliftonblock": "Clifton Block",
    # Bahria variants
    "bahria": "Bahria Town Karachi",
    "bth": "Bahria Town Karachi",
    "btk": "Bahria Town Karachi",
    "bahria town": "Bahria Town Karachi",
    "bahria sports": "Bahria Sports City",
    "bahria precint": "Bahria Town Karachi",
    "precinct": "Bahria Town Karachi",
    # Gulshan variants
    "gulshan": "Gulshan-e-Iqbal",
    "gulshan iqbal": "Gulshan-e-Iqbal",
    "gulshan-e-iqbal": "Gulshan-e-Iqbal",
    "gulshan jauhar": "Gulshan-e-Jauhar",
    "gulshan-e-jauhar": "Gulshan-e-Jauhar",
    # Other common aliases
    "nazimabad": "North Nazimabad",
    "f.b area": "FB Area",
    "fb area": "FB Area",
    "f.b.area": "FB Area",
    "gulistan johar": "Gulistan-e-Johar",
    "gulistan-e-johar": "Gulistan-e-Johar",
    "scheme 33": "Scheme 33",
    "scheme33": "Scheme 33",
    "north nazimabad": "North Nazimabad",
    "pec hs": "PECHS",
    "pecshs": "PECHS",
    "tariq road": "Tariq Road",
    "tariqroad": "Tariq Road",
    "badar": "Badar Commercial",
    "bukhari": "Bukhari Commercial",
    "badar commercial": "Badar Commercial",
    "bukhari commercial": "Bukhari Commercial",
    "zamzama": "Zamzama",
    "boat basin": "Boat Basin",
    "boatbasin": "Boat Basin",
    "sea view": "Sea View",
    "seaview": "Sea View",
    "marina": "Marina",
    "cantt": "Cantt",
    "malir": "Malir",
    "korangi": "Korangi",
    "landhi": "Korangi",
    "lyari": "Lyari",
    "saddar": "Saddar",
}

# DHA Phase-specific aliases
DHA_PHASE_ALIASES: dict[str, str] = {
    "ph1": "DHA Phase 1",
    "ph 1": "DHA Phase 1",
    "ph-1": "DHA Phase 1",
    "ph2": "DHA Phase 2",
    "ph 2": "DHA Phase 2",
    "ph-2": "DHA Phase 2",
    "ph4": "DHA Phase 4",
    "ph 4": "DHA Phase 4",
    "ph-4": "DHA Phase 4",
    "ph5": "DHA Phase 5",
    "ph 5": "DHA Phase 5",
    "ph-5": "DHA Phase 5",
    "ph6": "DHA Phase 6",
    "ph 6": "DHA Phase 6",
    "ph-6": "DHA Phase 6",
    "ph7": "DHA Phase 7",
    "ph 7": "DHA Phase 7",
    "ph-7": "DHA Phase 7",
    "ph8": "DHA Phase 8",
    "ph 8": "DHA Phase 8",
    "ph-8": "DHA Phase 8",
}


def normalize_karachi_location(location: str) -> str:
    """Normalize Karachi location names using aliases.

    Args:
        location: Raw location string

    Returns:
        Normalized location string
    """
    if not location:
        return ""

    normalized = normalize_text(location)

    # Check DHA phase aliases first (more specific)
    for alias, canonical in DHA_PHASE_ALIASES.items():
        if alias in normalized:
            return canonical

    # Check general location aliases
    for alias, canonical in KARACHI_LOCATION_ALIASES.items():
        if alias in normalized:
            return canonical

    # Return original if no match
    return str(location).strip()


def location_similarity(left: str, right: str) -> float:
    """Calculate location similarity using Karachi-specific normalization.

    This function handles Karachi's common location variations and
    provides higher scores for DHA phase matches and area matches.

    Args:
        left: First location string
        right: Second location string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not left or not right:
        return 0.0

    left_norm = normalize_text(left)
    right_norm = normalize_text(right)

    # Exact match
    if left_norm == right_norm:
        return 1.0

    # Check if both normalized to same canonical form
    left_canon = normalize_karachi_location(left)
    right_canon = normalize_karachi_location(right)

    if left_canon and right_canon and left_canon == right_canon:
        return 0.95

    # Check substring matches (one contains the other)
    if left_norm in right_norm or right_norm in left_norm:
        return 0.85

    # Token overlap
    left_tokens = tokens(left)
    right_tokens = tokens(right)

    if left_tokens and right_tokens:
        overlap = len(left_tokens & right_tokens)
        total = len(left_tokens | right_tokens)
        if overlap > 0:
            return 0.5 + (overlap / total) * 0.35

    # Check if both are DHA phases (same area family)
    left_lower = left_norm.lower()
    right_lower = right_norm.lower()

    if "dha" in left_lower and "dha" in right_lower:
        # Extract phase numbers
        left_match = re.search(r'phase\s*(\d+)', left_lower)
        right_match = re.search(r'phase\s*(\d+)', right_lower)
        if left_match and right_match:
            if left_match.group(1) == right_match.group(1):
                return 0.9
            return 0.6  # Same DHA family, different phase
        return 0.7  # Both DHA but no phase specified

    return 0.0


def prefilter_candidates(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    target_table: str,
    candidate_table: str,
    price_tolerance: float = 0.30,
    max_candidates: int = 200,
) -> list[dict[str, Any]]:
    """Pre-filter candidates by price range and location to reduce matching workload.
    
    Args:
        target: The source record to match against
        candidates: List of potential candidate records
        target_table: Table name of the target record
        candidate_table: Table name of the candidates
        price_tolerance: Price matching tolerance (default 30%)
        max_candidates: Maximum candidates to return after filtering
    
    Returns:
        Filtered list of candidates most likely to match
    """
    if not candidates:
        return []
    
    # Get target price
    target_amount = amount_for_table(target, target_table)
    target_location = normalize_text(target.get("location"))
    target_tokens = tokens(target_location)
    
    scored_candidates = []
    
    for candidate in candidates:
        candidate_row = record_to_dict(candidate)
        
        # Skip inactive records
        if not is_open_candidate(candidate_row, candidate_table):
            continue
        
        score = 0.0
        
        # Price proximity score (0-50)
        candidate_amount = amount_for_table(candidate_row, candidate_table)
        if target_amount and candidate_amount:
            price_ratio = min(target_amount, candidate_amount) / max(target_amount, candidate_amount)
            if price_ratio >= (1 - price_tolerance):
                score += 50 * price_ratio
        elif not target_amount or not candidate_amount:
            # If either has no price, give partial credit
            score += 25
        
        # Location proximity score (0-40)
        candidate_location = normalize_text(candidate_row.get("location"))
        if target_location and candidate_location:
            if target_location == candidate_location:
                score += 40
            elif target_location in candidate_location or candidate_location in target_location:
                score += 30
            else:
                # Token overlap
                candidate_tokens = tokens(candidate_location)
                if candidate_tokens and target_tokens:
                    overlap = len(target_tokens & candidate_tokens)
                    if overlap:
                        score += min(20, overlap * 10)
        
        # Property type similarity (0-10)
        target_type = property_text(target, target_table)
        candidate_type = property_text(candidate_row, candidate_table)
        if target_type and candidate_type:
            if normalize_text(target_type) == normalize_text(candidate_type):
                score += 10
            else:
                type_overlap = tokens(target_type) & tokens(candidate_type)
                if type_overlap:
                    score += min(5, len(type_overlap) * 2)
        
        scored_candidates.append((score, candidate_row))
    
    # Sort by pre-filter score and take top max_candidates
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in scored_candidates[:max_candidates]]


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
    """Calculate location matching score using Karachi-aware normalization."""
    if not left or not right:
        return 0.0, None

    left_text = normalize_text(left)
    right_text = normalize_text(right)

    if left_text == right_text:
        return 30.0, "same location"

    # Use Karachi-aware similarity
    similarity = location_similarity(left, right)

    if similarity >= 0.95:
        return 30.0, "same location"
    elif similarity >= 0.85:
        return 27.0, "same location"
    elif similarity >= 0.7:
        return 24.0, "near location"
    elif similarity >= 0.5:
        overlap = tokens(left_text) & tokens(right_text)
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
    use_prefilter: bool = True,
) -> list[dict[str, Any]]:
    """Find best matching candidates with optional pre-filtering for performance.
    
    Args:
        target: The source record to match against
        candidates: List of potential candidate records
        target_table: Table name of the target record
        candidate_table: Table name of the candidates
        limit: Maximum number of matches to return
        minimum_score: Minimum score threshold (0-100)
        use_prefilter: Whether to use pre-filtering for large candidate sets
    
    Returns:
        List of matching candidates sorted by score
    """
    # Convert target to dict once
    target_row = record_to_dict(target)
    
    # Pre-filter candidates if enabled and we have many candidates
    candidate_list = candidates
    if use_prefilter and len(candidates) > 50:
        candidate_list = prefilter_candidates(
            target_row, candidates, target_table, candidate_table
        )
    
    rows: list[dict[str, Any]] = []
    for candidate in candidate_list:
        row = record_to_dict(candidate)
        score, reasons = smart_match_score(target_row, row, target_table, candidate_table)
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
