"""Shared data formatting helpers."""

from __future__ import annotations

import re


def parse_currency(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"(?i)\brs\.?\s*", "", text).replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_currency(amount: object, currency: str = "Rs.") -> str:
    number = parse_currency(amount)
    if number is None:
        return ""
    symbol = (currency or "Rs.").strip()
    if symbol.lower() in {"rs", "rs."}:
        symbol = "Rs."
    return f"{symbol} {number:,.0f}"
