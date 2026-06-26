"""Shared validation helpers used by Desktop and Web/API code."""

from __future__ import annotations

import re


class PhoneValidator:
    """Pakistan mobile phone validation and normalization."""

    @staticmethod
    def normalize(phone_str: object) -> str:
        """Return an 11 digit local mobile number, or an empty string."""
        digits = re.sub(r"\D+", "", str(phone_str or ""))
        if digits.startswith("92") and len(digits) == 12:
            digits = "0" + digits[2:]
        return digits

    @staticmethod
    def validate_phone(phone_str: object, *, required: bool = False) -> str:
        """Accept 03001234567, 0300-1234567, +923001234567, or 923001234567."""
        digits = PhoneValidator.normalize(phone_str)
        if not digits:
            if required:
                raise ValueError("Phone number is required")
            return ""
        if len(digits) != 11 or not digits.startswith("03"):
            raise ValueError("Phone must be 03001234567 or +923001234567")
        return digits

    @staticmethod
    def display_phone(phone_str: object) -> str:
        digits = PhoneValidator.normalize(phone_str)
        if len(digits) == 11 and digits.startswith("03"):
            return f"+92 {digits[1:4]} {digits[4:]}"
        return str(phone_str or "")
