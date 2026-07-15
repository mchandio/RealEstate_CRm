# LibreOffice UNO Python macros for basic field validation
# Place this file in a location LibreOffice can load (e.g., user profile scripts/python
# or import it via Tools → Macros → Organize Macros → Python).

import re
from datetime import datetime

# Exported functions should be listed in __all__ for LibreOffice macro discovery
__all__ = [
    "normalize_phone",
    "validate_phone",
    "validate_cnic",
    "validate_date",
    "xs_validate_phone",
    "xs_validate_cnic",
    "xs_validate_date",
]

PHONE_RE = re.compile(r"\+?\d[\n\d\- ]+$")

def normalize_phone(phone: str) -> str:
    """Normalize phone numbers to international-ish format (keeps digits and leading +)."""
    if phone is None:
        return ""
    text = str(phone).strip()
    if not text:
        return ""
    # remove common separators
    digits = "+" + re.sub(r"[^\d]", "", text) if text.startswith("+") else re.sub(r"[^\d]", "", text)
    # if starts with 0 and 11-12 digits, convert to +92 form
    if digits.startswith("0") and 10 <= len(digits) <= 11:
        digits = "+92" + digits.lstrip("0")
    return digits


def validate_phone(phone: str, required: bool = False) -> bool:
    """Basic phone validation. Accepts digits, optional leading +. Raises ValueError for invalid input."""
    text = (phone or "").strip()
    if not text:
        if required:
            raise ValueError("Phone is required")
        return True
    normalized = normalize_phone(text)
    # require at least 9 digits (loose rule) and at most 15 including +
    digits_only = re.sub(r"[^\d]", "", normalized)
    if len(digits_only) < 9 or len(digits_only) > 15:
        raise ValueError("Phone number looks invalid")
    if not PHONE_RE.match(phone):
        raise ValueError("Phone number contains invalid characters")
    return True


def validate_cnic(cnic: str, required: bool = False) -> bool:
    """Validate CNIC-like national ID: ensure 13 digits present."""
    text = (cnic or "").strip()
    if not text:
        if required:
            raise ValueError("CNIC is required")
        return True
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) != 13:
        raise ValueError("CNIC must contain exactly 13 digits")
    return True


def validate_date(date_text: str, required: bool = False) -> bool:
    """Validate date in common formats (DD/MM/YYYY, YYYY-MM-DD)."""
    text = (date_text or "").strip()
    if not text:
        if required:
            raise ValueError("Date is required")
        return True
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    raise ValueError("Date must be in DD/MM/YYYY or YYYY-MM-DD format")

# XSCRIPTNAME wrappers for LibreOffice event bindings. They accept an event object
# when bound from a form control; the event's Source.Value typically contains control value.

def xs_validate_phone(event=None):
    """LibreOffice-callable wrapper. Raises an exception to show an error dialog in some bindings."""
    value = _event_value(event)
    return validate_phone(value, required=False)


def xs_validate_cnic(event=None):
    value = _event_value(event)
    return validate_cnic(value, required=False)


def xs_validate_date(event=None):
    value = _event_value(event)
    return validate_date(value, required=False)


def _event_value(event):
    # Extract value from different event shapes (FormControl, Document, direct call)
    try:
        if event is None:
            return ""
        # For control events, Source.Value often contains the field value
        src = getattr(event, 'Source', None) or getattr(event, 'SourceControl', None) or event
        if hasattr(src, 'Value'):
            return src.Value
        if hasattr(src, 'Text'):
            return src.Text
    except Exception:
        pass
    # fallback to string representation
    try:
        return str(event)
    except Exception:
        return ""
