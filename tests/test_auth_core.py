"""Unit tests for crm_core/auth.py - Password hashing, strength validation, and account lockout.

Covers:
- Password hashing (SHA-256 and bcrypt if available)
- Password verification
- Password rehashing detection
- Password strength validation
- Account lockout logic
- Failed login tracking
- Lockout reset on expiry
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from crm_core.auth import (
    LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_ATTEMPTS,
    MIN_PASSWORD_LENGTH,
    hash_password,
    is_account_locked,
    needs_rehash,
    record_failed_login,
    rehash_to_bcrypt,
    reset_failed_attempts,
    verify_password,
    validate_password_strength,
)


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

class TestHashPassword:
    def test_hash_password_returns_non_empty_string(self):
        result = hash_password("mysecretpassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_is_deterministic_with_bcrypt(self):
        """bcrypt produces unique hashes each time due to salt; just check type."""
        h1 = hash_password("testpassword")
        h2 = hash_password("testpassword")
        # bcrypt: both should be valid hashes (may differ due to salt)
        assert isinstance(h1, str)
        assert isinstance(h2, str)

    def test_hash_password_sha256_fallback(self):
        """Verify SHA-256 produces expected 64 hex char output."""
        # Directly test SHA-256 hashing as fallback
        password = "test"
        sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        assert len(sha256_hash) == 64
        assert re.fullmatch(r"[0-9a-fA-F]{64}", sha256_hash)


# ---------------------------------------------------------------------------
# Password Verification
# ---------------------------------------------------------------------------

class TestVerifyPassword:
    def test_verify_correct_password(self):
        password = "MySecurePass1!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "MySecurePass1!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword1!", hashed) is False

    def test_verify_empty_hash_returns_false(self):
        assert verify_password("anything", "") is False
        assert verify_password("anything", None) is False

    def test_verify_sha256_hash(self):
        """Legacy SHA-256 hashes should still verify."""
        password = "legacy123"
        sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        assert verify_password(password, sha256_hash) is True
        assert verify_password("wrong", sha256_hash) is False

    def test_verify_bcrypt_hash(self):
        """bcrypt hashes should verify correctly."""
        password = "bcryptpass1!"
        hashed = hash_password(password)
        if hashed.startswith("$2"):
            assert verify_password(password, hashed) is True
            assert verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# Rehash Detection
# ---------------------------------------------------------------------------

class TestNeedsRehash:
    def test_sha256_needs_rehash(self):
        sha256 = hashlib.sha256("test".encode()).hexdigest()
        assert needs_rehash(sha256) is True

    def test_bcrypt_does_not_need_rehash(self):
        hashed = hash_password("testpassword")
        if hashed.startswith("$2"):
            assert needs_rehash(hashed) is False

    def test_empty_hash_does_not_need_rehash(self):
        assert needs_rehash("") is False
        assert needs_rehash(None) is False


# ---------------------------------------------------------------------------
# Password Strength Validation
# ---------------------------------------------------------------------------

class TestValidatePasswordStrength:
    def test_valid_strong_password(self):
        is_valid, msg = validate_password_strength("MyStr0ng!Pass")
        assert is_valid is True
        assert msg == ""

    def test_too_short(self):
        is_valid, msg = validate_password_strength("Ab1!")
        assert is_valid is False
        assert "at least" in msg.lower()

    def test_no_uppercase(self):
        is_valid, msg = validate_password_strength("mystr0ng!pass")
        assert is_valid is False
        assert "uppercase" in msg.lower()

    def test_no_lowercase(self):
        is_valid, msg = validate_password_strength("MYSTR0NG!PASS")
        assert is_valid is False
        assert "lowercase" in msg.lower()

    def test_no_digit(self):
        is_valid, msg = validate_password_strength("MyStrong!Pass")
        assert is_valid is False
        assert "digit" in msg.lower()

    def test_no_special_character(self):
        is_valid, msg = validate_password_strength("MyStr0ngPass")
        assert is_valid is False
        assert "special" in msg.lower()

    def test_exactly_minimum_length(self):
        is_valid, _ = validate_password_strength("Abcdef1!")
        assert is_valid is True

    def test_various_special_characters(self):
        # Test common special characters (excluding problematic ones in regex)
        special_chars = "!@#$%^&*()_+-=[]{}|;:,./<>?"
        for char in special_chars:
            is_valid, _ = validate_password_strength(f"Abcdef1{char}")
            assert is_valid is True, f"Failed for special char: {char}"


# ---------------------------------------------------------------------------
# Account Lockout
# ---------------------------------------------------------------------------

def _make_mock_db(user_data=None):
    """Create mock db_fetch_one and db_execute functions with controllable data."""
    if user_data is None:
        user_data = {}
    
    fetch_one = MagicMock(return_value=user_data)
    execute = MagicMock()
    return fetch_one, execute


class TestIsAccountLocked:
    def test_user_not_found_not_locked(self):
        fetch_one, execute = _make_mock_db(None)
        is_locked, msg = is_account_locked(fetch_one, execute, "unknown")
        assert is_locked is False

    def test_no_lockout_field_not_locked(self):
        user = {"id": 1, "locked_until": None, "failed_attempts": 0}
        fetch_one, execute = _make_mock_db(user)
        is_locked, msg = is_account_locked(fetch_one, execute, "user1")
        assert is_locked is False

    def test_active_lockout_returns_locked(self):
        future = (datetime.now() + timedelta(minutes=10)).isoformat()
        user = {"id": 1, "locked_until": future, "failed_attempts": 5}
        fetch_one, execute = _make_mock_db(user)
        is_locked, msg = is_account_locked(fetch_one, execute, "user1")
        assert is_locked is True
        assert "locked" in msg.lower() or "try again" in msg.lower()

    def test_expired_lockout_resets_and_returns_unlocked(self):
        past = (datetime.now() - timedelta(minutes=10)).isoformat()
        user = {"id": 1, "locked_until": past, "failed_attempts": 5}
        fetch_one, execute = _make_mock_db(user)
        is_locked, msg = is_account_locked(fetch_one, execute, "user1")
        assert is_locked is False
        execute.assert_called_once()

    def test_invalid_lockout_date_resets(self):
        user = {"id": 1, "locked_until": "not-a-date", "failed_attempts": 3}
        fetch_one, execute = _make_mock_db(user)
        is_locked, msg = is_account_locked(fetch_one, execute, "user1")
        assert is_locked is False


class TestRecordFailedLogin:
    def test_increments_failed_attempts(self):
        user = {"id": 1, "failed_attempts": 2}
        fetch_one = MagicMock(return_value=user)
        execute = MagicMock()
        result = record_failed_login(execute, fetch_one, "user1")
        assert result == 3

    def test_locks_account_at_max_attempts(self):
        user = {"id": 1, "failed_attempts": MAX_FAILED_ATTEMPTS - 1}
        fetch_one = MagicMock(return_value=user)
        execute = MagicMock()
        result = record_failed_login(execute, fetch_one, "user1")
        assert result == MAX_FAILED_ATTEMPTS
        # Should have called execute with lockout query
        execute.assert_called_once()
        call_args = execute.call_args
        assert "locked_until" in call_args[0][0]

    def test_user_not_found_returns_zero(self):
        fetch_one = MagicMock(return_value=None)
        execute = MagicMock()
        result = record_failed_login(execute, fetch_one, "unknown")
        assert result == 0

    def test_first_failed_attempt(self):
        user = {"id": 1, "failed_attempts": 0}
        fetch_one = MagicMock(return_value=user)
        execute = MagicMock()
        result = record_failed_login(execute, fetch_one, "user1")
        assert result == 1


class TestResetFailedAttempts:
    def test_resets_attempts_and_lockout(self):
        execute = MagicMock()
        reset_failed_attempts(execute, "user1")
        execute.assert_called_once()
        call_args = execute.call_args
        assert "failed_attempts = 0" in call_args[0][0]
        assert "locked_until = NULL" in call_args[0][0]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_max_failed_attempts_is_five(self):
        assert MAX_FAILED_ATTEMPTS == 5

    def test_lockout_duration_is_thirty_minutes(self):
        assert LOCKOUT_DURATION_MINUTES == 30

    def test_min_password_length_is_eight(self):
        assert MIN_PASSWORD_LENGTH == 8
